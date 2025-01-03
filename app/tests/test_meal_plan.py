from django.test import TestCase, Client
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from .factories import UserFactory, MealPlanFactory, MembershipFactory, MealFactory, CollectionFactory, RecipeFactory, IngredientFactory
from main.models import MealPlan, Membership
from pytest import mark
from .test_base import MealPlanTestCase
from unittest.mock import patch

class TestMealPlanDetail(MealPlanTestCase):
    def setUp(self):
        super().setUp()
        self.member = UserFactory()
        self.non_member = UserFactory()
        
        # Create member membership (owner membership already created in base)
        MembershipFactory(user=self.member, meal_plan=self.meal_plan)
        
        # Add some meals to the plan
        self.meal1 = MealFactory()
        self.meal2 = MealFactory()
        self.meal_plan.meals.add(self.meal1, self.meal2)
        
        # URL for meal plan detail
        self.url = reverse('main:meal_plan_detail', kwargs={'shareable_link': self.meal_plan.shareable_link})

    def test_owner_view_permissions(self):
        """Owner should see edit button and member removal options"""
        self.login_user(self.user)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_member'])
        self.assertContains(response, 'bi-pencil-square')  # Edit icon should be present
        self.assertContains(response, 'bi-person-x')  # Remove member icon should be present
        self.assertNotContains(response, 'Leave Plan')  # Owner shouldn't see leave button

    def test_member_view_permissions(self):
        """Members should see share link and grocery list edit, but not plan edit"""
        self.login_user(self.member)
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
        self.login_user(self.non_member)
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
        self.login_user(self.member)
        member_response = self.client.get(self.url)
        self.assertContains(member_response, 'Planned Meals')
        self.assertTrue(member_response.context['is_member'])
        self.assertContains(member_response, 'bi-check-circle-fill')  # Should see add/remove meal icons
        
        # Check as non-member
        self.login_user(self.non_member)
        non_member_response = self.client.get(self.url)
        self.assertContains(non_member_response, 'Planned Meals')
        self.assertFalse(non_member_response.context['is_member'])
        self.assertNotContains(non_member_response, 'bi-check-circle-fill')  # Shouldn't see add/remove meal icons


