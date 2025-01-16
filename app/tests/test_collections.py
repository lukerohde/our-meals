import pytest
from django.urls import reverse
from .test_base import BaseTestCase
from .factories import UserFactory, CollectionFactory, MealPlanFactory, MembershipFactory

pytestmark = pytest.mark.django_db

class TestCollectionDetail(BaseTestCase):
    @pytest.fixture(autouse=True)
    def setup_collection(self, base_setup):
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
    def setup_collection(self, base_setup):
        """Set up test data for each test."""
        self.user = UserFactory()
        self.collection = CollectionFactory(user=self.user)
    
    def test_list_own_collections(self):
        # Arrange
        self.login_user(self.user)
        
        # Act
        response = self.client.get(reverse('main:collection_list'))
        
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
        response = self.client.get(reverse('main:collection_list'))
        
        # Assert
        assert response.status_code == 302
        assert '/login/' in response['Location']


class TestMemberManagement(BaseTestCase):
    @pytest.fixture(autouse=True)
    def setup_membership(self, base_setup):
        """Set up test data for each test."""
        self.owner = UserFactory()
        self.member = UserFactory()
        self.non_member = UserFactory()
        self.meal_plan = MealPlanFactory(owner=self.owner)
        self.membership = MembershipFactory(user=self.member, meal_plan=self.meal_plan)
    
    def test_owner_can_remove_member(self):
        # Arrange
        self.login_user(self.owner)
        
        # Act
        response = self.client.post(
            reverse('main:remove_member', kwargs={
                'shareable_link': self.meal_plan.shareable_link,
                'member_id': self.member.id
            })
        )
        
        # Assert
        assert response.status_code == 302
        assert not self.meal_plan.memberships.filter(user_id=self.member.id).exists()
    
    def test_non_owner_cannot_remove_member(self):
        # Arrange
        non_owner = UserFactory()
        self.login_user(non_owner)
        
        # Act
        response = self.client.post(
            reverse('main:remove_member', kwargs={
                'shareable_link': self.meal_plan.shareable_link,
                'member_id': self.member.id
            })
        )
        
        # Assert
        assert response.status_code == 403
        assert self.meal_plan.memberships.filter(user_id=self.member.id).exists()
    
    def test_cannot_remove_non_member(self):
        # Arrange
        self.login_user(self.owner)
        non_member = UserFactory()
        
        # Act
        response = self.client.post(
            reverse('main:remove_member', kwargs={
                'shareable_link': self.meal_plan.shareable_link,
                'member_id': non_member.id
            })
        )
        
        # Assert
        assert response.status_code == 404
    
    def test_cannot_remove_from_nonexistent_meal_plan(self):
        # Arrange
        self.login_user(self.owner)
        
        # Act
        response = self.client.post(
            reverse('main:remove_member', kwargs={
                'shareable_link': '12345678-1234-5678-1234-567812345678',
                'member_id': self.member.id
            })
        )
        
        # Assert
        assert response.status_code == 404


class TestCollectionEdit(BaseTestCase):
    @pytest.fixture(autouse=True)
    def setup_collection(self, base_setup):
        """Set up test data for each test."""
        self.user = UserFactory()
        self.collection = CollectionFactory(user=self.user)
        self.edit_url = reverse('main:collection_edit', kwargs={'pk': self.collection.pk})
    
    def test_owner_can_access_edit_page(self):
        # Arrange
        self.login_user(self.user)
        
        # Act
        response = self.client.get(self.edit_url)
        
        # Assert
        assert response.status_code == 200
        assert 'Edit Cook Book' in response.content.decode()
    
    def test_owner_can_edit_collection(self):
        # Arrange
        self.login_user(self.user)
        new_title = "Updated Collection Title"
        new_description = "Updated collection description"
        
        # Act
        response = self.client.post(self.edit_url, {
            'title': new_title,
            'description': new_description,
        })
        
        # Assert
        assert response.status_code == 302  # Redirect after successful edit
        self.collection.refresh_from_db()
        assert self.collection.title == new_title
        assert self.collection.description == new_description
    
    def test_non_owner_cannot_access_edit_page(self):
        # Arrange
        other_user = UserFactory()
        self.login_user(other_user)
        
        # Act
        response = self.client.get(self.edit_url)
        
        # Assert
        assert response.status_code == 302  # Redirect to detail page
        
    def test_non_owner_cannot_edit_collection(self):
        # Arrange
        other_user = UserFactory()
        self.login_user(other_user)
        original_title = self.collection.title
        
        # Act
        response = self.client.post(self.edit_url, {
            'title': 'Attempted title change',
            'description': 'Attempted description change',
        })
        
        # Assert
        assert response.status_code == 302  # Redirect to detail page
        self.collection.refresh_from_db()
        assert self.collection.title == original_title  # Title should not have changed
    
    def test_unauthenticated_cannot_access_edit_page(self):
        # Act
        response = self.client.get(self.edit_url)
        
        # Assert
        assert response.status_code == 302
        assert '/login/' in response['Location']
