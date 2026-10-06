import { defineConfig } from '@playwright/test';
import awsConfig from './playwright.aws.config';

// 配信した実ファイルを検証するため、Vite と API のローカルサーバーは起動しない。
const hostingUrl = process.env.HOSTING_BASE_URL;
if (!hostingUrl || !/^https:\/\/[a-z0-9-]+\.[a-z0-9]+\.amplifyapp\.com$/.test(hostingUrl)) {
  throw new Error('HOSTING_BASE_URL に Amplify の Origin（末尾スラッシュなし）を指定してください');
}

export default defineConfig({
  ...awsConfig,
  testIgnore: [],
  use: { ...awsConfig.use, baseURL: hostingUrl },
  webServer: [],
});
