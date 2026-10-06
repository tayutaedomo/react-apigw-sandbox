import type { Page, TestInfo } from '@playwright/test';

/** 画面の変化を PNG で保存し、操作の節目として HTML レポートへ添付する。 */
export async function capture(page: Page, testInfo: TestInfo, name: string) {
  const path = testInfo.outputPath(`${name}.png`);
  await page.screenshot({ path, fullPage: true });
  await testInfo.attach(name, { path, contentType: 'image/png' });
}
