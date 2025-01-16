import pytest
from unittest.mock import patch
from django.urls import reverse
from .test_base import BaseTestCase
from .factories import UserFactory, CollectionFactory
from .test_recipe_fixtures import get_mock_recipe_text, get_mock_parsed_recipe

pytestmark = pytest.mark.django_db

class TestRecipeScraping(BaseTestCase):
    @pytest.fixture(autouse=True)
    def setup_scraping(self, base_setup):
        """Set up test data for each test."""
        self.user = UserFactory()
        self.collection = CollectionFactory(user=self.user)
        self.url = 'https://example.com/recipe'
    
    def test_scrape_recipe_happy_path(self):
        """Test successful recipe scraping"""
        self.login_user(self.user)
        
        with patch('main.views.get_recipe_text_from_url', return_value=get_mock_recipe_text()), \
             patch('main.views.parse_recipe_with_genai', return_value=get_mock_parsed_recipe()):
            response = self.client.post(
                reverse('main:scrape', kwargs={'collection_id': self.collection.id}),
                {'recipe_text_and_urls': self.url}
            )
        
        assert response.status_code == 302  # Should redirect to collection detail
        assert '/meals/' in response['Location']
    
    def test_scrape_recipe_with_text_and_urls(self):
        """Test recipe scraping with both text and URLs"""
        self.login_user(self.user)
        recipe_text = "My favorite recipe:\n\n" + self.url + "\n\nNotes: Cook for 30 mins"
        
        with patch('main.views.get_recipe_text_from_url', return_value=get_mock_recipe_text()), \
             patch('main.views.parse_recipe_with_genai', return_value=get_mock_parsed_recipe()):
            response = self.client.post(
                reverse('main:scrape', kwargs={'collection_id': self.collection.id}),
                {'recipe_text_and_urls': recipe_text}
            )
        
        assert response.status_code == 302
        assert '/meals/' in response['Location']
    
    def test_scrape_recipe_ajax(self):
        """Test recipe scraping via AJAX"""
        self.login_user(self.user)
        
        with patch('main.views.get_recipe_text_from_url', return_value=get_mock_recipe_text()), \
             patch('main.views.parse_recipe_with_genai', return_value=get_mock_parsed_recipe()):
            response = self.client.post(
                reverse('main:scrape', kwargs={'collection_id': self.collection.id}),
                {'recipe_text_and_urls': self.url},
                HTTP_ACCEPT='application/json'
            )
        
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
        assert data['status'] == 'success'
        assert '/meals/' in data['redirect']
       
    def test_scrape_recipe_invalid_url(self):
        """Test scraping with invalid URL"""
        self.login_user(self.user)
        
        with patch('main.views.get_recipe_text_from_url', side_effect=ValueError('Failed to access the recipe URL: Invalid URL')):
            response = self.client.post(
                reverse('main:scrape', kwargs={'collection_id': self.collection.id}),
                {'recipe_text_and_urls': 'https://notarealwebsite.com/recipe'},
                HTTP_ACCEPT='application/json'
            )
        
        assert response.status_code == 400
        data = response.json()
        assert data['status'] == 'error'
        assert 'Failed to access the recipe URL' in data['message']
    
    def test_scrape_recipe_server_error(self):
        """Test scraping with server error"""
        self.login_user(self.user)
        
        with patch('main.views.get_recipe_text_from_url', side_effect=Exception('Server error')):
            response = self.client.post(
                reverse('main:scrape', kwargs={'collection_id': self.collection.id}),
                {'recipe_text_and_urls': self.url},
                HTTP_ACCEPT='application/json'
            )
        
        assert response.status_code == 400
        data = response.json()
        assert data['status'] == 'error'
        assert 'Server error' in data['message']

    def test_scrape_recipe_allowed(self):
        """Test that a user is allowed to scrape if they share a meal plan with the collection owner."""
        allowed_user = UserFactory()
        # Assume allowed_user shares a meal plan with self.user
        allowed_user.memberships.create(meal_plan=self.collection.user.memberships.first().meal_plan)
        self.login_user(allowed_user)

        with patch('main.views.get_recipe_text_from_url', return_value=get_mock_recipe_text()), \
             patch('main.views.parse_recipe_with_genai', return_value=get_mock_parsed_recipe()):
            response = self.client.post(
                reverse('main:scrape', kwargs={'collection_id': self.collection.id}),
                {'recipe_text_and_urls': self.url}
            )

        assert response.status_code == 302  # Should redirect to collection detail
        assert '/meals/' in response['Location']

    def test_scrape_recipe_denied(self):
        """Test that a user is not allowed to scrape if they do not share a meal plan with the collection owner."""
        denied_user = UserFactory()
        self.login_user(denied_user)

        response = self.client.post(
            reverse('main:scrape', kwargs={'collection_id': self.collection.id}),
            {'recipe_text_and_urls': self.url}
        )

        assert response.status_code == 403  # Should return forbidden status


