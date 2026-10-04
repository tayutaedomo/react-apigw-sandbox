import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import baseConfig from './playwright.config';

// endpoint は実行時に渡し、実環境の URL をソースへ保存しない。
const apiBaseUrl = process.env.AWS_API_BASE_URL?.replace(/\/$/, '');
if (!apiBaseUrl || !/^https:\/\/[^/]+\.execute-api\.[a-z0-9-]+\.amazonaws\.com(?:\.cn)?\/sandbox$/.test(apiBaseUrl)) {
  throw new Error('AWS_API_BASE_URL に sandbox ステージの REST API URL を指定してください');
}

export default defineConfig({
  ...baseConfig,
  webServer: [{
    cwd: fileURLToPath(new URL('../frontend', import.meta.url)),
    command: 'npm run dev',
    env: { VITE_API_BASE_URL: apiBaseUrl },
    url: 'http://localhost:5173',
    reuseExistingServer: false,
  }],
});
