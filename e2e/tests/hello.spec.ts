import { expect, test } from '@playwright/test';

test('React calls the real FastAPI from a different origin', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Hello World' })).toBeVisible();

  const responsePromise = page.waitForResponse('http://localhost:8000/hello');
  await page.getByRole('button', { name: 'API を呼び出す' }).click();
  const response = await responsePromise;

  expect(response.status()).toBe(200);
  expect(response.headers()['access-control-allow-origin']).toBe('http://localhost:5173');
  await expect(page.getByText('API: Hello World', { exact: true })).toBeVisible();
});

test('React displays a connection failure and allows retry', async ({ page }) => {
  await page.route('http://localhost:8000/hello', route => route.abort('connectionfailed'));
  await page.goto('/');
  await page.getByRole('button', { name: 'API を呼び出す' }).click();
  await expect(page.getByRole('alert')).toContainText('API 呼び出しに失敗しました');
  await expect(page.getByRole('button', { name: 'API を呼び出す' })).toBeEnabled();

  await page.unroute('http://localhost:8000/hello');
  await page.getByRole('button', { name: 'API を呼び出す' }).click();
  await expect(page.getByText('API: Hello World', { exact: true })).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
});
