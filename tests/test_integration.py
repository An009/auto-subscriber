import pytest
from playwright.sync_api import sync_playwright

@pytest.mark.skip(reason="Requires headful browser and network connection")
def test_integration_flow():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://example.com")
        assert page.title() == "Example Domain"
        browser.close()
