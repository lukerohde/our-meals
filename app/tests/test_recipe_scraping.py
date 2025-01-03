import pytest
from django.urls import reverse
from unittest.mock import patch
from .test_base import BaseTestCase
from .factories import UserFactory, CollectionFactory

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
        
        # Mock the scraping response
        mock_recipe = {
            'title': 'Test Recipe',
            'description': 'A delicious test recipe',
            'ingredients': ['1 cup test', '2 tbsp mock'],
            'method': ['Step 1', 'Step 2'],
            'photo_url': 'https://example.com/photo.jpg'
        }
        
        with patch('main.views.scrape_recipe_from_url', return_value=mock_recipe):
            response = self.client.post(
                reverse('main:scrape', kwargs={'collection_id': self.collection.id}),
                {'url': self.url},
                HTTP_REFERER='/collections/'
            )
        
        # Get the newly created meal ID from the redirect URL
        meal_id = response['Location'].split('/')[-2]
        
        # Check redirect and message
        self.assert_redirect_with_message(
            response,
            f'/meals/{meal_id}/',
            'Recipe successfully imported!',
            fetch_redirect=False
        )
    
    def test_scrape_recipe_ajax(self):
        """Test recipe scraping via AJAX"""
        self.login_user(self.user)
        
        # Mock the scraping response
        mock_recipe = {
            'title': 'Test Recipe',
            'description': 'A delicious test recipe',
            'ingredients': ['1 cup test', '2 tbsp mock'],
            'method': ['Step 1', 'Step 2'],
            'photo_url': 'https://example.com/photo.jpg'
        }
        
        with patch('main.views.scrape_recipe_from_url', return_value=mock_recipe):
            response = self.client.post(
                reverse('main:scrape', kwargs={'collection_id': self.collection.id}),
                {'url': self.url},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                HTTP_ACCEPT='application/json'
            )
        
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
        assert data['status'] == 'success'
        assert 'message' in data
        assert data['message'] == 'Recipe successfully imported!'
        assert 'redirect' in data
        assert '/meals/' in data['redirect']
    
    def test_scrape_recipe_invalid_url(self):
        """Test scraping with invalid URL"""
        self.login_user(self.user)
        
        with patch('main.views.scrape_recipe_from_url', side_effect=ValueError('Invalid URL')):
            response = self.client.post(
                reverse('main:scrape', kwargs={'collection_id': self.collection.id}),
                {'url': 'not-a-url'},
                HTTP_REFERER='/collections/'
            )
        
        # Check redirect and message
        self.assert_redirect_with_message(
            response,
            f'/collections/{self.collection.id}/',
            'Invalid URL',
            fetch_redirect=False
        )
    
    def test_scrape_recipe_server_error(self):
        """Test scraping with server error"""
        self.login_user(self.user)
        
        with patch('main.views.scrape_recipe_from_url', side_effect=Exception('Server error')):
            response = self.client.post(
                reverse('main:scrape', kwargs={'collection_id': self.collection.id}),
                {'url': self.url},
                HTTP_REFERER='/collections/'
            )
        
        # Check redirect and message
        self.assert_redirect_with_message(
            response,
            f'/collections/{self.collection.id}/',
            'An unexpected error occurred',
            fetch_redirect=False
        )
