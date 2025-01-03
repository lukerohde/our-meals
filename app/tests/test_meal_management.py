from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from .factories import UserFactory, CollectionFactory, MealFactory, MealPlanFactory, MembershipFactory

class TestMealManagement(TestCase):
    def setUp(self):
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

    def login_user(self, user):
        self.client.force_login(user)
        
    def test_toggle_meal_in_meal_plan(self):
        """Test adding and removing a meal from meal plan"""
        self.login_user(self.user)
        
        # Initially meal should not be in plan
        self.assertFalse(self.meal_plan.meals.filter(id=self.meal.id).exists())
        
        # Add meal to plan
        response = self.client.post(
            reverse('main:toggle_meal_in_meal_plan', kwargs={
                'shareable_link': self.meal_plan.shareable_link,
                'meal_id': self.meal.id
            }),
            HTTP_REFERER='/collections/'
        )
        
        # Check redirect and message
        self.assertRedirects(response, '/collections/', fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(f"{self.meal.title} added to meal plan!", str(messages[0]))
        
        # Verify meal was added
        self.meal_plan.refresh_from_db()
        self.assertTrue(self.meal_plan.meals.filter(id=self.meal.id).exists())
        
        # Get fresh request for second operation
        response = self.client.post(
            reverse('main:toggle_meal_in_meal_plan', kwargs={
                'shareable_link': self.meal_plan.shareable_link,
                'meal_id': self.meal.id
            }),
            HTTP_REFERER='/collections/'
        )
        
        # Check redirect and message
        self.assertRedirects(response, '/collections/', fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(f"{self.meal.title} removed from meal plan!", str(messages[-1]))
        
        # Verify meal was removed
        self.meal_plan.refresh_from_db()
        self.assertFalse(self.meal_plan.meals.filter(id=self.meal.id).exists())
        
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
        self.assertRedirects(response, '/collections/', fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('added to meal plan', str(messages[0]))
        
        # Verify meal was added
        self.meal_plan.refresh_from_db()
        self.assertIn(self.shared_meal, self.meal_plan.meals.all())
        
    def test_toggle_meal_unauthorized(self):
        """Test that unauthorized users can't toggle meals"""
        url_path = reverse('main:toggle_meal_in_meal_plan', kwargs={
            'shareable_link': self.meal_plan.shareable_link,
            'meal_id': self.meal.id
        })
        
        # Try without login
        response = self.client.post(url_path)
        self.assertRedirects(response, f'/accounts/login/?next={url_path}')
        
        # Try with different user who doesn't share any meal plans
        self.login_user(self.other_user)
        response = self.client.post(url_path)
        self.assertEqual(response.status_code, 404)  # Should 404 since other user has no access
        
    def test_delete_meal(self):
        """Test deleting a meal"""
        self.login_user(self.user)
        
        response = self.client.post(
            reverse('main:delete_meal', kwargs={'pk': self.meal.id}),
            HTTP_REFERER='/collections/'
        )
        
        # Check redirect and message
        self.assertRedirects(response, '/collections/', fetch_redirect_response=False)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('has been deleted', str(messages[0]))
        
        # Verify meal was deleted
        self.assertFalse(self.collection.meals.filter(id=self.meal.id).exists())
        
    def test_delete_meal_unauthorized(self):
        """Test that unauthorized users can't delete meals"""
        url_path = reverse('main:delete_meal', kwargs={'pk': self.meal.id})
        
        # Try without login
        response = self.client.post(url_path)
        self.assertRedirects(response, f'/accounts/login/?next={url_path}')
        
        # Try with different user
        self.login_user(self.other_user)
        response = self.client.post(url_path)
        self.assertEqual(response.status_code, 404)
        
    def test_delete_nonexistent_meal(self):
        """Test deleting a meal that doesn't exist"""
        self.login_user(self.user)
        
        response = self.client.post(
            reverse('main:delete_meal', kwargs={'pk': 99999}),
            HTTP_REFERER='/collections/'
        )
        self.assertEqual(response.status_code, 404)
