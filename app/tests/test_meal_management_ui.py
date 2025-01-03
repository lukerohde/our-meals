from django.urls import reverse
from pytest import mark
from django.test import Client
from .factories import UserFactory, CollectionFactory, MealFactory, MealPlanFactory, MembershipFactory

@mark.playwright
class TestMealManagementUI:
    def test_toggle_meal_in_meal_plan(self, page, live_server, django_user_model):
        # Create test data
        user = UserFactory()
        collection = CollectionFactory(user=user)
        meal = MealFactory(collection=collection, title="Test Meal")
        meal_plan = MealPlanFactory(owner=user)
        MembershipFactory(user=user, meal_plan=meal_plan)
        
        # Login user via test client to get a valid session
        client = Client()
        client.force_login(user)
        session_cookie = client.cookies['sessionid']
        page.context.add_cookies([{
            'name': 'sessionid',
            'value': session_cookie.value,
            'domain': 'localhost',
            'path': '/',
        }])
        
        # Visit collection detail page
        url = f"{live_server.url}{reverse('main:collection_detail', kwargs={'pk': collection.pk})}"
        print(f"Navigating to: {url}")
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        
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
        success_toast = page.locator(".toast.bg-success").last
        print("Waiting for success toast...")
        success_toast.wait_for(state="visible")
        assert success_toast.is_visible()
        assert "added to meal plan" in success_toast.text_content()
        
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
        success_toast = page.locator(".toast.bg-success").last
        print("Waiting for success toast...")
        success_toast.wait_for(state="visible")
        assert success_toast.is_visible()
        assert "removed from meal plan" in success_toast.text_content()
        
        # Button should be back to outline
        add_button = page.locator("button.btn.btn-sm.btn-outline-success")
        add_button.wait_for(state="visible")
        assert add_button.is_visible()
