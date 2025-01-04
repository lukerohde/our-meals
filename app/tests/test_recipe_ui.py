import pytest
from unittest.mock import patch
from django.urls import reverse
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from .factories import UserFactory, CollectionFactory
from .test_base_ui import UITestBase
from .test_recipe_fixtures import get_mock_delayed_response, get_mock_parsed_recipe, get_mock_recipe_text

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

    def test_recipe_import_with_url(self):
        """Test the full recipe import flow"""
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        self.setup_user_session(self.page, user)
        
        # Mock the OpenAI call
        with patch('main.views.get_recipe_text_from_url', return_value=get_mock_recipe_text()), \
             patch('main.views.parse_recipe_with_genai', return_value=get_mock_parsed_recipe()):
            
            # Act - Go to collection detail page
            self.page.goto(f"{self.live_server.url}{reverse('main:collection_detail', args=[collection.id])}")
            self.wait_for_page_load(self.page)
            
            # Enter recipe URL
            self.page.locator("input#recipe-url").fill("https://example.com/recipe")
            
            # Submit the form
            submit_button = self.page.locator("button[data-recipe-importer-target='submit']")
            loading_indicator = self.page.locator("div[data-recipe-importer-target='loading']")
            
            # Click submit and verify loading state
            submit_button.click()
            assert loading_indicator.is_visible()
            assert submit_button.is_hidden()
            
            # Wait for redirect to meal detail page
            self.page.wait_for_url("**/meals/*/", timeout=5000)
            
            # Verify we're on the meal detail page
            assert "/meals/" in self.page.url
            
            # Verify recipe content is displayed
            recipe_title = self.page.locator("h1:text('Classic Chocolate Chip Cookies')")
            assert recipe_title.is_visible()
            
            # Verify ingredients are displayed
            ingredients = self.page.locator(".ingredients-list .list-group-item")
            assert ingredients.count() == 4  # Based on our mock recipe data
            
            # Verify method steps
            method_steps = self.page.locator(".method-steps li")
            assert method_steps.count() == 4  # Based on our mock recipe data

    def test_photo_upload_and_import(self):
        """Test photo upload functionality including multiple files and recipe import"""
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        self.setup_user_session(self.page, user)
        
        # Mock the OpenAI call
        with patch('main.views.parse_recipe_with_genai', return_value=get_mock_parsed_recipe()):
            # Act - Go to collection detail page
            self.page.goto(f"{self.live_server.url}{reverse('main:collection_detail', args=[collection.id])}")
            self.wait_for_page_load(self.page)
            
            # Set up file chooser before clicking button
            with self.page.expect_file_chooser() as fc_info:
                # Click the image button to trigger file input
                self.page.locator("button[data-action='click->recipe-importer#triggerFileInput']").click()
            
            # Get the file chooser and set multiple files
            file_chooser = fc_info.value
            file_chooser.set_files([
                "tests/fixtures/test_recipe_image.jpg",
                "tests/fixtures/test_recipe_image_2.jpg"
            ])
            
            # Assert - Check both photo previews appear
            self.page.wait_for_selector(".photo-preview img", state="visible", timeout=5000)
            previews = self.page.locator(".photo-preview")
            assert previews.count() == 2
            
            # Verify both previews have remove buttons
            remove_buttons = self.page.locator(".remove-photo")
            assert remove_buttons.count() == 2
            
            # Test removing just the first photo
            remove_buttons.first.click()
            assert previews.count() == 1

            # Submit the form
            submit_button = self.page.locator("button[data-recipe-importer-target='submit']")
            loading_indicator = self.page.locator("div[data-recipe-importer-target='loading']")
            
            # Click submit and verify loading state
            submit_button.click()
            assert loading_indicator.is_visible()
            assert submit_button.is_hidden()
            
            # Wait for redirect to meal detail page
            self.page.wait_for_url("**/meals/*/", timeout=5000)
            
            # Verify we're on the meal detail page
            assert "/meals/" in self.page.url
            
            # Verify recipe content is displayed
            recipe_title = self.page.locator("h1:text('Classic Chocolate Chip Cookies')")
            assert recipe_title.is_visible()
            
            # Verify ingredients are displayed
            ingredients = self.page.locator(".ingredients-list .list-group-item")
            assert ingredients.count() == 4  # Based on our mock recipe data
            
            # Verify method steps
            method_steps = self.page.locator(".method-steps li")
            assert method_steps.count() == 4  # Based on our mock recipe data
