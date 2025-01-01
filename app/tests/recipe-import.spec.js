const { test, expect } = require('@playwright/test');

test.use({ storageState: 'playwright/.auth/user.json' });

test.describe('Recipe Import', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/collections/1', { waitUntil: 'networkidle' });
  });

  test('should show success message when importing a valid recipe URL', async ({ page }) => {
    // Get the form elements
    const urlInput = page.locator('#recipe-url');
    const submitButton = page.locator('[data-recipe-importer-target="submit"]');
    const loadingElement = page.locator('[data-recipe-importer-target="loading"]');
    
    // Fill in a valid recipe URL
    await urlInput.fill('https://example.com/valid-recipe');
    
    // Intercept the form submission
    await page.route('**/scrape/', async route => {
      const headers = route.request().headers();
      if (headers['accept'] === 'application/json') {
        // Add a small delay to simulate server processing
        await new Promise(resolve => setTimeout(resolve, 100));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            status: 'success',
            redirect: '/collections/1'  // Redirect back to collections since /recipes/123 doesn't exist
          })
        });
      } else {
        await route.continue();
      }
    });
    
    // Submit the form
    await submitButton.click();
    
    // Check that loading state is shown
    await expect(loadingElement).toBeVisible({ timeout: 10000 });
    await expect(submitButton).toBeHidden();
    
    // Wait for success toast
    const toastMessage = page.locator('.toast-body');
    await expect(toastMessage).toBeVisible({ timeout: 10000 });
    await expect(toastMessage).toContainText('Recipe successfully imported!');
    
    // Wait for navigation after successful import
    await page.waitForURL('**/collections/1', { waitUntil: 'networkidle', timeout: 10000 });
  });

  test('should show error message for invalid URL', async ({ page }) => {
    const urlInput = page.locator('#recipe-url');
    const submitButton = page.locator('[data-recipe-importer-target="submit"]');
    
    // Mock server error response
    await page.route('**/scrape/', async route => {
      const headers = route.request().headers();
      if (headers['accept'] === 'application/json') {
        // Add a small delay to simulate server processing
        await new Promise(resolve => setTimeout(resolve, 100));
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            status: 'error',
            message: "We couldn't access that website. Please check the URL and try again."
          })
        });
      } else {
        await route.continue();
      }
    });
    
    // Try to submit with invalid URL
    await urlInput.fill('not-a-url');
    await submitButton.click();
    
    // Check for toast message
    const toastMessage = page.locator('.toast-body');
    await expect(toastMessage).toBeVisible({ timeout: 10000 });
    await expect(toastMessage).toContainText("We couldn't access that website. Please check the URL and try again.");
  });

  test('should handle server error gracefully', async ({ page }) => {
    const urlInput = page.locator('#recipe-url');
    const submitButton = page.locator('[data-recipe-importer-target="submit"]');
    const loadingElement = page.locator('[data-recipe-importer-target="loading"]');
    
    // Fill in URL
    await urlInput.fill('https://example.com/recipe');
    
    // Mock server error response
    await page.route('**/scrape/', async route => {
      const headers = route.request().headers();
      if (headers['accept'] === 'application/json') {
        // Add a small delay to simulate server processing
        await new Promise(resolve => setTimeout(resolve, 100));
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            status: 'error',
            message: 'Failed to scrape recipe: 404 Client Error: Not Found for url: https://example.com/recipe'
          })
        });
      } else {
        await route.continue();
      }
    });
    
    // Submit form
    await submitButton.click();
    
    // Check that loading state is shown then hidden
    await expect(loadingElement).toBeVisible({ timeout: 10000 });
    
    // Check for toast error message
    const toastMessage = page.locator('.toast-body');
    await expect(toastMessage).toBeVisible({ timeout: 10000 });
    await expect(toastMessage).toContainText('Failed to scrape recipe: 404 Client Error: Not Found for url: https://example.com/recipe');
    
    // Check that form returns to initial state
    await expect(loadingElement).toBeHidden();
    await expect(submitButton).toBeVisible();
  });
});
