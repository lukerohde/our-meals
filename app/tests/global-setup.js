const { chromium } = require('@playwright/test');

async function waitForServer(url, timeout = 60000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
    } catch (error) {
      // Ignore errors and keep trying
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  throw new Error(`Server at ${url} did not respond within ${timeout}ms`);
}

async function globalSetup() {
  // Create test user and collection via Django management command
  const { execSync } = require('child_process');
  execSync('python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser(\'admin\', \'admin@example.com\', \'admin\') if not User.objects.filter(username=\'admin\').exists() else None"');
  execSync('python manage.py shell -c "from main.models import Collection; from django.contrib.auth.models import User; Collection.objects.create(title=\'Test Collection\', description=\'Test Description\', user=User.objects.get(username=\'admin\')) if not Collection.objects.filter(title=\'Test Collection\').exists() else None"');

  // Wait for server to be ready
  await waitForServer('http://localhost:5000');

  // Setup auth state
  const browser = await chromium.launch({
    executablePath: '/usr/bin/chromium-browser'
  });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Login
  await page.goto('http://localhost:5000/accounts/login/', { waitUntil: 'networkidle' });
  await page.fill('#id_login', 'admin');
  await page.fill('#id_password', 'admin');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/', { waitUntil: 'networkidle' });

  // Save auth state
  await context.storageState({ path: 'playwright/.auth/user.json' });
  await browser.close();
}

module.exports = globalSetup;
