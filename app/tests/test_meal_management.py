import pytest
from django.urls import reverse
from .test_base import MealPlanTestCase

pytestmark = pytest.mark.django_db

class TestMealManagement(MealPlanTestCase):
    def test_toggle_meal_in_meal_plan(self):
        """Test adding and removing a meal from meal plan"""
        self.login_user(self.user)
        
        # Initially meal should not be in plan
        assert not self.meal_plan.meals.filter(id=self.meal.id).exists()
        
        # Add meal to plan
        response = self.client.post(
            reverse('main:toggle_meal_in_meal_plan', kwargs={
                'shareable_link': self.meal_plan.shareable_link,
                'meal_id': self.meal.id
            }),
            HTTP_REFERER='/collections/'
        )
        
        # Check redirect and message
        self.assert_redirect_with_message(
            response,
            '/collections/',
            'added to meal plan',
            fetch_redirect=False
        )
        
        # Verify meal was added
        assert self.meal_plan.meals.filter(id=self.meal.id).exists()
        
        # Remove meal from plan
        response = self.client.post(
            reverse('main:toggle_meal_in_meal_plan', kwargs={
                'shareable_link': self.meal_plan.shareable_link,
                'meal_id': self.meal.id
            }),
            HTTP_REFERER='/collections/'
        )
        
        # Check redirect and message
        self.assert_redirect_with_message(
            response,
            '/collections/',
            'removed from meal plan',
            fetch_redirect=False
        )
        
        # Verify meal was removed
        assert not self.meal_plan.meals.filter(id=self.meal.id).exists()
    
    def test_toggle_shared_meal_in_meal_plan(self):
        """Test toggling a meal from a user who shares a meal plan"""
        self.login_user(self.user)
        
        # Add shared meal to plan
        response = self.client.post(
            reverse('main:toggle_meal_in_meal_plan', kwargs={
                'shareable_link': self.meal_plan.shareable_link,
                'meal_id': self.shared_meal.id
            }),
            HTTP_REFERER='/collections/'
        )
        
        # Check redirect and message
        self.assert_redirect_with_message(
            response,
            '/collections/',
            'added to meal plan',
            fetch_redirect=False
        )
        
        # Verify meal was added
        assert self.meal_plan.meals.filter(id=self.shared_meal.id).exists()
    
    def test_toggle_meal_unauthorized(self):
        """Test that unauthorized users can't toggle meals"""
        url_path = reverse('main:toggle_meal_in_meal_plan', kwargs={
            'shareable_link': self.meal_plan.shareable_link,
            'meal_id': self.meal.id
        })
        
        # Try without login
        response = self.client.post(url_path)
        self.assertRedirects(response, f'/accounts/login/?next={url_path}')
        
        # Try with non-member
        self.login_user(self.other_user)
        response = self.client.post(url_path)
        assert response.status_code == 404
        
        # Verify meal was not added
        assert not self.meal_plan.meals.filter(id=self.meal.id).exists()
    
    def test_delete_meal(self):
        """Test deleting a meal"""
        self.login_user(self.user)
        
        # Delete meal
        response = self.client.post(
            reverse('main:delete_meal', kwargs={'pk': self.meal.id}),
            HTTP_REFERER='/collections/'
        )
        
        # Check redirect and message
        self.assert_redirect_with_message(
            response,
            '/collections/',
            f"{self.meal.title} has been deleted!",
            fetch_redirect=False
        )
        
        # Verify meal was deleted
        assert not self.collection.meals.filter(id=self.meal.id).exists()
    
    def test_delete_meal_unauthorized(self):
        """Test that unauthorized users can't delete meals"""
        url_path = reverse('main:delete_meal', kwargs={'pk': self.meal.id})
        
        # Try without login
        response = self.client.post(url_path)
        self.assertRedirects(response, f'/accounts/login/?next={url_path}')
        
        # Try with non-owner
        self.login_user(self.other_user)
        response = self.client.post(url_path)
        assert response.status_code == 404
        
        # Verify meal was not deleted
        assert self.collection.meals.filter(id=self.meal.id).exists()
