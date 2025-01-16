import pytest
from unittest.mock import patch
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .factories import UserFactory, CollectionFactory, MealFactory
from .test_base_ui import UITestBase
from .test_recipe_fixtures import get_mock_parsed_recipe

@pytest.mark.playwright
class TestMealEditUI(UITestBase, StaticLiveServerTestCase):
    @pytest.fixture(autouse=True)
    def setup_test(self, page, live_server):
        self.page = page
        self.live_server = live_server
        return self

    def test_meal_edit_success(self):
        """Test successful meal edit flow with loading states"""
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        meal = MealFactory(collection=collection)
        self.setup_user_session(self.page, user)
        
        # Mock the AI parsing
        with patch('main.views.parse_recipe_with_genai', return_value=get_mock_parsed_recipe()):
            # Act - Go to meal edit page
            self.page.goto(f"{self.live_server.url}{reverse('main:meal_edit', args=[meal.id])}")
            self.wait_for_page_load(self.page)
            
            # Update meal text
            self.page.locator("textarea[name='meal_text']").fill("Updated recipe text")
            
            # Get references to UI elements
            submit_button = self.page.locator("button[data-recipe-editor-target='submit']")
            loading_indicator = self.page.locator("div[data-recipe-editor-target='loading']")
            
            # Submit the form
            submit_button.click()
            
            # Assert - Check loading state appears
            assert loading_indicator.is_visible()
            assert submit_button.is_hidden()
            
            # Wait for redirect to meal detail page
            self.page.wait_for_url(f"**/meals/{meal.id}/", timeout=5000)

    def test_meal_edit_error(self):
        """Test error handling in meal edit UI"""
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        meal = MealFactory(collection=collection)
        self.setup_user_session(self.page, user)
        
        # Mock AI parsing to fail
        with patch('main.views.parse_recipe_with_genai', side_effect=ValueError("Failed to parse recipe")):
            # Act - Go to meal edit page
            self.page.goto(f"{self.live_server.url}{reverse('main:meal_edit', args=[meal.id])}")
            self.wait_for_page_load(self.page)
            
            # Update meal text and submit
            self.page.locator("textarea[name='meal_text']").fill("This will cause an error")
            self.page.locator("button[data-recipe-editor-target='submit']").click()
            
            # Assert - Check error appears in toast
            toast = self.page.wait_for_selector(".toast-body", state="visible", timeout=2000)
            assert "Failed to parse recipe" in toast.text_content()
            
            # Verify submit button is re-enabled and loading state is hidden
            assert self.page.locator("button[data-recipe-editor-target='submit']").is_visible()
            assert not self.page.locator(".ai-loading").is_visible()
            
            # Verify we're still on the edit page
            assert f"/meals/{meal.id}/edit" in self.page.url

    def test_keyboard_shortcut(self):
        """Test that Cmd+S (Mac) or Ctrl+S (Windows) triggers save"""
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        meal = MealFactory(collection=collection)
        self.setup_user_session(self.page, user)
        
        # Mock the AI parsing
        with patch('main.views.parse_recipe_with_genai', return_value=get_mock_parsed_recipe()):
            # Act - Go to meal edit page
            self.page.goto(f"{self.live_server.url}{reverse('main:meal_edit', args=[meal.id])}")
            self.wait_for_page_load(self.page)
            
            # Update meal text
            self.page.locator("textarea[name='meal_text']").fill("Saved with keyboard shortcut")
            
            # Press Cmd+S (Mac) or Ctrl+S (Windows)
            # Playwright automatically handles the platform-specific modifier key
            self.page.keyboard.press("Meta+s")
            
            # Assert - Check loading state appears
            assert self.page.locator(".ai-loading").is_visible()
            assert self.page.locator("button[data-recipe-editor-target='submit']").is_hidden()
            
            # Wait for redirect to meal detail page
            self.page.wait_for_url(f"**/meals/{meal.id}/", timeout=5000)
