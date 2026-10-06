/**
 * 概要: Lambda を介さない Gateway の正常応答と必須クエリ欠落の400を確認する。
 * 方針: 実 AWS のヘッダー・本文を検証する。CORS なしの比較では EXPECT_GATEWAY_CORS=false。
 * ケース: GET の MOCK 応答、GET の400、Hosting の固定 Origin、credentials 不許可、Gateway ID。
 */
import { expect, test } from '@playwright/test';
import { apiBaseUrl, frontendOrigin } from '../../helpers/endpoints';
import { gatewayCorsEnabled, gatewayTestEnabled } from '../../helpers/gateway';

test('Gateway の必須クエリ欠落は400になり、Hosting だけを CORS で許可する', async ({ request }) => {
  test.skip(!gatewayTestEnabled, 'AWS と Hosting の URL を指定したモードでのみ検証する');
  for (const origin of [frontendOrigin, 'https://unapproved.example', undefined]) {
    const response = await request.get(`${apiBaseUrl}/gateway-probe`, {
      headers: origin ? { Origin: origin } : {},
    });
    expect(response.status()).toBe(400);
    const headers = response.headers();
    expect(headers['x-request-id']).toBeUndefined(); // Lambda のログ用 ID は生成されない。
    expect(headers['access-control-allow-credentials']).toBeUndefined();
    if (gatewayCorsEnabled) {
      // 固定 Origin のため未許可 Origin / Origin なしにも同じ値が付く。ブラウザーは不一致を拒否する。
      expect(headers['access-control-allow-origin']).toBe(frontendOrigin);
      expect(headers['access-control-expose-headers'].toLowerCase()).toBe('x-amzn-requestid');
      expect(await response.json()).toEqual({
        message: 'Missing required query parameter: value',
        type: 'BAD_REQUEST_PARAMETERS',
        request_id: headers['x-amzn-requestid'],
      });
      expect(headers['x-amzn-requestid']).toBeTruthy();
    } else {
      expect(headers['access-control-allow-origin']).toBeUndefined();
      expect((await response.json()).message).toContain('Missing required request parameters');
    }
  }
});

test('Gateway の検証パスは必須クエリ付き GET に正常応答を返す', async ({ request }) => {
  test.skip(!gatewayTestEnabled, 'AWS と Hosting の URL を指定したモードでのみ検証する');
  const response = await request.get(`${apiBaseUrl}/gateway-probe?value=ok`);
  expect(response.status()).toBe(200);
  expect(await response.json()).toEqual({ message: 'Gateway probe' });
  expect(response.headers()['x-request-id']).toBeUndefined();
});
