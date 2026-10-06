/**
 * 概要: Amplify がビルド済みの HTML / JS を配信し、SPA の直接アクセスを扱えるか確認する。
 * 方針: ローカルサーバーを使わず、配信先の実レスポンスと画面を検証する。
 * ケース: JS の content-type と本文、未存在 JS の404、ページ URL の直接アクセス。
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

test('ページ URL を直接開いても React と API 呼び出しが動作する', async ({ page }, testInfo) => {
  const response = await page.goto('/poc/direct-access');
  expect(response?.status()).toBe(200);
  await expect(page.getByRole('heading', { name: 'Hello World' })).toBeVisible();
  const initial = testInfo.outputPath('01-direct-access.png');
  await page.screenshot({ path: initial, fullPage: true });
  await testInfo.attach('直接アクセス', { path: initial, contentType: 'image/png' });
  await page.getByRole('button', { name: 'API を呼び出す', exact: true }).click();
  await expect(page.getByText('API: Hello World', { exact: true })).toBeVisible();
  const completed = testInfo.outputPath('02-api-response.png');
  await page.screenshot({ path: completed, fullPage: true });
  await testInfo.attach('API 応答', { path: completed, contentType: 'image/png' });
});
