import pytest
from django.urls import reverse
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
from django.test import Client
from django.contrib.auth.models import User
from main.views import get_possessive_name
from main.models import Membership
from .factories import UserFactory, CollectionFactory, MealPlanFactory, MembershipFactory

pytestmark = pytest.mark.django_db

class BaseTestCase:
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


class TestCollectionDetail(BaseTestCase):
    @pytest.fixture(autouse=True)
    def test_setup(self, base_setup):
        """Set up test data for each test."""
        self.user = UserFactory()
        self.collection = CollectionFactory(user=self.user)
    
    def test_get_collection_returns_200(self):
        # Arrange
        self.login_user(self.user)
        
        # Act
        url = reverse('main:collection_detail', kwargs={'pk': self.collection.pk})
        response = self.client.get(url)
        
        # Assert
        assert response.status_code == 200
        assert self.collection.title in response.content.decode()
    
    def test_get_collection_as_meal_plan_member_returns_200(self):
        # Arrange
        other_user = UserFactory()
        meal_plan = MealPlanFactory()
        # Add both users to the meal plan
        MembershipFactory(user=self.user, meal_plan=meal_plan)
        MembershipFactory(user=other_user, meal_plan=meal_plan)
        
        self.login_user(other_user)
        
        # Act
        url = reverse('main:collection_detail', kwargs={'pk': self.collection.pk})
        response = self.client.get(url)
        
        # Assert
        assert response.status_code == 200
        assert self.collection.title in response.content.decode()
    
    def test_get_collection_without_shared_meal_plan_returns_404(self):
        # Arrange
        non_member = UserFactory()
        self.login_user(non_member)
        
        # Act
        url = reverse('main:collection_detail', kwargs={'pk': self.collection.pk})
        response = self.client.get(url)
        
        # Assert
        assert response.status_code == 404
    
    def test_get_collection_unauthenticated_redirects_to_login(self):
        # Act
        url = reverse('main:collection_detail', kwargs={'pk': self.collection.pk})
        response = self.client.get(url)
        
        # Assert
        assert response.status_code == 302
        assert '/login/' in response['Location']


class TestCollectionList(BaseTestCase):
    @pytest.fixture(autouse=True)
    def test_setup(self, base_setup):
        """Set up test data for each test."""
        self.user = UserFactory()
        self.collection = CollectionFactory(user=self.user)
    
    def test_list_own_collections(self):
        # Arrange
        self.login_user(self.user)
        
        # Act
        url = reverse('main:collection_list')
        response = self.client.get(url)
        
        # Assert
        assert response.status_code == 200
        assert self.collection.title in response.content.decode()
    
    def test_list_shared_collections(self):
        # Arrange
        other_user = UserFactory()
        other_collection = CollectionFactory(user=other_user)
        meal_plan = MealPlanFactory()
        MembershipFactory(user=self.user, meal_plan=meal_plan)
        MembershipFactory(user=other_user, meal_plan=meal_plan)
        
        self.login_user(self.user)
        
        # Act
        url = reverse('main:collection_list')
        response = self.client.get(url)
        
        # Assert
        assert response.status_code == 200
        assert other_collection.title in response.content.decode()
    
    def test_dont_list_unshared_collections(self):
        # Arrange
        other_user = UserFactory()
        other_collection = CollectionFactory(user=other_user)
        
        self.login_user(self.user)
        
        # Act
        url = reverse('main:collection_list')
        response = self.client.get(url)
        
        # Assert
        assert response.status_code == 200
        assert other_collection.title not in response.content.decode()
    
    def test_list_collections_unauthenticated_redirects_to_login(self):
        # Act
        url = reverse('main:collection_list')
        response = self.client.get(url)
        
        # Assert
        assert response.status_code == 302
        assert '/login/' in response['Location']


class TestMemberManagement(BaseTestCase):
    @pytest.fixture(autouse=True)
    def test_setup(self, base_setup):
        """Set up test data for each test."""
        self.owner = UserFactory()
        self.member = UserFactory()
        self.non_member = UserFactory()
        self.meal_plan = MealPlanFactory(owner=self.owner)
        MembershipFactory(user=self.member, meal_plan=self.meal_plan)
    
    def test_owner_can_remove_member(self):
        # Arrange
        self.login_user(self.owner)
        
        # Act
        url = reverse('main:remove_member', kwargs={
            'shareable_link': self.meal_plan.shareable_link,
            'member_id': self.member.id
        })
        response = self.client.post(url)
        
        # Assert
        assert response.status_code == 302
        assert response.url == reverse('main:collection_list')
        assert not Membership.objects.filter(
            user=self.member,
            meal_plan=self.meal_plan
        ).exists()
    
    def test_non_owner_cannot_remove_member(self):
        # Arrange
        self.login_user(self.member)  # Login as member, not owner
        
        # Act
        url = reverse('main:remove_member', kwargs={
            'shareable_link': self.meal_plan.shareable_link,
            'member_id': self.member.id
        })
        response = self.client.post(url)
        
        # Assert
        assert response.status_code == 403
        assert Membership.objects.filter(
            user=self.member,
            meal_plan=self.meal_plan
        ).exists()
    
    def test_cannot_remove_non_member(self):
        # Arrange
        self.login_user(self.owner)
        
        # Act
        url = reverse('main:remove_member', kwargs={
            'shareable_link': self.meal_plan.shareable_link,
            'member_id': self.non_member.id
        })
        response = self.client.post(url)
        
        # Assert
        assert response.status_code == 404
    
    def test_cannot_remove_from_nonexistent_meal_plan(self):
        # Arrange
        self.login_user(self.owner)
        
        # Act
        url = reverse('main:remove_member', kwargs={
            'shareable_link': '12345678-1234-5678-1234-567812345678',  
            'member_id': self.member.id
        })
        response = self.client.post(url)
        
        # Assert
        assert response.status_code == 404
