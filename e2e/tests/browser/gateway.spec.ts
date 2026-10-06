/**
 * 概要: Gateway 自身が生成した400をブラウザーが読めるか、実 AWS で確認する。
 * 方針: 配信済みページの Origin から fetch し、テスト専用パネルに結果を表示して撮影する。
 *       React の実装や API 応答は差し替えない。未許可 Origin は別サイトからの通信として再現する。
 * ケース: CORS 設定前後の読み取り、拒否後の正常 GET、未許可 Origin による拒否。
 */
import { expect, test, type Page } from '@playwright/test';
import { apiBaseUrl } from '../../helpers/endpoints';
import { capture } from '../../helpers/capture';
import { gatewayCorsEnabled, gatewayTestEnabled } from '../../helpers/gateway';

async function probe(page: Page, valid: boolean) {
  // 単純リクエストにして、プリフライトの失敗と本リクエストの400を混同しない。
  return page.evaluate(async ({ url }) => {
    let result;
    try {
      const response = await fetch(url, { credentials: 'omit' });
      result = {
        readable: true as const,
        status: response.status,
        body: await response.json(),
        requestId: response.headers.get('x-amzn-RequestId'),
      };
    } catch (error) {
      result = { readable: false as const, error: error instanceof Error ? error.name : 'Unknown' };
    }
    const panel = document.querySelector('#gateway-test-result') || document.body.appendChild(document.createElement('pre'));
    panel.id = 'gateway-test-result';
    // 製品の画面には追加しない。撮影時だけ、結果を読みやすい大きさで表示する。
    panel.setAttribute('style', 'max-width:960px;margin:24px auto;padding:16px;border:1px solid #94a3b8;font-size:16px;white-space:pre-wrap');
    panel.textContent = `Gateway ブラウザー結合テスト（GET）\n${JSON.stringify(result, null, 2)}`;
    return result;
  }, { url: `${apiBaseUrl}/gateway-probe${valid ? '?value=ok' : ''}` });
}

test('Hosting から Gateway の400を読み取り、正常 GET に切り替えられる', async ({ page }, testInfo) => {
  test.skip(!gatewayTestEnabled, 'Hosting モードでのみ検証する');
  await page.goto('/');
  await capture(page, testInfo, '01-hosting');
  const failure = await probe(page, false);
  await capture(page, testInfo, '02-gateway-400');
  expect(failure.readable).toBe(gatewayCorsEnabled);
  if (failure.readable) {
    expect(failure.status).toBe(400);
    expect(failure.body.type).toBe('BAD_REQUEST_PARAMETERS');
    expect(failure.requestId).toBeTruthy();
    expect(failure.body.request_id).toBe(failure.requestId);
  } else {
    expect(failure.error).toBe('TypeError');
  }
  const success = await probe(page, true);
  await capture(page, testInfo, '03-gateway-recovery');
  expect(success.readable).toBe(true);
  if (success.readable) {
    expect(success.status).toBe(200);
    expect(success.body).toEqual({ message: 'Gateway probe' });
  }
});

test('未許可 Origin では Gateway の400本文を読み取れない', async ({ page }, testInfo) => {
  test.skip(!gatewayTestEnabled, 'Hosting モードでのみ検証する');
  // 未許可 Origin のページだけをテストで用意する。AWS API の通信はモックしない。
  await page.route('https://unapproved.example/', route => route.fulfill({
    contentType: 'text/html', body: '<!doctype html><html lang="ja"><meta charset="utf-8"><title>未許可 Origin</title><body><h1>未許可 Origin の検証</h1></body></html>',
  }));
  await page.goto('https://unapproved.example/');
  await capture(page, testInfo, '01-unapproved-origin');
  const result = await probe(page, false);
  await capture(page, testInfo, '02-cors-blocked');
  expect(result.readable).toBe(false);
  if (!result.readable) expect(result.error).toBe('TypeError');
});
