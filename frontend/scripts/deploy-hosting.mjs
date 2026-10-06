#!/usr/bin/env node
/**
 * ビルド済み dist を手動公開する。ビルドと Terraform apply は実行しない。
 * 順序: ZIP 作成 → 配信ジョブ作成 → 署名付き URL へ PUT → 公開 → 完了待機。
 */
import { execFile } from 'node:child_process';
import { openAsBlob } from 'node:fs';
import { access, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { setTimeout as delay } from 'node:timers/promises';

const execute = promisify(execFile);
const frontendDir = resolve(dirname(fileURLToPath(import.meta.url)), '..');

/** CLI は引数配列で実行し、実行環境の AWS 認証を引き継ぐ。 */
async function run(command, args, options = {}) {
  const { stdout } = await execute(command, args, { ...options, env: { ...process.env, AWS_PAGER: '' } });
  return stdout.trim();
}

/** 配信完了まで待ち、失敗や上限超過を成功として扱わない。 */
export async function waitForDeployment(getStatus, { sleep = delay, attempts = 120 } = {}) {
  for (let attempt = 0; attempt < attempts; attempt++) {
    const status = await getStatus();
    if (status === 'SUCCEED') return;
    if (['FAILED', 'CANCELLED'].includes(status)) throw new Error(`Amplify の配信が ${status} になりました`);
    if (!['CREATED', 'PENDING', 'PROVISIONING', 'RUNNING', 'CANCELLING'].includes(status)) {
      throw new Error('Amplify から不明なジョブ状態が返されました');
    }
    if (attempt + 1 < attempts) await sleep(5000);
  }
  throw new Error('配信完了の待機上限に達しました。Amplify のジョブ状態を確認してください');
}

/** index.html を ZIP の直下に入れ、アップロード成功後だけ公開を開始する。 */
export async function deploy({ distDir = join(frontendDir, 'dist'), cli = run, upload = fetch, sleep = delay } = {}) {
  await access(join(distDir, 'index.html')); // 未ビルド時は AWS に配信ジョブを作らない。
  const outputs = JSON.parse(await cli('terraform', [`-chdir=${join(frontendDir, '../infra/hosting')}`, 'output', '-json']));
  const appId = outputs.app_id.value;
  const branch = outputs.branch_name.value;
  const region = outputs.region.value;
  const url = outputs.hosting_url.value;
  const args = ['--app-id', appId, '--branch-name', branch, '--region', region];
  const workDir = await mkdtemp(join(tmpdir(), 'sandbox-hosting-'));
  const cleanup = () => rm(workDir, { recursive: true, force: true });
  // 一時 ZIP は成功・失敗・中断のいずれでも削除する。
  const interrupt = async () => { await cleanup(); process.exit(130); };
  process.once('SIGINT', interrupt);
  process.once('SIGTERM', interrupt);
  try {
    const archive = join(workDir, 'site.zip');
    await cli('zip', ['-q', '-r', archive, '.'], { cwd: distDir });
    const deployment = JSON.parse(await cli('aws', ['amplify', 'create-deployment', ...args, '--output', 'json']));
    if (!/^\d+$/.test(deployment.jobId) || new URL(deployment.zipUploadUrl).protocol !== 'https:') {
      throw new Error('Amplify のアップロード情報が不正です');
    }
    // 署名付き URL はログやファイルへ出さない。送信に失敗した場合は公開しない。
    let response;
    try {
      response = await upload(deployment.zipUploadUrl, {
        method: 'PUT', body: await openAsBlob(archive), signal: AbortSignal.timeout(120_000),
      });
    } catch {
      throw new Error('成果物のアップロードに失敗しました');
    }
    if (!response.ok) throw new Error(`成果物のアップロードに失敗しました（HTTP ${response.status}）`);
    await cli('aws', ['amplify', 'start-deployment', ...args, '--job-id', deployment.jobId, '--output', 'json']);
    await waitForDeployment(() => cli('aws', [
      'amplify', 'get-job', ...args, '--job-id', deployment.jobId,
      '--query', 'job.summary.status', '--output', 'text',
    ]), { sleep });
    console.log(`配信完了: ${url}`);
  } finally {
    process.removeListener('SIGINT', interrupt);
    process.removeListener('SIGTERM', interrupt);
    await cleanup();
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv.length > 2) {
    console.error('使用方法: node scripts/deploy-hosting.mjs');
    process.exitCode = 1;
  } else {
    // CLI 例外の stdout には署名付き URL が含まれ得るため、例外全体を出力しない。
    deploy().catch(error => { console.error(error.message); process.exitCode = 1; });
  }
}
