/**
 * 概要: AWS の API Gateway / Lambda 統合を HTTP 応答で確認する。
 * 方針: ブラウザーを起動せず実 API を呼ぶ。画面キャプチャは対象外。
 * ケース: Hello World の本文、許可 Origin、Lambda の呼び出し ID。
 */
import { expect, test } from '@playwright/test';
import { frontendOrigin, helloUrl } from '../../helpers/endpoints';

test('AWS の Lambda 呼び出し ID をレスポンスから取得できる', async ({ request }) => {
  test.skip(!process.env.AWS_API_BASE_URL, 'AWS モードでのみ検証する');
  const response = await request.get(helloUrl, { headers: { Origin: frontendOrigin } });
  expect(response.status()).toBe(200);
  expect(await response.json()).toEqual({ message: 'Hello World' });
  expect(response.headers()['x-request-id']).toMatch(/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/);
  expect(response.headers()['access-control-allow-origin']).toBe(frontendOrigin);
});
