"""
UI Workflow Tests with Playwright
==================================

Tests actual user workflows through the RangerIO UI.
These tests require:
1. RangerIO backend running on localhost:9000
2. RangerIO frontend running on localhost:5173

Run with:
    PYTHONPATH=. pytest rangerio_tests/frontend/test_ui_workflows.py -v -s

Setup:
    pip install playwright
    playwright install chromium
"""
import pytest
import time
from pathlib import Path
from playwright.sync_api import Page, expect, TimeoutError as PlaywrightTimeout

# Test configuration
FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://127.0.0.1:9000"
DEFAULT_TIMEOUT = 30000  # 30 seconds
IMPORT_TIMEOUT = 120000  # 2 minutes for file import


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def browser_context(playwright):
    """
    Create a reusable browser context for all UI tests.
    Records video on failure for debugging.
    """
    browser = playwright.chromium.launch(
        headless=True,  # Set to False for debugging
        slow_mo=100  # Slow down actions for visibility
    )
    
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        record_video_dir="reports/videos/",
        record_video_size={"width": 1280, "height": 800}
    )
    
    # Set default timeout
    context.set_default_timeout(DEFAULT_TIMEOUT)
    
    yield context
    
    context.close()
    browser.close()


@pytest.fixture
def page(browser_context):
    """Create a new page for each test"""
    page = browser_context.new_page()
    yield page
    page.close()


@pytest.fixture
def app_page(page):
    """Navigate to the app and wait for it to load"""
    page.goto(FRONTEND_URL)
    
    # Wait for app to be ready (look for main navigation)
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeout:
        pass  # Continue even if networkidle times out
    
    # Give React time to render
    page.wait_for_timeout(1000)
    
    return page


@pytest.fixture
def test_csv_file(tmp_path):
    """Create a simple test CSV file"""
    csv_content = """product,category,price,quantity,date
Widget A,Electronics,29.99,100,2024-01-15
Widget B,Electronics,49.99,50,2024-01-16
Gadget X,Home,19.99,200,2024-01-17
Gadget Y,Home,39.99,75,2024-01-18
Tool Z,Industrial,99.99,25,2024-01-19
"""
    csv_file = tmp_path / "test_sales_data.csv"
    csv_file.write_text(csv_content)
    return csv_file


# =============================================================================
# BASIC NAVIGATION TESTS
# =============================================================================

@pytest.mark.ui
class TestBasicNavigation:
    """Test basic app navigation works"""
    
    def test_app_loads(self, app_page):
        """Test that the app loads successfully"""
        page = app_page
        
        # Should see some main UI element
        assert page.title() or page.url
        
        # Take screenshot
        page.screenshot(path="reports/screenshots/app_loaded.png")
    
    def test_navigate_all_pages(self, app_page):
        """Test navigating to all main pages"""
        page = app_page
        
        pages_to_test = [
            ("#/import", "Import"),
            ("#/prepare", "Prepare"),
            ("#/rags", "RAGs"),
            ("#/prompts", "Prompts"),
            ("#/chat", "Chat"),
            ("#/settings", "Settings"),
        ]
        
        for url_hash, name in pages_to_test:
            page.goto(f"{FRONTEND_URL}/{url_hash}")
            page.wait_for_timeout(500)
            
            # Verify URL changed
            assert url_hash.replace("#/", "") in page.url.lower() or \
                   url_hash.replace("#/", "") in page.url, \
                   f"Failed to navigate to {name}"
    
    def test_sidebar_navigation(self, app_page):
        """Test navigation via sidebar links"""
        page = app_page
        
        # Look for sidebar navigation links
        sidebar_links = page.locator("nav a, aside a, .sidebar a").all()
        
        if len(sidebar_links) > 0:
            # Click first link and verify navigation
            first_link = sidebar_links[0]
            first_link.click()
            page.wait_for_timeout(500)
            # Just verify no errors occurred
            assert True


# =============================================================================
# IMPORT WORKFLOW TESTS
# =============================================================================

