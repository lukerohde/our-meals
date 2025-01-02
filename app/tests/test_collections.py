import pytest
from django.urls import reverse
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
from main.views import get_possessive_name
from .factories import UserFactory, CollectionFactory, MealPlanFactory, MembershipFactory

pytestmark = pytest.mark.django_db

def _create_session(user):
    """Create a session for the given user."""
    session = SessionStore()
    session[SESSION_KEY] = user.id
    session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()
    return session.session_key

class TestCollectionDetail:
    def test_get_collection_returns_200(self, client):
        # Arrange
        user = UserFactory()
        collection = CollectionFactory(user=user)
        client.force_login(user)
        
        # Act
        url = reverse('main:collection_detail', kwargs={'pk': collection.pk})
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        assert collection.title in response.content.decode()
    
    def test_get_collection_as_meal_plan_member_returns_200(self, client):
        # Arrange
        collection_owner = UserFactory()
        collection = CollectionFactory(user=collection_owner)
        
        other_user = UserFactory()
        meal_plan = MealPlanFactory()
        # Add both users to the meal plan
        MembershipFactory(user=collection_owner, meal_plan=meal_plan)
        MembershipFactory(user=other_user, meal_plan=meal_plan)
        
        client.force_login(other_user)
        
        # Act
        url = reverse('main:collection_detail', kwargs={'pk': collection.pk})
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        assert collection.title in response.content.decode()
    
    def test_get_collection_without_shared_meal_plan_returns_404(self, client):
        # Arrange
        collection_owner = UserFactory()
        collection = CollectionFactory(user=collection_owner)
        
        non_member = UserFactory()
        client.force_login(non_member)
        
        # Act
        url = reverse('main:collection_detail', kwargs={'pk': collection.pk})
        response = client.get(url)
        
        # Assert
        assert response.status_code == 404
    
    def test_get_collection_unauthenticated_redirects_to_login(self, client):
        # Arrange
        collection = CollectionFactory()
        
        # Act
        url = reverse('main:collection_detail', kwargs={'pk': collection.pk})
        response = client.get(url)
        
        # Assert
        assert response.status_code == 302
        assert '/login/' in response['Location']

class TestCollectionList:
    def test_list_own_collections(self, client):
        # Arrange
        user = UserFactory()
        collection1 = CollectionFactory(user=user, title="My Collection 1")
        collection2 = CollectionFactory(user=user, title="My Collection 2")
        client.force_login(user)
        
        # Act
        url = reverse('main:collection_list')
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        assert "Your Cook Books" in content
        assert collection1.title in content
        assert collection2.title in content

    def test_list_shared_collections(self, client):
        # Arrange
        user = UserFactory()
        other_user = UserFactory()
        
        # Create a meal plan and add both users
        meal_plan = MealPlanFactory()
        MembershipFactory(user=user, meal_plan=meal_plan)
        MembershipFactory(user=other_user, meal_plan=meal_plan)
        
        # Create collections for both users
        user_collection = CollectionFactory(user=user, title="User Collection")
        other_collection = CollectionFactory(user=other_user, title="Other Collection")
        
        client.force_login(user)
        
        # Act
        url = reverse('main:collection_list')
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        
        # Check that we got the expected collections in the context
        assert set(response.context['grouped_collections'].keys()) == {
            'Your Cook Books',
            f"{other_user.username.title()}'s Cook Books"
        }
        
        # Check that collections are displayed
        assert user_collection.title in response.content.decode()
        assert other_collection.title in response.content.decode()

    def test_dont_list_unshared_collections(self, client):
        # Arrange
        user = UserFactory()
        other_user = UserFactory()
        
        # Create collections for both users
        user_collection = CollectionFactory(user=user, title="User Collection")
        other_collection = CollectionFactory(user=other_user, title="Other Collection")
        
        client.force_login(user)
        
        # Act
        url = reverse('main:collection_list')
        response = client.get(url)
        
        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        assert "Your Cook Books" in content
        assert user_collection.title in content
        assert other_collection.title not in content
        assert get_possessive_name(other_user.username.title()) not in content

    def test_list_collections_unauthenticated_redirects_to_login(self, client):
        # Arrange
        CollectionFactory()  # Create a collection that shouldn't be visible
        
        # Act
        url = reverse('main:collection_list')
        response = client.get(url)
        
        # Assert
        assert response.status_code == 302
        assert '/login/' in response['Location']
