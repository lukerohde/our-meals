import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from .test_base import MealPlanTestCase
from .factories import UserFactory, MealPlanFactory
from main.models import Membership

pytestmark = pytest.mark.django_db

class TestMealPlanMembership(MealPlanTestCase):
    def setUp(self):
        super().setUp()
        self.non_member = UserFactory()
        self.join_url = reverse('main:join_meal_plan', kwargs={'shareable_link': self.meal_plan.shareable_link})
        self.leave_url = reverse('main:leave_meal_plan', kwargs={'shareable_link': self.meal_plan.shareable_link})
        self.detail_url = reverse('main:meal_plan_detail', kwargs={'shareable_link': self.meal_plan.shareable_link})
        self.login_url = '/accounts/login/'
        self.signup_url = '/accounts/signup/'

    def test_authenticated_user_can_join_meal_plan(self):
        """Test that an authenticated user can join a meal plan"""
        self.login_user(self.non_member)
        response = self.client.post(self.join_url)
        
        # Should redirect back to meal plan
        self.assertRedirects(response, self.detail_url)
        
        # Should be a member now
        self.assertTrue(
            Membership.objects.filter(
                user=self.non_member, 
                meal_plan=self.meal_plan
            ).exists()
        )

    def test_authenticated_user_can_leave_meal_plan(self):
        """Test that a member can leave a meal plan"""
        # First join the meal plan
        self.login_user(self.non_member)
        self.client.post(self.join_url)
        
        # Then leave it
        response = self.client.post(self.leave_url)
        
        # Should redirect to home
        self.assertRedirects(response, '/')
        
        # Should not be a member anymore
        self.assertFalse(
            Membership.objects.filter(
                user=self.non_member, 
                meal_plan=self.meal_plan
            ).exists()
        )

    def test_owner_cannot_leave_meal_plan(self):
        """Test that the owner cannot leave their own meal plan"""
        self.login_user(self.user)  # self.user is the owner
        response = self.client.post(self.leave_url)
        
        # Should redirect back to meal plan with error message
        self.assert_redirect_with_message(
            response, 
            self.detail_url,
            "Owners cannot leave their own meal plan"
        )
        
        # Should still be a member
        self.assertTrue(
            Membership.objects.filter(
                user=self.user, 
                meal_plan=self.meal_plan
            ).exists()
        )

    def test_unauthenticated_user_redirected_to_login(self):
        """Test that unauthenticated users are redirected to signup"""
        # Try to join without being logged in
        response = self.client.post(self.join_url)
        
        # Should be redirected to signup
        self.assertRedirects(response, '/accounts/signup/')
        
        # The shareable link should be stored in session
        self.assertEqual(
            str(self.meal_plan.shareable_link),
            self.client.session['joining_shareable_link']
        )

    def test_join_from_login_flow(self):
        """Test joining after login redirect works"""
        # First try to join while logged out
        response = self.client.post(self.join_url)
        self.assertRedirects(response, '/accounts/signup/')
        
        # Verify the shareable link is stored in session
        self.assertEqual(
            str(self.meal_plan.shareable_link),
            self.client.session['joining_shareable_link']
        )
        
        # Create a new session for login to avoid middleware issues
        session = self.client.session
        session['joining_shareable_link'] = str(self.meal_plan.shareable_link)
        session.save()
        
        # Now login
        self.login_user(self.non_member)
        
        # Should be a member now due to the login signal
        self.assertTrue(
            Membership.objects.filter(
                user=self.non_member, 
                meal_plan=self.meal_plan
            ).exists()
        )

    def test_join_from_signup_flow(self):
        """Test joining after signup redirect works"""
        # First try to join while logged out
        response = self.client.post(self.join_url)
        
        # Should be redirected to signup
        self.assertRedirects(response, '/accounts/signup/')
        
        # Verify the shareable link is stored in session
        self.assertEqual(
            str(self.meal_plan.shareable_link),
            self.client.session['joining_shareable_link']
        )
        
        # Create a new session for login to avoid middleware issues
        session = self.client.session
        session['joining_shareable_link'] = str(self.meal_plan.shareable_link)
        session.save()
        
        # Create and login a new user (simulating signup)
        new_user = UserFactory()
        self.login_user(new_user)
        
        # Should be a member now due to the login signal
        self.assertTrue(
            Membership.objects.filter(
                user=new_user, 
                meal_plan=self.meal_plan
            ).exists()
        )