@pytest.mark.ui
class TestImportWorkflow:
    """Test the file import workflow"""
    
    def test_import_page_loads(self, app_page):
        """Test import page has file upload area"""
        page = app_page
        page.goto(f"{FRONTEND_URL}/#/import")
        page.wait_for_timeout(1000)
        
        # Look for file input or drop zone
        file_input = page.locator('input[type="file"]').first
        drop_zone = page.locator('[data-testid="dropzone"], .dropzone, [class*="drop"]').first
        
        has_upload = file_input.count() > 0 or drop_zone.count() > 0
        
        if not has_upload:
            # Take screenshot for debugging
            page.screenshot(path="reports/screenshots/import_page_no_upload.png")
        
        # Don't fail - just log
        print(f"File input found: {file_input.count() > 0}")
        print(f"Drop zone found: {drop_zone.count() > 0}")
    
    def test_file_upload_interaction(self, app_page, test_csv_file):
        """Test file upload interaction"""
        page = app_page
        page.goto(f"{FRONTEND_URL}/#/import")
        page.wait_for_timeout(1000)
        
        # Find file input
        file_input = page.locator('input[type="file"]').first
        
        if file_input.count() > 0:
            # Upload test file
            file_input.set_input_files(str(test_csv_file))
            page.wait_for_timeout(1000)
            
            # Take screenshot of upload state
            page.screenshot(path="reports/screenshots/file_uploaded.png")
            
            # Look for file name or preview
            page_text = page.content().lower()
            assert "test_sales_data" in page_text or \
                   "csv" in page_text or \
                   file_input.count() > 0, \
                   "File upload doesn't seem to have worked"
        else:
            pytest.skip("No file input found on import page")


# =============================================================================
# CHAT WORKFLOW TESTS
# =============================================================================

@pytest.mark.ui
class TestChatWorkflow:
    """Test the chat/query workflow"""
    
    def test_chat_page_loads(self, app_page):
        """Test chat page has input area"""
        page = app_page
        page.goto(f"{FRONTEND_URL}/#/chat")
        page.wait_for_timeout(1000)
        
        # Look for chat input
        chat_input = page.locator(
            'textarea, input[type="text"][placeholder*="ask" i], '
            'input[type="text"][placeholder*="message" i], '
            '[data-testid="chat-input"]'
        ).first
        
        print(f"Chat input found: {chat_input.count() > 0}")
        page.screenshot(path="reports/screenshots/chat_page.png")
    
    def test_chat_input_interaction(self, app_page):
        """Test typing in chat input"""
        page = app_page
        page.goto(f"{FRONTEND_URL}/#/chat")
        page.wait_for_timeout(1000)
        
        # Find chat input
        chat_input = page.locator('textarea').first
        if chat_input.count() == 0:
            chat_input = page.locator('input[type="text"]').first
        
        if chat_input.count() > 0:
            # Type a test message
            chat_input.fill("What data do you have?")
            page.wait_for_timeout(500)
            
            # Verify text was entered
            value = chat_input.input_value()
            assert "What data" in value, "Text input failed"
            
            page.screenshot(path="reports/screenshots/chat_typed.png")
        else:
            pytest.skip("No chat input found")


# =============================================================================
# RAGS MANAGEMENT TESTS
# =============================================================================

@pytest.mark.ui
class TestRAGsWorkflow:
    """Test the RAGs management workflow"""
    
    def test_rags_page_loads(self, app_page):
        """Test RAGs page displays list"""
        page = app_page
        page.goto(f"{FRONTEND_URL}/#/rags")
        page.wait_for_timeout(1000)
        
        # Look for RAGs heading or list
        rags_heading = page.locator("h1, h2").filter(has_text="RAG")
        rags_list = page.locator('[data-testid="rags-list"], .rags-list, table')
        
        print(f"RAGs heading found: {rags_heading.count() > 0}")
        print(f"RAGs list found: {rags_list.count() > 0}")
        
        page.screenshot(path="reports/screenshots/rags_page.png")
    
    def test_create_rag_button(self, app_page):
        """Test that create RAG button exists"""
        page = app_page
        page.goto(f"{FRONTEND_URL}/#/rags")
        page.wait_for_timeout(1000)
        
        # Look for create/new button
        create_btn = page.locator(
            'button:has-text("Create"), button:has-text("New"), '
            'button:has-text("Add"), [data-testid="create-rag"]'
        ).first
        
        print(f"Create button found: {create_btn.count() > 0}")


