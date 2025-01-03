import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.contrib.messages import get_messages
from .factories import UserFactory, CollectionFactory
from django.test import Client

@pytest.mark.django_db
class TestRecipeScraping:
    def test_scrape_recipe_happy_path(self, client):
        """Test successful recipe scraping with mocked external services"""
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        client.force_login(user)
        
        recipe_url = "https://example.com/recipe"
        mock_recipe_data = {
            "title": "Test Recipe",
            "description": "A test recipe",
            "recipes": [{
                "title": "Main Recipe",
                "description": "The main part",
                "ingredients": [
                    {"name": "ingredient1", "amount": "1", "unit": "cup"}
                ],
                "method": ["Step 1", "Step 2"]
            }]
        }
        
        # Mock both external services
        with patch('main.views.scrape_recipe_from_url') as mock_scrape:
            mock_scrape.return_value = mock_recipe_data
            
            # Act
            response = client.post(reverse('main:scrape', args=[collection.id]), {
                'recipe_url': recipe_url,
            })
            
            # Assert
            assert response.status_code == 302  # Redirect on success
            mock_scrape.assert_called_once_with(recipe_url)
            
            # Check database objects were created
            meal = collection.meals.first()
            assert meal is not None
            assert meal.title == "Test Recipe"
            assert meal.description == "A test recipe"
            
            recipe = meal.recipes.first()
            assert recipe is not None
            assert recipe.title == "Main Recipe"
            
            ingredient = recipe.ingredients.first()
            assert ingredient is not None
            assert ingredient.name == "ingredient1"
            assert ingredient.amount == "1"
            assert ingredient.unit == "cup"
            
            steps = list(recipe.method_steps.all())
            assert len(steps) == 2
            assert steps[0].description == "Step 1"
            assert steps[1].description == "Step 2"
    
    def test_scrape_recipe_ajax(self, client):
        """Test AJAX recipe scraping path"""
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        client.force_login(user)
        
        recipe_url = "https://example.com/recipe"
        mock_recipe_data = {
            "title": "Test Recipe",
            "description": "A test recipe",
            "recipes": [{
                "title": "Main Recipe",
                "description": "The main part",
                "ingredients": [],
                "method": []
            }]
        }
        
        # Mock external service
        with patch('main.views.scrape_recipe_from_url') as mock_scrape:
            mock_scrape.return_value = mock_recipe_data
            
            # Act - Make AJAX request
            response = client.post(
                reverse('main:scrape', args=[collection.id]),
                {'recipe_url': recipe_url},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                HTTP_ACCEPT='application/json'
            )
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert 'message' in data
            assert 'redirect' in data
            assert data['message'] == 'Recipe successfully imported!'
            assert '/meals/' in data['redirect']
    
    def test_scrape_recipe_invalid_url(self, client):
        """Test error handling for invalid URLs"""
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        client.force_login(user)
        
        with patch('main.views.scrape_recipe_from_url') as mock_scrape:
            mock_scrape.side_effect = ValueError("Failed to fetch: Invalid URL")
            
            # Act - Make AJAX request
            response = client.post(
                reverse('main:scrape', args=[collection.id]),
                {'recipe_url': 'invalid-url'},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                HTTP_ACCEPT='application/json'
            )
            
            # Assert
            assert response.status_code == 400
            data = response.json()
            assert 'message' in data
            assert 'check the URL' in data['message']
    
    def test_scrape_recipe_server_error(self, client):
        """Test handling of unexpected server errors"""
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        client.force_login(user)
        
        with patch('main.views.scrape_recipe_from_url') as mock_scrape:
            mock_scrape.side_effect = Exception("Unexpected error")
            
            # Act - Make regular request
            response = client.post(reverse('main:scrape', args=[collection.id]), {
                'recipe_url': 'https://example.com/recipe',
            })
            
            # Assert
            assert response.status_code == 302  # Redirects back
            messages = list(get_messages(response.wsgi_request))
            assert len(messages) == 1
            assert "unexpected error" in str(messages[0]).lower()

    @pytest.mark.playwright
    def test_recipe_import_ui_flow(self, page, live_server):
        """Test the UI flow of recipe importing with loading states"""
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        
        # Login user via test client to get a valid session
        client = Client()
        client.force_login(user)
        session_cookie = client.cookies['sessionid']
        page.context.add_cookies([{
            'name': 'sessionid',
            'value': session_cookie.value,
            'domain': 'localhost',
            'path': '/',
        }])
        
        # Mock the scraping to take a moment to simulate loading
        with patch('main.views.scrape_recipe_from_url') as mock_scrape:
            def delayed_response(*args):
                import time
                time.sleep(0.1)  # Small delay to ensure we can see loading state
                return {
                    "title": "Test Recipe",
                    "description": "A test recipe",
                    "recipes": [{
                        "title": "Main Recipe",
                        "description": "The main part",
                        "ingredients": [
                            {
                                "name": "flour",
                                "amount": "2",
                                "unit": "cups"
                            },
                            {
                                "name": "sugar",
                                "amount": "1",
                                "unit": "cup"
                            }
                        ],
                        "method": [
                            "Mix flour and sugar",
                            "Bake at 180C"
                        ]
                    }]
                }
            mock_scrape.side_effect = delayed_response
            
            # Act - Go to collection detail page
            page.goto(f"{live_server.url}{reverse('main:collection_detail', args=[collection.id])}")
            page.wait_for_load_state("networkidle", timeout=2000)
            
            # Fill URL and submit
            page.locator("input[name='recipe_url']").fill("https://example.com/recipe")
            page.locator("button[type='submit']").click()
            
            # Assert - Check loading state appears
            assert page.locator(".ai-loading").is_visible()
            
            # Wait for redirect to meal detail page
            page.wait_for_url("**/meals/*/", timeout=2000)
    
    @pytest.mark.playwright
    def test_recipe_import_ui_error(self, page, live_server):
        """Test error handling in the UI"""
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        
        # Login user via test client to get a valid session
        client = Client()
        client.force_login(user)
        session_cookie = client.cookies['sessionid']
        page.context.add_cookies([{
            'name': 'sessionid',
            'value': session_cookie.value,
            'domain': 'localhost',
            'path': '/',
        }])
        
        # Mock scraping to fail
        with patch('main.views.scrape_recipe_from_url') as mock_scrape:
            mock_scrape.side_effect = ValueError("Failed to fetch: Invalid URL")
            
            # Act - Go to collection detail page
            page.goto(f"{live_server.url}{reverse('main:collection_detail', args=[collection.id])}")
            page.wait_for_load_state("networkidle", timeout=2000)
            
            # Fill URL and submit (use a malformed but valid-looking URL)
            page.locator("input[name='recipe_url']").fill("https://notarealwebsite.com/recipe")
            page.locator("button[type='submit']").click()
            
            # Assert - Check error appears in toast
            toast = page.wait_for_selector(".toast-body", state="visible", timeout=2000)
            assert "check the URL" in toast.text_content()
            
            # Verify submit button is re-enabled
            assert page.locator("button[type='submit']").is_visible()
            assert not page.locator(".ai-loading").is_visible()
            
            # Verify we're still on the same page
            assert f"/collections/{collection.id}" in page.url
