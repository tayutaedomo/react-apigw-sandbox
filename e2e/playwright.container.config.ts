import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import baseConfig from './playwright.config';

export default defineConfig({
  ...baseConfig,
  webServer: [
    {
      cwd: fileURLToPath(new URL('.', import.meta.url)),
      command: 'bash scripts/run-api-container.sh',
      url: 'http://localhost:8000/hello',
      reuseExistingServer: false,
      gracefulShutdown: { signal: 'SIGTERM', timeout: 10_000 },
      timeout: 60_000,
    },
    {
      cwd: fileURLToPath(new URL('../frontend', import.meta.url)),
      command: 'npm run dev -- --host 127.0.0.1',
      url: 'http://localhost:5173',
      reuseExistingServer: false,
    },
  ],
});
