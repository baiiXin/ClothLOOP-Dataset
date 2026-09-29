import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  workers: 1,
  timeout: 60000,
  reporter: [['list'], ['github'], ['json', { outputFile: 'test-results/results.json' }]],
  use: {
    baseURL: 'http://127.0.0.1:4173/ClothLOOP-Dataset/',
    viewport: { width: 1440, height: 1000 },
    screenshot: 'only-on-failure',
    launchOptions: { args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] },
  },
  webServer: {
    command: 'python3 ../scripts/serve_web.py',
    url: 'http://127.0.0.1:4173/ClothLOOP-Dataset/',
    reuseExistingServer: false,
    timeout: 20000,
  },
});
