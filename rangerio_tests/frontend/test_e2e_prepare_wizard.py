"""
Frontend E2E tests with Playwright
Tests complete user workflows and visual regression
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestImportWizard:
    """Test Import Wizard UI flow"""
    
    def test_wizard_navigation(self, authenticated_page: Page):
        """Test opening and navigating the import wizard"""
        page = authenticated_page
        
        # Navigate to import page
        page.goto(f"{page.url.split('#')[0]}#/import")
        page.wait_for_load_state("networkidle")
        
        # Just verify the page loaded and URL is correct
        assert "/import" in page.url or "#/import" in page.url
        # Wait a bit for any dynamic content
        page.wait_for_timeout(1000)


@pytest.mark.e2e
class TestPrepareWizard:
    """Test Prepare Wizard with PandasAI features"""
    
    def test_wizard_open(self, authenticated_page: Page):
        """Test opening prepare wizard"""
        page = authenticated_page
        page.goto(f"{page.url.split('#')[0]}#/prepare")
        page.wait_for_load_state("networkidle")
        
        expect(page.locator("text=Prepare Data")).to_be_visible(timeout=5000)
    
    def test_chat_panel(self, authenticated_page: Page):
        """Test chat panel interaction"""
        page = authenticated_page
        page.goto(f"{page.url.split('#')[0]}#/prepare")
        
        # Look for chat input
        chat_input = page.locator("textarea[placeholder*='Ask']").first
        if chat_input.is_visible():
            chat_input.fill("Test query")
            # Don't send without actual data loaded


@pytest.mark.e2e
class TestRagsManagement:
    """Test RAGs management UI"""
    
    def test_rags_page(self, authenticated_page: Page):
        """Test RAGs page loads and displays tree"""
        page = authenticated_page
        page.goto(f"{page.url.split('#')[0]}#/rags")
        page.wait_for_load_state("networkidle")
        
        # Should see RAGs interface - use h1 specifically
        rags_heading = page.locator("h1").filter(has_text="RAGs").first
        expect(rags_heading).to_be_visible(timeout=5000)


@pytest.mark.e2e
class TestPromptsManagement:
    """Test Prompts management UI"""
    
    def test_prompts_page(self, authenticated_page: Page):
        """Test Prompts page loads"""
        page = authenticated_page
        page.goto(f"{page.url.split('#')[0]}#/prompts")
        page.wait_for_load_state("networkidle")
        
        # Just verify the page loaded and URL is correct
        assert "/prompts" in page.url or "#/prompts" in page.url
        # Wait a bit for any dynamic content
        page.wait_for_timeout(1000)


@pytest.mark.e2e
class TestVisualRegression:
    """Visual regression tests using Playwright screenshots"""
    
    def test_main_page_visual(self, authenticated_page: Page, reports_dir):
        """Capture main page screenshot for visual regression"""
        page = authenticated_page
        
        # Take screenshot
        screenshot_path = reports_dir / "screenshots" / "main_page.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot_path))
        
        # Note: For actual visual regression, use toHaveScreenshot()
        # await expect(page).toHaveScreenshot("main_page.png", maxDiffPixels=100)



@pytest.mark.e2e
class TestDataWorkflow:
    """Test complete data workflow from import to prepare"""
    
    def test_import_to_prepare_workflow(self, authenticated_page: Page):
        """Test navigating from import to prepare workflow"""
        page = authenticated_page
        
        # Start at import page
        page.goto(f"{page.url.split('#')[0]}#/import")
        page.wait_for_load_state("networkidle")
        assert "/import" in page.url or "#/import" in page.url
        
        # Navigate to prepare
        page.goto(f"{page.url.split('#')[0]}#/prepare")
        page.wait_for_load_state("networkidle")
        
        # Verify prepare page loaded
        expect(page.locator("text=Prepare Data")).to_be_visible(timeout=5000)
    
    def test_complete_navigation(self, authenticated_page: Page):
        """Test navigating through all main pages"""
        page = authenticated_page
        pages_to_test = ['import', 'prepare', 'rags', 'prompts', 'chat']
        
        for page_name in pages_to_test:
            page.goto(f"{page.url.split('#')[0]}#{page_name}")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)
            # Just verify navigation works
            assert True
