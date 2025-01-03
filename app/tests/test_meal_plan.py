from django.test import TestCase, Client
from django.urls import reverse
from .factories import UserFactory, MealPlanFactory, MembershipFactory, MealFactory
from main.models import MealPlan, Membership
from pytest import mark

class TestMealPlanDetail(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = UserFactory()
        self.member = UserFactory()
        self.non_member = UserFactory()
        self.meal_plan = MealPlanFactory(owner=self.owner)
        
        # Create memberships
        MembershipFactory(user=self.owner, meal_plan=self.meal_plan)  # Owner membership
        MembershipFactory(user=self.member, meal_plan=self.meal_plan)  # Member membership
        
        # Add some meals to the plan
        self.meal1 = MealFactory()
        self.meal2 = MealFactory()
        self.meal_plan.meals.add(self.meal1, self.meal2)
        
        # URL for meal plan detail
        self.url = reverse('main:meal_plan_detail', kwargs={'shareable_link': self.meal_plan.shareable_link})

    def test_owner_view_permissions(self):
        """Owner should see edit button and member removal options"""
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_member'])
        self.assertContains(response, 'bi-pencil-square')  # Edit icon should be present
        self.assertContains(response, 'bi-person-x')  # Remove member icon should be present
        self.assertNotContains(response, 'Leave Plan')  # Owner shouldn't see leave button

    def test_member_view_permissions(self):
        """Members should see share link and grocery list edit, but not plan edit"""
        self.client.force_login(self.member)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_member'])
        self.assertContains(response, 'Leave Plan')  # Should see leave button
        self.assertContains(response, 'Share this meal plan')  # Should see share section
        self.assertContains(response, 'grocery-list-instruction')  # Should see editable grocery list
        self.assertNotContains(response, 'bi-pencil-square')  # Shouldn't see edit icon
        self.assertNotContains(response, 'bi-person-x')  # Shouldn't see remove member icon

    def test_non_member_view_permissions(self):
        """Non-members should see read-only view with join button"""
        self.client.force_login(self.non_member)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_member'])
        self.assertContains(response, 'Join Plan')  # Should see join button
        self.assertNotContains(response, 'Share this meal plan')  # Shouldn't see share section
        self.assertNotContains(response, 'grocery-list-instruction')  # Shouldn't see editable grocery list
        
        # Should see grocery list in read-only mode
        self.assertContains(response, '<pre class="bg-light p-4 rounded">')

    def test_unauthenticated_user_view_permissions(self):
        """Unauthenticated users should see read-only view with join button"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_member'])
        self.assertContains(response, 'Join Plan')  # Should see join button
        self.assertNotContains(response, 'Share this meal plan')  # Shouldn't see share section
        
        # Should see grocery list in read-only mode
        self.assertContains(response, '<pre class="bg-light p-4 rounded">')

    def test_meal_list_visibility(self):
        """All users should see the meal list, but only members see add/remove buttons"""
        # Check as member
        self.client.force_login(self.member)
        member_response = self.client.get(self.url)
        self.assertContains(member_response, 'Planned Meals')
        self.assertTrue(member_response.context['is_member'])
        self.assertContains(member_response, 'bi-check-circle-fill')  # Should see add/remove meal icons
        
        # Check as non-member
        self.client.force_login(self.non_member)
        non_member_response = self.client.get(self.url)
        self.assertContains(non_member_response, 'Planned Meals')
        self.assertFalse(non_member_response.context['is_member'])
        self.assertNotContains(non_member_response, 'bi-check-circle-fill')  # Shouldn't see add/remove meal icons


class TestMealPlanEdit(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = UserFactory()
        self.member = UserFactory()
        self.non_member = UserFactory()
        self.meal_plan = MealPlanFactory(owner=self.owner, name="Original Name")
        
        # Create memberships
        MembershipFactory(user=self.owner, meal_plan=self.meal_plan)
        MembershipFactory(user=self.member, meal_plan=self.meal_plan)
        
        # URLs
        self.edit_url = reverse('main:meal_plan_edit', kwargs={'shareable_link': self.meal_plan.shareable_link})
        self.detail_url = reverse('main:meal_plan_detail', kwargs={'shareable_link': self.meal_plan.shareable_link})

    def test_owner_can_access_edit_page(self):
        """Owner should be able to access the edit page"""
        self.client.force_login(self.owner)
        response = self.client.get(self.edit_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit Meal Plan')
        self.assertContains(response, self.meal_plan.name)

    def test_member_cannot_access_edit_page(self):
        """Members should be redirected with an error message"""
        self.client.force_login(self.member)
        response = self.client.get(self.edit_url)
        
        self.assertRedirects(response, self.detail_url)
        # Note: Django's messages framework doesn't work in tests by default
        # We could test for messages if needed by setting up message middleware

    def test_non_member_cannot_access_edit_page(self):
        """Non-members should be redirected with an error message"""
        self.client.force_login(self.non_member)
        response = self.client.get(self.edit_url)
        
        self.assertRedirects(response, self.detail_url)

    def test_unauthenticated_user_cannot_access_edit_page(self):
        """Unauthenticated users should be redirected to login"""
        response = self.client.get(self.edit_url)
        expected_url = f'/accounts/login/?next={self.edit_url}'
        self.assertRedirects(response, expected_url)

    def test_owner_can_edit_meal_plan(self):
        """Owner should be able to edit the meal plan name"""
        self.client.force_login(self.owner)
        new_name = "Updated Name"
        response = self.client.post(self.edit_url, {'name': new_name})
        
        self.assertRedirects(response, self.detail_url)
        self.meal_plan.refresh_from_db()
        self.assertEqual(self.meal_plan.name, new_name)

    def test_empty_name_validation(self):
        """Empty names should be rejected"""
        self.client.force_login(self.owner)
        response = self.client.post(self.edit_url, {'name': ''})
        
        self.assertEqual(response.status_code, 200)  # Stays on the same page
        self.meal_plan.refresh_from_db()
        self.assertEqual(self.meal_plan.name, "Original Name")  # Name unchanged
