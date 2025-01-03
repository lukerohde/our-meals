import pytest
from django.test import Client, TestCase
from django.contrib.messages import get_messages
from django.urls import reverse
from .factories import UserFactory, CollectionFactory, MealFactory, MealPlanFactory, MembershipFactory

pytestmark = pytest.mark.django_db

class BaseTestCase(TestCase):
    """Base test class with common authentication and setup methods."""
    
    @pytest.fixture(autouse=True)
    def base_setup(self):
        """Set up test client for each test."""
        self.client = Client()
    
    def login_user(self, user):
        """Log in a user and create their session."""
        self.client.force_login(user)
    
    def create_and_login_user(self):
        """Create a new user and log them in."""
        user = UserFactory()
        self.login_user(user)
        return user
    
    def get_messages_list(self, response):
        """Get list of messages from response."""
        return list(get_messages(response.wsgi_request))
    
    def assert_redirect_with_message(self, response, redirect_url, message_text, fetch_redirect=False):
        """Assert that response redirects and contains expected message."""
        self.assertRedirects(response, redirect_url, fetch_redirect_response=fetch_redirect)
        messages = self.get_messages_list(response)
        self.assertIn(message_text, str(messages[-1]))


class MealPlanTestCase(BaseTestCase):
    """Base test class for meal plan related tests."""
    
    @pytest.fixture(autouse=True)
    def meal_plan_setup(self, base_setup):
        """Set up common meal plan test data."""
        # Create users
        self.user = UserFactory()
        self.other_user = UserFactory()
        self.shared_user = UserFactory()
        
        # Create collection and meal
        self.collection = CollectionFactory(user=self.user)
        self.meal = MealFactory(collection=self.collection)
        self.shared_collection = CollectionFactory(user=self.shared_user)
        self.shared_meal = MealFactory(collection=self.shared_collection)
        
        # Create meal plan and membership
        self.meal_plan = MealPlanFactory(owner=self.user)
        MembershipFactory(user=self.user, meal_plan=self.meal_plan)
        # Add shared user to meal plan
        MembershipFactory(user=self.shared_user, meal_plan=self.meal_plan)
