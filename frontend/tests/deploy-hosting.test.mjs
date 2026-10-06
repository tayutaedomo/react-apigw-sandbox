/**
 * 概要: 手動公開の引数、成果物の配置、失敗時の停止を AWS へ接続せず確認する。
 * 方針: ZIP は実際に作成し、Terraform / AWS の境界だけを置き換える。
 * ケース: 成功時のリージョン・ジョブ ID、ZIP 直下の index.html、一時ファイル削除、
 *         アップロード失敗時の公開抑止、未ビルド時の停止、配信失敗・待機上限。
 */
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { access, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { promisify } from 'node:util';
import { test } from 'node:test';
import { deploy, waitForDeployment } from '../scripts/deploy-hosting.mjs';

const execute = promisify(execFile);

async function fixture(t, uploadOk = true) {
  const distDir = await mkdtemp(join(tmpdir(), 'sandbox-dist-test-'));
  t.after(() => rm(distDir, { recursive: true, force: true }));
  await writeFile(join(distDir, 'index.html'), '<h1>Hello</h1>');
  const calls = [];
  let archive;
  let uploaded = false;
  const cli = async (command, args, options) => {
    calls.push({ command, args });
    if (command === 'terraform') {
      assert.match(args[0], /\/infra\/app$/);
      assert.deepEqual(args.slice(1), ['output', '-json']);
      return JSON.stringify(Object.fromEntries(
        Object.entries({ app_id: 'dexample', branch_name: 'sandbox', region: 'us-west-2', hosting_url: 'https://sandbox.example.com' })
          .map(([key, value]) => [key, { value }]),
      ));
    }
    if (command === 'zip') {
      archive = args[2];
      await execute(command, args, options);
      const { stdout } = await execute('unzip', ['-Z1', archive]);
      assert.deepEqual(stdout.trim().split('\n'), ['index.html']);
      return '';
    }
    assert.deepEqual(args.slice(2, 8), ['--app-id', 'dexample', '--branch-name', 'sandbox', '--region', 'us-west-2']);
    if (args[1] === 'create-deployment') return JSON.stringify({ jobId: '123', zipUploadUrl: 'https://upload.example.com/?signature=private' });
    assert.equal(args[args.indexOf('--job-id') + 1], '123');
    if (args[1] === 'start-deployment') {
      assert.equal(uploaded, true);
      return '{}';
    }
    if (args[1] === 'get-job') return 'SUCCEED';
    throw new Error('想定していない CLI');
  };
  const upload = async (url, options) => {
    assert.equal(url, 'https://upload.example.com/?signature=private');
    assert.equal(options.method, 'PUT');
    const body = new Uint8Array(await options.body.arrayBuffer());
    assert.deepEqual(body.slice(0, 2), new Uint8Array([0x50, 0x4b])); // ZIP のバイナリを送信する。
    uploaded = true;
    return { ok: uploadOk, status: uploadOk ? 200 : 403 };
  };
  return { distDir, cli, upload, calls, archive: () => archive };
}

test('成果物を ZIP 直下へ格納し、アップロード後に指定先へ公開する', async t => {
  const f = await fixture(t);
  await deploy(f);
  assert.deepEqual(f.calls.filter(call => call.command === 'aws').map(call => call.args[1]), ['create-deployment', 'start-deployment', 'get-job']);
  await assert.rejects(access(f.archive()), { code: 'ENOENT' });
});

test('アップロードが拒否された場合は公開せず、一時 ZIP を削除する', async t => {
  const f = await fixture(t, false);
  await assert.rejects(deploy(f), /HTTP 403/);
  assert.equal(f.calls.some(call => call.args[1] === 'start-deployment'), false);
  await assert.rejects(access(f.archive()), { code: 'ENOENT' });
});

test('送信例外に署名付き URL が含まれてもエラーには公開しない', async t => {
  const f = await fixture(t);
  f.upload = async () => { throw new Error('https://upload.example.com/?signature=private'); };
  await assert.rejects(deploy(f), { message: '成果物のアップロードに失敗しました' });
  assert.equal(f.calls.some(call => call.args[1] === 'start-deployment'), false);
  await assert.rejects(access(f.archive()), { code: 'ENOENT' });
});

test('未ビルドなら配信ジョブを作らない', async t => {
  const distDir = await mkdtemp(join(tmpdir(), 'sandbox-empty-test-'));
  t.after(() => rm(distDir, { recursive: true, force: true }));
  await assert.rejects(deploy({ distDir, cli: () => assert.fail('CLI を実行しない') }), { code: 'ENOENT' });
});

test('配信状態を待ち、成功時に終了する', async () => {
  const statuses = ['PENDING', 'RUNNING', 'SUCCEED'];
  let waits = 0;
  await waitForDeployment(async () => statuses.shift(), { sleep: async () => { waits++; } });
  assert.equal(waits, 2);
});

for (const status of ['FAILED', 'CANCELLED']) {
  test(`配信状態 ${status} は失敗として扱う`, async () => {
    await assert.rejects(waitForDeployment(async () => status), new RegExp(status));
  });
}

test('待機上限と不明な状態を検出する', async () => {
  await assert.rejects(waitForDeployment(async () => 'RUNNING', { attempts: 2, sleep: async () => {} }), /待機上限/);
  await assert.rejects(waitForDeployment(async () => 'UNKNOWN'), /不明なジョブ状態/);
});
