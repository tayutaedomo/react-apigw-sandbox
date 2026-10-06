/**
 * 概要: Amplify のページ URL を直接開き、画面から API を呼べるか確認する。
 * 方針: ブラウザーで実際の配信済み画面を操作し、表示の変化を PNG に記録する。
 * ケース: SPA の直接アクセス、Hello World の取得。
 */
import { expect, test } from '@playwright/test';
import { capture } from '../../helpers/capture';

test('ページ URL を直接開いても React と API 呼び出しが動作する', async ({ page }, testInfo) => {
  const response = await page.goto('/poc/direct-access');
  expect(response?.status()).toBe(200);
  await expect(page.getByRole('heading', { name: 'Hello World' })).toBeVisible();
  await capture(page, testInfo, '01-direct-access');
  await page.getByRole('button', { name: 'API を呼び出す', exact: true }).click();
  await expect(page.getByText('API: Hello World', { exact: true })).toBeVisible();
  await capture(page, testInfo, '02-api-response');
});
