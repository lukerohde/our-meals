from unittest.mock import patch
from django.urls import reverse
from pytest import mark
from .factories import UserFactory, CollectionFactory
from .test_base_ui import UITestBase

@mark.playwright
class TestRecipeUI(UITestBase):
    def test_recipe_import_ui_flow(self, page, live_server):
        """Test the UI flow of recipe importing with loading states"""
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        self.setup_user_session(page, user)
        
        def delayed_response(*args):
            import time
            time.sleep(0.1)  # Small delay to ensure we can see loading state
            return """
                Classic Chocolate Chip Cookies
                
                These cookies are crispy on the outside, chewy on the inside.
                
                Ingredients:
                - 2 1/4 cups all-purpose flour
                - 1 tsp baking soda
                - 1 cup butter, softened
                - 2 cups chocolate chips
                
                Instructions:
                1. Preheat oven to 375°F
                2. Mix dry ingredients
                3. Cream butter and sugars
                4. Combine and bake
                """

        mock_parsed_recipe = {
            "title": "Classic Chocolate Chip Cookies",
            "description": "These cookies are crispy on the outside, chewy on the inside.",
            "recipes": [{
                "title": "Classic Chocolate Chip Cookies",
                "description": "These cookies are crispy on the outside, chewy on the inside.",
                "ingredients": [
                    {"name": "all-purpose flour", "amount": "2 1/4", "unit": "cups"},
                    {"name": "baking soda", "amount": "1", "unit": "tsp"},
                    {"name": "butter", "amount": "1", "unit": "cup", "notes": "softened"},
                    {"name": "chocolate chips", "amount": "2", "unit": "cups"}
                ],
                "method": [
                    "Preheat oven to 375°F",
                    "Mix dry ingredients",
                    "Cream butter and sugars",
                    "Combine and bake"
                ]
            }]
        }

        # Mock the scraping to take a moment to simulate loading
        with patch('main.views.get_recipe_text_from_url', side_effect=delayed_response), \
             patch('main.views.parse_recipe_with_genai', return_value=mock_parsed_recipe):
            
            # Act - Go to collection detail page
            page.goto(f"{live_server.url}{reverse('main:collection_detail', args=[collection.id])}")
            self.wait_for_page_load(page)
            
            # Fill URL and submit
            page.locator("input[name='recipe_url']").fill("https://example.com/recipe")
            page.locator("button[type='submit']").click()
                
            # Assert - Check loading state appears
            page.wait_for_selector(".ai-loading", state="visible", timeout=2000)
            assert page.locator(".ai-loading").is_visible()
            
            # Wait for redirect to meal detail page
            page.wait_for_url("**/meals/*/", timeout=2000)
        
    def test_recipe_import_ui_error(self, page, live_server):
        """Test error handling in the UI"""
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        self.setup_user_session(page, user)
        
        # Mock scraping to fail
        with patch('main.views.get_recipe_text_from_url', side_effect=ValueError("Failed to fetch: Invalid URL")):
            # Act - Go to collection detail page
            page.goto(f"{live_server.url}{reverse('main:collection_detail', args=[collection.id])}")
            self.wait_for_page_load(page)
            
            # Fill URL and submit (use a malformed but valid-looking URL)
            page.locator("input[name='recipe_url']").fill("https://notarealwebsite.com/recipe")
            page.locator("button[type='submit']").click()
            
            # Assert - Check error appears in toast
            toast = page.wait_for_selector(".toast-body", state="visible", timeout=2000)
            assert "Invalid URL" in toast.text_content()
            
            # Verify submit button is re-enabled
            assert page.locator("button[type='submit']").is_visible()
            assert not page.locator(".ai-loading").is_visible()
            
            # Verify we're still on the same page
            assert f"/collections/{collection.id}" in page.url