class TestRecipeDataSaving(BaseTestCase):
    @pytest.fixture(autouse=True)
    def setup_recipe_data(self, base_setup):
        """Set up test data for each test."""
        self.user = UserFactory()
        self.collection = CollectionFactory(user=self.user)
        self.recipe_data = {
            'title': 'Test Recipe',
            'description': 'A test recipe',
            'url': 'https://example.com/recipe',
            'recipes': [
                {
                    'title': 'Main Recipe',
                    'description': 'The main part',
                    'ingredients': [
                        {'name': 'flour', 'amount': '2', 'unit': 'cups'},
                        {'name': 'sugar', 'amount': '1', 'unit': 'cup'}
                    ],
                    'method': [
                        'Mix flour and sugar',
                        'Bake at 350F'
                    ]
                }
            ]
        }

    def test_create_new_meal(self):
        """Test creating a new meal from recipe data"""
        from main.ai_helpers import save_parsed_recipe

        meal, created = save_parsed_recipe(self.recipe_data, collection=self.collection)

        assert created is True
        assert meal.title == 'Test Recipe'
        assert meal.description == 'A test recipe'
        assert meal.url == 'https://example.com/recipe'
        assert meal.collection == self.collection

        # Check recipe was created
        assert meal.recipes.count() == 1
        recipe = meal.recipes.first()
        assert recipe.title == 'Main Recipe'
        assert recipe.description == 'The main part'

        # Check ingredients were created
        assert recipe.ingredients.count() == 2
        flour = recipe.ingredients.get(name='flour')
        assert flour.amount == '2'
        assert flour.unit == 'cups'

        # Check method steps were created
        assert recipe.method_steps.count() == 2
        assert 'Mix flour and sugar' in [s.description for s in recipe.method_steps.all()]

    def test_update_existing_meal(self):
        """Test updating an existing meal with new recipe data"""
        from main.ai_helpers import save_parsed_recipe

        # First create a meal
        meal, _ = save_parsed_recipe(self.recipe_data, collection=self.collection)

        # Now update it with new data
        updated_data = {
            'title': 'Updated Recipe',
            'description': 'An updated recipe',
            'url': 'https://example.com/updated',
            'recipes': [
                {
                    'title': 'New Version',
                    'description': 'The updated version',
                    'ingredients': [
                        {'name': 'chocolate', 'amount': '3', 'unit': 'oz'}
                    ],
                    'method': [
                        'Melt chocolate',
                        'Let cool'
                    ]
                }
            ]
        }

        updated_meal, created = save_parsed_recipe(updated_data, meal=meal)

        assert created is False
        assert updated_meal.id == meal.id  # Same meal
        assert updated_meal.title == 'Updated Recipe'
        assert updated_meal.url == 'https://example.com/updated'

        # Check recipe was updated
        assert updated_meal.recipes.count() == 1
        recipe = updated_meal.recipes.first()
        assert recipe.title == 'New Version'

        # Check ingredients were updated
        assert recipe.ingredients.count() == 1
        chocolate = recipe.ingredients.first()
        assert chocolate.name == 'chocolate'
        assert chocolate.amount == '3'

        # Check method steps were updated
        assert recipe.method_steps.count() == 2
        assert 'Melt chocolate' in [s.description for s in recipe.method_steps.all()]

    def test_save_recipe_without_collection_or_meal(self):
        """Test that save_parsed_recipe raises ValueError when neither collection nor meal is provided"""
        from main.ai_helpers import save_parsed_recipe

        with pytest.raises(ValueError, match="Must provide either a meal to update or a collection to create in"):
            save_parsed_recipe(self.recipe_data)

    def test_save_recipe_with_missing_fields(self):
        """Test that save_parsed_recipe handles missing optional fields gracefully"""
        from main.ai_helpers import save_parsed_recipe

        minimal_data = {
            'title': 'Minimal Recipe',
            'recipes': [
                {
                    'title': 'Basic',
                    'ingredients': [],
                    'method': []
                }
            ]
        }

        meal, created = save_parsed_recipe(minimal_data, collection=self.collection)

        assert created is True
        assert meal.title == 'Minimal Recipe'
        assert meal.description == ''  # Default empty string
        assert meal.url == ''  # Default empty string
        assert meal.recipes.count() == 1
        recipe = meal.recipes.first()
        assert recipe.title == 'Basic'
        assert recipe.description == ''
        assert recipe.ingredients.count() == 0
        assert recipe.method_steps.count() == 0
