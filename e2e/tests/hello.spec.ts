/**
 * 概要: 実 API に対する React の表示と再試行をブラウザーで確認する。
 * 方針: UI と HTTP 応答を検証し、操作の節目を PNG としてレポートへ添付する。
 * ケース: 別 Origin の API 呼び出し成功、通信失敗の表示と回復後の再試行。
 */
import { expect, test, type Page, type TestInfo } from '@playwright/test';

async function capture(page: Page, testInfo: TestInfo, name: string) {
  const path = testInfo.outputPath(`${name}.png`);
  await page.screenshot({ path, fullPage: true });
  await testInfo.attach(name, { path, contentType: 'image/png' });
}

test('React から別 Origin の実 API を呼び出して結果を表示する', async ({ page }, testInfo) => {
  await page.goto('/');
  await capture(page, testInfo, '01-initial');
  await expect(page.getByRole('heading', { name: 'Hello World' })).toBeVisible();

  const responsePromise = page.waitForResponse('http://localhost:8000/hello');
  await page.getByRole('button', { name: 'API を呼び出す' }).click();
  const response = await responsePromise;

  expect(response.status()).toBe(200);
  expect(response.headers()['access-control-allow-origin']).toBe('http://localhost:5173');
  await expect(page.getByText('API: Hello World', { exact: true })).toBeVisible();
  await capture(page, testInfo, 'success');
});

test('React で通信失敗を表示し、回復後に再試行できる', async ({ page }, testInfo) => {
  await page.route('http://localhost:8000/hello', route => route.abort('connectionfailed'));
  await page.goto('/');
  await capture(page, testInfo, '01-initial');
  await page.getByRole('button', { name: 'API を呼び出す' }).click();
  await expect(page.getByRole('alert')).toContainText('API 呼び出しに失敗しました');
  await expect(page.getByRole('button', { name: 'API を呼び出す' })).toBeEnabled();
  await capture(page, testInfo, '02-connection-failed');

  await page.unroute('http://localhost:8000/hello');
  await page.getByRole('button', { name: 'API を呼び出す' }).click();
  await expect(page.getByText('API: Hello World', { exact: true })).toBeVisible();
  await capture(page, testInfo, 'success');
  await expect(page.getByRole('alert')).toHaveCount(0);
});
