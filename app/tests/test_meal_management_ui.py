from django.urls import reverse
from pytest import mark
from .factories import UserFactory, CollectionFactory, MealFactory, MealPlanFactory, MembershipFactory
from .test_base_ui import UITestBase

@mark.playwright
class TestMealManagementUI(UITestBase):
    def test_toggle_meal_in_meal_plan(self, page, live_server, django_user_model):
        # Create test data
        user = UserFactory()
        collection = CollectionFactory(user=user)
        meal = MealFactory(collection=collection, title="Test Meal")
        meal_plan = MealPlanFactory(owner=user)
        MembershipFactory(user=user, meal_plan=meal_plan)
        
        # Set up user session
        self.setup_user_session(page, user)
        
        # Visit collection detail page
        url = f"{live_server.url}{reverse('main:collection_detail', kwargs={'pk': collection.pk})}"
        print(f"Navigating to: {url}")
        page.goto(url)
        self.wait_for_page_load(page)
        
        # Initially meal should not be in plan (outline button)
        add_button = page.locator("button.btn.btn-sm.btn-outline-success")
        print("Waiting for add button...")
        add_button.wait_for(state="visible")
        assert add_button.is_visible()
        
        # Click add button and wait for response
        print("Clicking add button...")
        with page.expect_response(lambda response: 'meal-plan' in response.url and response.status == 200):
            add_button.click()
        
        # Wait for success toast
        self.wait_for_toast(page, "added to meal plan")
        
        # Button should now be solid success
        remove_button = page.locator("button.btn.btn-sm.btn-success")
        remove_button.wait_for(state="visible")
        assert remove_button.is_visible()
        
        # Wait for the remove button to be ready for interaction
        print("Waiting for remove button to be ready...")
        remove_button.wait_for(state="attached")
        
        # Click remove button and wait for response
        print("Clicking remove button...")
        remove_button.click()
        
        # Wait for success toast
        self.wait_for_toast(page, "removed from meal plan")
        
        # Button should be back to outline
        add_button = page.locator("button.btn.btn-sm.btn-outline-success")
        add_button.wait_for(state="visible")
        assert add_button.is_visible()
    
    def test_delete_meal(self, page, live_server, django_user_model):
        # Create test data
        user = UserFactory()
        collection = CollectionFactory(user=user)
        meal = MealFactory(collection=collection, title="Test Meal")
        
        # Set up user session
        self.setup_user_session(page, user)
        
        # Visit collection detail page
        url = f"{live_server.url}{reverse('main:collection_detail', kwargs={'pk': collection.pk})}"
        print(f"Navigating to: {url}")
        page.goto(url)
        self.wait_for_page_load(page)
        
        # Find the delete button
        delete_button = page.locator("button.btn.btn-sm.btn-outline-danger")
        print("Waiting for delete button...")
        delete_button.wait_for(state="visible")
        assert delete_button.is_visible()
        
        # Set up dialog handler to accept confirmation
        page.on("dialog", lambda dialog: dialog.accept())
        
        # Click delete button and wait for response
        print("Clicking delete button...")
        delete_button.click()
        
        # Wait for success toast
        self.wait_for_toast(page, "has been deleted")
        
        # Wait for card to be removed
        meal_card = page.locator(".meal-card")
        print("Waiting for meal card to be removed...")
        meal_card.wait_for(state="hidden")
        assert meal_card.count() == 0
