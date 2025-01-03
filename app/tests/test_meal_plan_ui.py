from django.urls import reverse
import pytest

from .factories import CollectionFactory, MealFactory, MealPlanFactory, MembershipFactory, UserFactory
from .test_base_ui import UITestBase


class TestMealPlanUI(UITestBase):
    """UI tests for meal plan functionality"""
    
    def test_meal_toggle_with_animation(self, page, live_server, django_user_model):
        """Test toggling meals in/out of meal plan with animation"""
        # Create test data
        user = UserFactory()
        collection = CollectionFactory(user=user)
        meal = MealFactory(collection=collection, title="Test Meal")
        meal_plan = MealPlanFactory(owner=user)
        MembershipFactory(user=user, meal_plan=meal_plan)
        
        # Add meal to plan initially
        meal_plan.meals.add(meal)
        
        # Set up user session
        self.setup_user_session(page, user)
        
        # Visit meal plan detail page
        url = f"{live_server.url}{reverse('main:meal_plan_detail', kwargs={'shareable_link': meal_plan.shareable_link})}"
        print(f"Navigating to: {url}")
        page.goto(url)
        self.wait_for_page_load(page)
        
        # Initially meal should be in plan (solid button with check icon)
        remove_button = page.locator("button.btn-success i.bi-check-circle-fill")
        print("Checking for remove button...")
        assert remove_button.is_visible()
        
        # Remove meal from plan
        print("Removing meal from plan...")
        with page.expect_response(lambda response: 'meal-plan' in response.url and response.status == 200):
            remove_button.click()
        
        # Wait for success toast
        self.wait_for_toast(page, "removed from meal plan")
        
        # Verify button has changed to outline with plus icon
        add_button = page.locator("button.btn-outline-success i.bi-plus-circle")
        add_button.wait_for(state="visible")
        assert add_button.is_visible()
        
        # Add meal back to plan
        print("Adding meal back to plan...")
        with page.expect_response(lambda response: 'meal-plan' in response.url and response.status == 200):
            add_button.click()
        
        # Wait for success toast
        self.wait_for_toast(page, "added to meal plan")
        
        # Verify button is back to solid with check icon
        remove_button = page.locator("button.btn-success i.bi-check-circle-fill")
        remove_button.wait_for(state="visible")
        assert remove_button.is_visible()
    
    def test_delete_meal_with_confirmation(self, page, live_server, django_user_model):
        """Test deleting a meal with confirmation dialog and animation"""
        # Create test data
        user = UserFactory()
        collection = CollectionFactory(user=user)
        meal = MealFactory(collection=collection, title="Test Meal")
        meal_plan = MealPlanFactory(owner=user)
        MembershipFactory(user=user, meal_plan=meal_plan)
        meal_plan.meals.add(meal)
        
        # Set up user session
        self.setup_user_session(page, user)
        
        # Visit meal plan detail page
        url = f"{live_server.url}{reverse('main:meal_plan_detail', kwargs={'shareable_link': meal_plan.shareable_link})}"
        print(f"Navigating to: {url}")
        page.goto(url)
        self.wait_for_page_load(page)
        
        # Find the delete button
        delete_button = page.locator("button.btn-outline-danger i.bi-trash")
        print("Checking for delete button...")
        delete_button.wait_for(state="visible")
        assert delete_button.is_visible()
        
        # Set up dialog handler to accept confirmation
        page.on("dialog", lambda dialog: dialog.accept())
        
        # Click delete and verify card animation
        print("Deleting meal...")
        delete_button.click()
        
        # Wait for success toast
        self.wait_for_toast(page, "has been deleted")
        
        # Verify meal card is removed with animation
        meal_card = page.locator(".meal-card")
        meal_card.wait_for(state="hidden")
        assert meal_card.count() == 0
        
        # Reload page and verify meal is still gone
        page.reload()
        self.wait_for_page_load(page)
        assert meal_card.count() == 0
        
        # Verify meal is deleted from database
        from main.models import Meal
        assert not Meal.objects.filter(id=meal.id).exists()
    
    def test_grocery_list_autosave(self, page, live_server, django_user_model):
        """Test auto-saving grocery list with debounce"""
        # Create test data
        user = UserFactory()
        meal_plan = MealPlanFactory(owner=user)
        MembershipFactory(user=user, meal_plan=meal_plan)
        
        # Set up user session
        self.setup_user_session(page, user)
        
        # Visit meal plan detail page
        url = f"{live_server.url}{reverse('main:meal_plan_detail', kwargs={'shareable_link': meal_plan.shareable_link})}"
        print(f"Navigating to: {url}")
        page.goto(url)
        self.wait_for_page_load(page)
        
        # Find grocery list textarea
        grocery_list = page.locator("[data-meal-plan-target='groceryList']")
        print("Checking for grocery list...")
        grocery_list.wait_for(state="visible")
        
        # Type into grocery list
        test_text = "Test grocery list"
        print("Updating grocery list...")
        grocery_list.fill(test_text)
        
        # Wait for auto-save status to show "Saving..."
        save_status = page.locator("[data-meal-plan-target='saveStatus']")
        save_status.wait_for(state="visible")
        assert "Saving..." in save_status.text_content()
        
        # Wait for auto-save to complete (3 second debounce + request time)
        page.wait_for_timeout(4000)
        assert "Changes saved" in save_status.text_content()
        
        # Reload page and verify text persisted
        page.reload()
        self.wait_for_page_load(page)
        grocery_list = page.locator("[data-meal-plan-target='groceryList']")
        assert grocery_list.input_value() == test_text
        
        # Verify text is saved in database
        meal_plan.refresh_from_db()
        assert meal_plan.grocery_list == test_text
    
    #@pytest.mark.browser_context_args(permissions=["clipboard-read", "clipboard-write"])
    def test_copy_share_link(self, page, live_server, django_user_model):
        """Test copying share link to clipboard"""
        # Create test data
        user = UserFactory()
        meal_plan = MealPlanFactory(owner=user)
        MembershipFactory(user=user, meal_plan=meal_plan)
        
        # Set up user session
        self.setup_user_session(page, user)
        
        # Visit meal plan detail page
        url = f"{live_server.url}{reverse('main:meal_plan_detail', kwargs={'shareable_link': meal_plan.shareable_link})}"
        print(f"Navigating to: {url}")
        page.goto(url)
        self.wait_for_page_load(page)
        
        # Find share link input and copy button
        share_link = page.locator("[data-meal-plan-target='shareLink']")
        copy_button = page.locator("button[data-action='meal-plan#copyLink']")
        print("Checking for share link and copy button...")
        share_link.wait_for(state="visible")
        copy_button.wait_for(state="visible")
        
        # Verify share link value
        assert share_link.input_value() == url
        
        # Click the copy button and handle clipboard permission
        page.get_by_role("button", name="Copy Link").click()
        #page.get_by_role("button", name="Allow").click()

        # Now check for the toast after clipboard permission is granted
        page.get_by_text("Link copied to clipboard").wait_for()

        # Verify the clipboard content
        for attempt in range(5):
            try:
                clipboard_text = page.evaluate("navigator.clipboard.readText()")
                if clipboard_text == url:
                    break
            except:
                page.wait_for_timeout(1000)  # Wait 1 second between attempts
        
        assert clipboard_text == url, f"Expected clipboard to contain '{url}', got '{clipboard_text}'"
