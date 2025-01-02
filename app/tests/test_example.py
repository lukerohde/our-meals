# tests/test_example.py
import pytest
from playwright.sync_api import Page

@pytest.mark.playwright
def test_example(page: Page):
    page.goto("https://example.com")
    assert page.title() == "Example Domain"