class TestMealPlanEdit(MealPlanTestCase):
    def setUp(self):
        super().setUp()
        self.member = UserFactory()
        self.non_member = UserFactory()
        self.meal_plan.name = "Original Name"
        self.meal_plan.save()
        
        # Create member membership (owner membership already created in base)
        MembershipFactory(user=self.member, meal_plan=self.meal_plan)
        
        # URLs
        self.edit_url = reverse('main:meal_plan_edit', kwargs={'shareable_link': self.meal_plan.shareable_link})
        self.detail_url = reverse('main:meal_plan_detail', kwargs={'shareable_link': self.meal_plan.shareable_link})

    def test_owner_can_access_edit_page(self):
        """Owner should be able to access the edit page"""
        self.login_user(self.user)
        response = self.client.get(self.edit_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit Meal Plan')
        self.assertContains(response, self.meal_plan.name)

    def test_member_cannot_access_edit_page(self):
        """Members should be redirected with an error message"""
        self.login_user(self.member)
        response = self.client.get(self.edit_url)
        
        self.assertRedirects(response, self.detail_url)

    def test_non_member_cannot_access_edit_page(self):
        """Non-members should be redirected with an error message"""
        self.login_user(self.non_member)
        response = self.client.get(self.edit_url)
        
        self.assertRedirects(response, self.detail_url)

    def test_unauthenticated_user_cannot_access_edit_page(self):
        """Unauthenticated users should be redirected to login"""
        response = self.client.get(self.edit_url)
        expected_url = f'/accounts/login/?next={self.edit_url}'
        self.assertRedirects(response, expected_url)

    def test_owner_can_edit_meal_plan(self):
        """Owner should be able to edit the meal plan name"""
        self.login_user(self.user)
        new_name = "Updated Name"
        response = self.client.post(self.edit_url, {'name': new_name})
        
        self.assertRedirects(response, self.detail_url)
        self.meal_plan.refresh_from_db()
        self.assertEqual(self.meal_plan.name, new_name)

    def test_empty_name_validation(self):
        """Empty names should be rejected"""
        self.login_user(self.user)
        response = self.client.post(self.edit_url, {'name': ''})
        
        self.assertEqual(response.status_code, 200)  # Stays on the same page
        self.meal_plan.refresh_from_db()
        self.assertEqual(self.meal_plan.name, "Original Name")  # Name unchanged


class TestMealPlanToggle(MealPlanTestCase):
    def setUp(self):
        super().setUp()
        self.member = UserFactory()
        self.non_member = UserFactory()
        
        # Create member membership (owner membership already created in base)
        MembershipFactory(user=self.member, meal_plan=self.meal_plan)
        
        # URLs
        self.toggle_url = reverse('main:toggle_meal_in_meal_plan', kwargs={
            'shareable_link': self.meal_plan.shareable_link,
            'meal_id': self.meal.id
        })
        self.meal_plan_url = reverse('main:meal_plan_detail', kwargs={
            'shareable_link': self.meal_plan.shareable_link
        })

    def test_owner_can_toggle_meal(self):
        """Owner should be able to add and remove meals"""
        self.login_user(self.user)
        
        # Initially meal should not be in plan
        self.assertFalse(self.meal_plan.meals.filter(id=self.meal.id).exists())
        
        # Add meal to plan
        response = self.client.post(
            self.toggle_url,
            HTTP_REFERER=self.meal_plan_url
        )
        
        # Should redirect back to meal plan page
        self.assertRedirects(response, self.meal_plan_url)
        # Meal should be added
        self.assertTrue(self.meal_plan.meals.filter(id=self.meal.id).exists())
        
        # Remove meal from plan
        response = self.client.post(
            self.toggle_url,
            HTTP_REFERER=self.meal_plan_url
        )
        
        # Should redirect back to meal plan page
        self.assertRedirects(response, self.meal_plan_url)
        # Meal should be removed
        self.assertFalse(self.meal_plan.meals.filter(id=self.meal.id).exists())

    def test_member_can_toggle_meal(self):
        """Members should be able to add and remove meals"""
        self.login_user(self.member)
        
        # Add meal to plan
        response = self.client.post(
            self.toggle_url,
            HTTP_REFERER=self.meal_plan_url
        )
        
        # Should redirect back to meal plan page
        self.assertRedirects(response, self.meal_plan_url)
        # Meal should be added
        self.assertTrue(self.meal_plan.meals.filter(id=self.meal.id).exists())

    def test_non_member_cannot_toggle_meal(self):
        """Non-members should not be able to toggle meals"""
        self.login_user(self.non_member)
        
        # Try to add meal to plan
        response = self.client.post(
            self.toggle_url,
            HTTP_REFERER=self.meal_plan_url
        )
        
        # Should return 404 (not found)
        self.assertEqual(response.status_code, 404)
        # Meal should not be added
        self.assertFalse(self.meal_plan.meals.filter(id=self.meal.id).exists())

    def test_unauthenticated_user_cannot_toggle_meal(self):
        """Unauthenticated users should be redirected to login"""
        response = self.client.post(
            self.toggle_url,
            HTTP_REFERER=self.meal_plan_url
        )
        
        expected_url = f'/accounts/login/?next={self.toggle_url}'
        self.assertRedirects(response, expected_url)
        # Meal should not be added
        self.assertFalse(self.meal_plan.meals.filter(id=self.meal.id).exists())

    def test_toggle_respects_referer(self):
        """Toggle should redirect back to referring page"""
        self.login_user(self.user)
        
        # Try toggle from collection page
        collection_url = reverse('main:collection_detail', kwargs={'pk': self.collection.pk})
        response = self.client.post(
            self.toggle_url,
            HTTP_REFERER=collection_url
        )
        
        # Should redirect back to collection page
        self.assertRedirects(response, collection_url)


class TestGroceryList(MealPlanTestCase):
    """Tests for grocery list functionality"""
    
    @pytest.fixture(autouse=True)
    def grocery_list_setup(self, meal_plan_setup):
        """Set up test data for grocery list tests"""
        self.url = reverse('main:create_grocery_list', kwargs={'shareable_link': self.meal_plan.shareable_link})
        
        # Add meal to plan
        self.meal_plan.meals.add(self.meal)
        
        # Create recipe with ingredients
        self.recipe = RecipeFactory(meal=self.meal)
        IngredientFactory(recipe=self.recipe, name='Milk', amount='1', unit='cup')
        IngredientFactory(recipe=self.recipe, name='Cinnamon', amount='2', unit='tbsp')
        
        # Set member for testing
        self.member = self.shared_user
    
    def test_create_grocery_list_requires_auth(self):
        """Test that creating grocery list requires authentication"""
        response = self.client.post(self.url)
        self.assertRedirects(response, f'/accounts/login/?next={self.url}')
    
    def test_create_grocery_list_requires_post(self):
        """Test that creating grocery list requires POST method"""
        self.login_user(self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)  # Method not allowed
    
    def test_create_grocery_list_success(self):
        """Test successful grocery list creation"""
        self.login_user(self.member)
        instruction = "Organize by aisle"
        
        mock_response = """```
Dairy:
- Milk (1 cup) - Test Recipe from Test Meal

Spices:
- Cinnamon (2 tbsp) - Test Recipe from Test Meal
```"""
        with patch('main.ai_helpers.OpenAI') as mock_openai:
            # Mock the chat completion
            mock_chat = mock_openai.return_value.chat.completions
            mock_chat.create.return_value.choices[0].message.content = mock_response
            
            response = self.client.post(self.url, {'grocery_list_instruction': instruction})
        
        # Should redirect back to meal plan
        self.assertRedirects(response, reverse('main:meal_plan_detail', kwargs={'shareable_link': self.meal_plan.shareable_link}))
        
        # Refresh meal plan from db
        self.meal_plan.refresh_from_db()
        self.assertEqual(self.meal_plan.grocery_list_instruction, instruction)
        self.assertEqual(self.meal_plan.grocery_list, mock_response)

    def test_create_grocery_list_non_member_forbidden(self):
        """Test that non-members cannot create grocery lists"""
        non_member = UserFactory()
        self.login_user(non_member)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)
    
    def test_create_grocery_list_empty_instruction(self):
        """Test grocery list creation with empty instruction"""
        self.login_user(self.member)
        
        mock_response = """```
Dairy:
- Milk (1 cup) - Test Recipe from Test Meal

Spices:
- Cinnamon (2 tbsp) - Test Recipe from Test Meal
```"""
        with patch('main.ai_helpers.OpenAI') as mock_openai:
            mock_chat = mock_openai.return_value.chat.completions
            mock_chat.create.return_value.choices[0].message.content = mock_response
            
            response = self.client.post(self.url)
        
        self.assertRedirects(response, reverse('main:meal_plan_detail', kwargs={'shareable_link': self.meal_plan.shareable_link}))
        
        self.meal_plan.refresh_from_db()
        self.assertEqual(self.meal_plan.grocery_list_instruction, '')
        self.assertEqual(self.meal_plan.grocery_list, mock_response)
    
    def test_create_grocery_list_multiple_recipes(self):
        """Test that grocery list includes ingredients from all recipes"""
        self.login_user(self.member)
        
        # Create another recipe with ingredients
        recipe2 = RecipeFactory(meal=self.meal)
        IngredientFactory(recipe=recipe2, name='Sugar', amount='2', unit='tbsp')
        IngredientFactory(recipe=recipe2, name='Flour', amount='1', unit='cup')
        
        mock_response = """```
Baking:
- Flour (1 cup) - Test Recipe from Test Meal
- Sugar (2 tbsp) - Test Recipe from Test Meal

Dairy:
- Milk (1 cup) - Test Recipe from Test Meal

Spices:
- Cinnamon (2 tbsp) - Test Recipe from Test Meal
```"""
        with patch('main.ai_helpers.OpenAI') as mock_openai:
            mock_chat = mock_openai.return_value.chat.completions
            mock_chat.create.return_value.choices[0].message.content = mock_response
            
            response = self.client.post(self.url, {'grocery_list_instruction': 'Group by type'})
        
        self.assertRedirects(response, reverse('main:meal_plan_detail', kwargs={'shareable_link': self.meal_plan.shareable_link}))
        
        self.meal_plan.refresh_from_db()
        self.assertEqual(self.meal_plan.grocery_list_instruction, 'Group by type')
        self.assertEqual(self.meal_plan.grocery_list, mock_response)
