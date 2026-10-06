/**
 * 概要: 実 API のエラーを React から呼び、ブラウザーの CORS 判定を確認する。
 * 方針: 応答をモックせず、HTTP エラーの読み取りと fetch の拒否を区別する。
 * ケース: 404/405/422、明示的4xx/5xx、未処理・応答検証500、Origin拒否、
 *         プリフライトの許可・ヘッダー拒否・メソッド拒否、再試行。
 * 記録: 操作前後の PNG と、プリフライト後の送信有無を HTML レポートへ添付する。
 */
import { expect, test, type Page, type TestInfo } from '@playwright/test';

const apiBaseUrl = (process.env.AWS_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
const uuid = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;

async function capture(page: Page, testInfo: TestInfo, name: string) {
  const path = testInfo.outputPath(`${name}.png`);
  await page.screenshot({ path, fullPage: true });
  await testInfo.attach(name, { path, contentType: 'image/png' });
}

const cases = [
  { id: 'not-found', label: '存在しないパス', status: 404 },
  { id: 'method', label: '未対応メソッド', status: 405 },
  { id: 'validation', label: '入力検証エラー', status: 422 },
  ...[400, 409, 418, 429, 500, 502, 503, 504].map(status => ({ id: `http-${status}`, label: '明示的なエラー', status })),
  { id: 'unhandled', label: '未処理例外', status: 500 },
  { id: 'response-validation', label: 'レスポンス検証エラー', status: 500 },
];

for (const probe of cases) {
  test(`${probe.status}：${probe.label}の本文と相関 ID を読み取れる`, async ({ page }, testInfo) => {
    await page.goto('/');
    await page.getByLabel('検証ケース').selectOption(probe.id);
    await capture(page, testInfo, '01-selected');
    await page.getByRole('button', { name: 'エラー API を呼び出す' }).click();
    const section = page.getByRole('region', { name: 'エラーレスポンスの CORS 検証' });
    await expect(section.getByText(`HTTP ステータス: ${probe.status}`, { exact: true })).toBeVisible();
    await expect(section.getByText(/^Request ID:/)).toHaveText(new RegExp(`^Request ID: ${uuid.source.slice(1, -1)}$`));
    if (['unhandled', 'response-validation'].includes(probe.id)) {
      await expect(section.locator('pre')).toHaveText('Internal Server Error');
    } else if (probe.id.startsWith('http-')) {
      await expect(section.locator('pre')).toContainText(`Error probe: ${probe.status}`);
    } else {
      await expect(section.locator('pre')).toContainText('detail');
    }
    if (probe.status === 429) await expect(section.getByText('Retry-After: 1')).toBeVisible();
    await expect(section.getByRole('alert')).toHaveCount(0);
    await capture(page, testInfo, '02-readable-error');
  });
}

test('未許可 Origin ではサーバーが400を返しても本文を読み取れない', async ({ page }, testInfo) => {
  // 同じ Vite を別ホスト名で開き、ページの Origin を変える。レスポンスは加工しない。
  await page.goto('http://127.0.0.1:5173');
  await page.getByLabel('検証ケース').selectOption('http-400');
  await capture(page, testInfo, '01-unapproved-origin');
  await page.getByRole('button', { name: 'エラー API を呼び出す' }).click();
  await expect(page.getByRole('alert')).toContainText('レスポンスを読み取れませんでした');
  await expect(page.getByText('HTTP ステータス: 400', { exact: true })).toHaveCount(0);
  // ブラウザー外の確認は、通信失敗ではなく CORS 拒否だったことの補助証拠。
  const response = await page.request.get(`${apiBaseUrl}/errors/http/400`, { headers: { Origin: 'http://127.0.0.1:5173' } });
  expect(response.status()).toBe(400);
  expect(response.headers()['access-control-allow-origin']).toBeUndefined();
  await capture(page, testInfo, '02-origin-blocked');
});

for (const probe of [
  { id: 'preflight-ok', label: 'GET の許可', allowed: true, deniedOrigin: false },
  { id: 'preflight-ok', label: '未許可 Origin の拒否', allowed: false, deniedOrigin: true },
  { id: 'preflight-header', label: '未許可ヘッダーの拒否', allowed: false, deniedOrigin: false },
  { id: 'preflight-method', label: '未許可メソッドの拒否', allowed: false, deniedOrigin: false },
]) {
  test(`プリフライト：${probe.label}と実リクエストの送信有無`, async ({ page, context }, testInfo) => {
    // CDP は Chromium が実際に送信した OPTIONS と本リクエストを観測するために使う。
    const session = await context.newCDPSession(page);
    await session.send('Network.enable');
    const requests = new Map<string, string>();
    const received: { requestId: string; status: number }[] = [];
    const sent = new Set<string>();
    session.on('Network.requestWillBeSentExtraInfo', event => sent.add(event.requestId));
    session.on('Network.responseReceivedExtraInfo', event => {
      received.push({ requestId: event.requestId, status: event.statusCode });
    });
    session.on('Network.requestWillBeSent', event => {
      if (event.request.url === `${apiBaseUrl}/errors/http/400`) requests.set(event.requestId, event.request.method);
    });
    await page.goto(probe.deniedOrigin ? 'http://127.0.0.1:5173' : '/');
    await page.getByLabel('検証ケース').selectOption(probe.id);
    await capture(page, testInfo, '01-preflight-selected');
    await page.getByRole('button', { name: 'エラー API を呼び出す' }).click();
    if (probe.allowed) {
      await expect(page.getByText('HTTP ステータス: 400', { exact: true })).toBeVisible();
    } else {
      await expect(page.getByRole('alert')).toContainText('レスポンスを読み取れませんでした');
    }
    // CORS 拒否で JS に公開されない応答も含め、実際に受信した応答だけを数える。
    const responses = received.filter(item => requests.has(item.requestId)).map(item => ({
      method: requests.get(item.requestId), status: item.status,
    }));
    expect(responses).toEqual(expect.arrayContaining([
      { method: 'OPTIONS', status: probe.allowed ? 200 : 400 },
    ]));
    expect(responses.some(item => item.method !== 'OPTIONS')).toBe(probe.allowed);
    const sentMethods = [...sent].filter(id => requests.has(id)).map(id => requests.get(id));
    expect(sentMethods).toContain('OPTIONS');
    expect(sentMethods.some(method => method !== 'OPTIONS')).toBe(probe.allowed);
    await testInfo.attach('プリフライトの観測', { body: JSON.stringify({ sentMethods, responses }), contentType: 'application/json' });
    await capture(page, testInfo, '02-preflight-result');
    if (!probe.allowed) {
      if (probe.deniedOrigin) await page.goto('/');
      await page.getByLabel('検証ケース').selectOption('http-400');
      await page.getByRole('button', { name: 'エラー API を呼び出す' }).click();
      await expect(page.getByText('HTTP ステータス: 400', { exact: true })).toBeVisible();
      await expect(page.getByRole('alert')).toHaveCount(0);
      await capture(page, testInfo, '03-retry-readable');
    }
  });
}