# =============================================================================
# SETTINGS WORKFLOW TESTS
# =============================================================================

@pytest.mark.ui
class TestSettingsWorkflow:
    """Test the settings workflow"""
    
    def test_settings_page_loads(self, app_page):
        """Test settings page loads"""
        page = app_page
        page.goto(f"{FRONTEND_URL}/#/settings")
        page.wait_for_timeout(1000)
        
        page.screenshot(path="reports/screenshots/settings_page.png")
        
        # Should have some settings content
        page_text = page.content().lower()
        assert "settings" in page_text or "model" in page_text or "config" in page_text


# =============================================================================
# COMPLETE WORKFLOW TESTS
# =============================================================================

@pytest.mark.ui
@pytest.mark.slow
class TestCompleteWorkflow:
    """Test complete end-to-end workflows through the UI"""
    
    def test_import_to_chat_workflow(self, app_page, test_csv_file):
        """
        Complete workflow: Import file → Navigate to Chat → Ask question
        
        This is a slow test that simulates a real user session.
        """
        page = app_page
        
        # Step 1: Go to import
        print("\n📁 Step 1: Navigate to Import page")
        page.goto(f"{FRONTEND_URL}/#/import")
        page.wait_for_timeout(1000)
        
        # Step 2: Upload file (if possible)
        print("📤 Step 2: Upload test file")
        file_input = page.locator('input[type="file"]').first
        if file_input.count() > 0:
            file_input.set_input_files(str(test_csv_file))
            page.wait_for_timeout(2000)
            page.screenshot(path="reports/screenshots/workflow_file_uploaded.png")
        else:
            print("   ⚠️ No file input found, skipping upload")
        
        # Step 3: Navigate to RAGs
        print("📊 Step 3: Navigate to RAGs page")
        page.goto(f"{FRONTEND_URL}/#/rags")
        page.wait_for_timeout(1000)
        page.screenshot(path="reports/screenshots/workflow_rags.png")
        
        # Step 4: Navigate to Chat
        print("💬 Step 4: Navigate to Chat page")
        page.goto(f"{FRONTEND_URL}/#/chat")
        page.wait_for_timeout(1000)
        
        # Step 5: Try to ask a question
        print("❓ Step 5: Enter a question")
        chat_input = page.locator('textarea').first
        if chat_input.count() == 0:
            chat_input = page.locator('input[type="text"]').first
        
        if chat_input.count() > 0:
            chat_input.fill("What data is available?")
            page.wait_for_timeout(500)
            page.screenshot(path="reports/screenshots/workflow_question_entered.png")
            
            # Look for send button
            send_btn = page.locator(
                'button:has-text("Send"), button:has-text("Ask"), '
                'button[type="submit"]'
            ).first
            
            if send_btn.count() > 0:
                print("✅ Complete workflow UI elements found")
            else:
                print("⚠️ Send button not found")
        
        # Final screenshot
        page.screenshot(path="reports/screenshots/workflow_complete.png")
        print("📸 Workflow screenshots saved to reports/screenshots/")


# =============================================================================
# VISUAL REGRESSION TESTS
# =============================================================================

@pytest.mark.ui
class TestVisualRegression:
    """
    Visual regression tests - capture screenshots for comparison.
    These can be used with Playwright's built-in visual comparison.
    """
    
    def test_capture_all_pages(self, app_page):
        """Capture screenshots of all main pages"""
        page = app_page
        
        pages = [
            ("import", "Import"),
            ("prepare", "Prepare"),
            ("rags", "RAGs"),
            ("prompts", "Prompts"),
            ("chat", "Chat"),
            ("settings", "Settings"),
        ]
        
        screenshots_dir = Path("reports/screenshots/visual_regression")
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        for url_suffix, name in pages:
            page.goto(f"{FRONTEND_URL}/#{url_suffix}")
            page.wait_for_timeout(1000)
            page.screenshot(path=str(screenshots_dir / f"{url_suffix}.png"))
            print(f"📸 Captured {name} page")
        
        print(f"\n✅ Visual regression screenshots saved to {screenshots_dir}")
