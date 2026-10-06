import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  testDir: './tests',
  testIgnore: '**/hosting.spec.ts',
  fullyParallel: true,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'on',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      cwd: fileURLToPath(new URL('../backend', import.meta.url)),
      command: 'uv run --locked uvicorn app.main:app --host localhost --port 8000',
      env: { ENABLE_ERROR_ENDPOINTS: 'true' },
      url: 'http://localhost:8000/hello',
      reuseExistingServer: false,
    },
    {
      cwd: fileURLToPath(new URL('../frontend', import.meta.url)),
      command: 'npm run dev -- --host 127.0.0.1',
      url: 'http://localhost:5173',
      reuseExistingServer: false,
    },
  ],
});
