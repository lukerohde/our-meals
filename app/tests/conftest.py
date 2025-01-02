# tests/conftest.py
import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # Optional: Load initial data or perform setup
        pass

# Remove pytest_addoption to avoid conflict
@pytest.fixture(scope="session")
def browser_context(request):
    headed = request.config.getoption("--headed", False)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context()
        yield context
        browser.close()

@pytest.fixture
def page(browser_context):
    page = browser_context.new_page()
    yield page
    page.close()