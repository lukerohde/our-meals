const { defineConfig, devices } = require('@playwright/test');

const config = {
  testDir: './tests',
  timeout: 30000,
  expect: {
    timeout: 5000
  },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { 
      open: 'never',
      host: '0.0.0.0',
      port: 9323
    }],
    ['list']
  ],
  use: {
    actionTimeout: 0,
    baseURL: 'http://localhost:5000',
    trace: 'on-first-retry',
    screenshot: 'on',
    video: 'on',
    launchOptions: {
      executablePath: '/usr/bin/chromium-browser',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
  },
  globalSetup: require.resolve('./tests/global-setup.js'),
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],
  webServer: {
    command: 'python manage.py runserver 0.0.0.0:5000',
    url: 'http://localhost:5000',
    reuseExistingServer: !process.env.CI,
    stdout: 'pipe',
    stderr: 'pipe',
    timeout: 60 * 1000,
  },
};

module.exports = defineConfig(config);
