import pytest
from unittest.mock import patch
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .factories import UserFactory, CollectionFactory
from .test_base_ui import UITestBase
from .test_recipe_fixtures import get_mock_delayed_response, get_mock_parsed_recipe

@pytest.mark.playwright
class TestRecipeUI(UITestBase, StaticLiveServerTestCase):
    @pytest.fixture(autouse=True)
    def setup_test(self, page, live_server):
        self.page = page
        self.live_server = live_server
        return self

    def test_recipe_import_ui_flow(self):
        """Test the UI flow of recipe importing with loading states"""
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        self.setup_user_session(self.page, user)

        # Mock the scraping to take a moment to simulate loading
        with patch('main.views.get_recipe_text_from_url', side_effect=get_mock_delayed_response), \
             patch('main.views.parse_recipe_with_genai', return_value=get_mock_parsed_recipe()):
            
            # Act - Go to collection detail page
            self.page.goto(f"{self.live_server.url}{reverse('main:collection_detail', args=[collection.id])}")
            self.wait_for_page_load(self.page)
            
            # Fill URL and submit
            self.page.locator("input[name='recipe_url']").fill("https://example.com/recipe")
            self.page.locator("button[type='submit']").click()
                
            # Assert - Check loading state appears
            self.page.wait_for_selector(".ai-loading", state="visible", timeout=2000)
            assert self.page.locator(".ai-loading").is_visible()
            
            # Wait for redirect to meal detail page
            self.page.wait_for_url("**/meals/*/", timeout=5000)
        
    def test_recipe_import_ui_error(self):
        """Test error handling in the UI"""
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        self.setup_user_session(self.page, user)
        
        # Mock scraping to fail
        with patch('main.views.get_recipe_text_from_url', side_effect=ValueError("Failed to fetch: Invalid URL")):
            # Act - Go to collection detail page
            self.page.goto(f"{self.live_server.url}{reverse('main:collection_detail', args=[collection.id])}")
            self.wait_for_page_load(self.page)
            
            # Fill URL and submit (use a malformed but valid-looking URL)
            self.page.locator("input[name='recipe_url']").fill("https://notarealwebsite.com/recipe")
            self.page.locator("button[type='submit']").click()
            
            # Assert - Check error appears in toast
            toast = self.page.wait_for_selector(".toast-body", state="visible", timeout=2000)
            assert "Invalid URL" in toast.text_content()
            
            # Verify submit button is re-enabled
            assert self.page.locator("button[type='submit']").is_visible()
            assert not self.page.locator(".ai-loading").is_visible()
            
            # Verify we're still on the same page
            assert f"/collections/{collection.id}" in self.page.url
