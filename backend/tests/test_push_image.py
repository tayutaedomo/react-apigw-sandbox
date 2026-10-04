"""ECR push スクリプトの概要・方針・ケース一覧。

方針: CLI を一時的なスタブへ置き換え、AWS を変更せず入力検証と失敗時の
認証設定削除を確認する。実際の ECR 転送は AWS 上の疎通確認で扱う。
ケース: 不正タグの拒否、arm64 の拒否、push 失敗時の cleanup、成功時の digest URI、タグ自動発番。
"""

import os
import re
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "push-image.sh"


@pytest.fixture
def cli_environment(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = f"#!{sys.executable}\n" + '''
import os
from pathlib import Path
import sys
name = Path(sys.argv[0]).name
args = sys.argv[1:]
if name == "terraform":
    print("123456789012.dkr.ecr.us-east-1.amazonaws.com/test-api" if args[-1] == "repository_url" else "test-api")
elif name == "aws":
    print("dummy-token" if "get-login-password" in args else "sha256:" + "a" * 64)
elif name == "docker":
    if "tag" in args:
        Path(os.environ["TEST_CONFIG_PATH"] + ".destination").write_text(args[-1])
    elif "inspect" in args:
        print(os.environ.get("TEST_PLATFORM", "linux/amd64"))
    elif "--config" in args:
        config = Path(args[args.index("--config") + 1])
        Path(os.environ["TEST_CONFIG_PATH"]).write_text(str(config))
        if "login" in args:
            sys.stdin.read()
            (config / "config.json").write_text("dummy authentication data")
        elif "push" in args and os.environ.get("TEST_PUSH_FAIL"):
            sys.exit(1)
'''
    for command in ("terraform", "docker", "aws"):
        path = bin_dir / command
        path.write_text(stub)
        path.chmod(0o755)
    return {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "TMPDIR": str(tmp_path),
        "TEST_CONFIG_PATH": str(tmp_path / "config-path"),
    }


def run_push(environment, tag="test-001"):
    return subprocess.run(["bash", str(SCRIPT), tag], cwd=environment["TMPDIR"],
                          env=environment, capture_output=True, text=True)


def test_invalid_tag_is_rejected_before_authentication(cli_environment):
    result = run_push(cli_environment, "invalid/tag")
    assert result.returncode == 2
    assert not Path(cli_environment["TEST_CONFIG_PATH"]).exists()


def test_wrong_architecture_is_rejected_before_authentication(cli_environment):
    result = run_push({**cli_environment, "TEST_PLATFORM": "linux/arm64"})
    assert result.returncode == 1
    assert "linux/amd64" in result.stderr
    assert not Path(cli_environment["TEST_CONFIG_PATH"]).exists()


@pytest.mark.parametrize("fails", [False, True])
def test_authentication_directory_is_removed_on_success_and_failure(cli_environment, fails):
    environment = {**cli_environment, **({"TEST_PUSH_FAIL": "1"} if fails else {})}
    result = run_push(environment)
    auth_directory = Path(Path(environment["TEST_CONFIG_PATH"]).read_text())
    assert not auth_directory.exists()
    assert result.returncode == (1 if fails else 0)
    if not fails:
        assert result.stdout.strip() == "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-api@sha256:" + "a" * 64
    assert "dummy-token" not in result.stdout + result.stderr


def test_tag_is_generated_when_omitted(cli_environment):
    result = subprocess.run(["bash", str(SCRIPT)], env=cli_environment,
                            capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == "123456789012.dkr.ecr.us-east-1.amazonaws.com/test-api@sha256:" + "a" * 64
    destination = Path(cli_environment["TEST_CONFIG_PATH"] + ".destination").read_text()
    assert re.fullmatch(r"123456789012\.dkr\.ecr\.us-east-1\.amazonaws\.com/test-api:git-[a-f0-9]+-[0-9]{8}T[0-9]{6}Z-[0-9]+", destination)
