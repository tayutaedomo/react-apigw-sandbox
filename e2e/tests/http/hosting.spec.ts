/**
 * 概要: Amplify の静的ファイル配信を HTTP 応答で確認する。
 * 方針: ブラウザーを起動せず実成果物を取得する。画面キャプチャは対象外。
 * ケース: JS の content-type と本文、未存在 JS の404。
 */
import { expect, test } from '@playwright/test';

test('Amplify が JavaScript を配信し、未存在アセットを HTML に置き換えない', async ({ request }) => {
  const index = await request.get('/');
  expect(index.status()).toBe(200);
  const html = await index.text();
  const asset = html.match(/src="([^"]+\.js)"/)?.[1];
  expect(asset).toBeTruthy();
  const script = await request.get(asset!);
  expect(script.status()).toBe(200);
  expect(script.headers()['content-type']).toMatch(/javascript/);
  expect(await script.text()).not.toContain('<!doctype html>');
  const missing = await request.get('/assets/does-not-exist.js');
  expect(missing.status()).toBe(404);
});
