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
                {'recipe_url': self.url}
            )
        
        assert response.status_code == 302  # Should redirect to collection detail
        assert '/meals/' in response['Location']
    
    def test_scrape_recipe_ajax(self):
        """Test recipe scraping via AJAX"""
        self.login_user(self.user)
        
        with patch('main.views.get_recipe_text_from_url', return_value=get_mock_recipe_text()), \
             patch('main.views.parse_recipe_with_genai', return_value=get_mock_parsed_recipe()):
            response = self.client.post(
                reverse('main:scrape', kwargs={'collection_id': self.collection.id}),
                {'recipe_url': self.url},
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
        
        #with patch('main.views.get_recipe_text_from_url', side_effect=ValueError('Invalid URL')):
        response = self.client.post(
            reverse('main:scrape', kwargs={'collection_id': self.collection.id}),
            {'recipe_url': 'not-a-url'},
            HTTP_ACCEPT='application/json'
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data['status'] == 'error'
        assert 'Invalid URL' in data['message']
    
    def test_scrape_recipe_server_error(self):
        """Test scraping with server error"""
        self.login_user(self.user)
        
        with patch('main.views.get_recipe_text_from_url', side_effect=Exception('Server error')):
            response = self.client.post(
                reverse('main:scrape', kwargs={'collection_id': self.collection.id}),
                {'recipe_url': self.url},
                HTTP_ACCEPT='application/json'
            )
        
        assert response.status_code == 400
        data = response.json()
        assert data['status'] == 'error'
        assert 'Server error' in data['message']
