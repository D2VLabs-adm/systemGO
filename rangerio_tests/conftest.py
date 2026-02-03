"""
Shared pytest fixtures for all tests
"""
import pytest
import asyncio
import uuid
from pathlib import Path
from typing import Generator, Dict, Any, List
import requests
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
import psutil
import time

from rangerio_tests.config import config
from rangerio_tests.utils.mode_config import get_mode, get_all_modes


# ============================================================================
# Session-Level Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def rangerio_backend_url() -> str:
    """Backend URL for API testing"""
    return config.RANGERIO_BACKEND_URL


@pytest.fixture(scope="session")
def rangerio_frontend_url() -> str:
    """Frontend URL for E2E testing"""
    return config.RANGERIO_FRONTEND_URL


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Directory containing test data files"""
    return config.TEST_DATA_DIR


@pytest.fixture(scope="session")
def golden_output_dir() -> Path:
    """Directory containing golden output data"""
    return config.GOLDEN_OUTPUT_DIR


@pytest.fixture(scope="session")
def reports_dir() -> Path:
    """Directory for test reports and outputs"""
    return config.REPORTS_DIR


# ============================================================================
# Backend API Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def api_client(rangerio_backend_url):
    """HTTP client for API testing"""
    session = requests.Session()
    # Don't set Content-Type globally - let requests handle it per request
    # (multipart/form-data for file uploads, application/json for JSON)
    
    class APIClient:
        def __init__(self, base_url):
            self.base_url = base_url
            self.session = session
            
        def get(self, endpoint, **kwargs):
            return self.session.get(f"{self.base_url}{endpoint}", **kwargs)
        
        def post(self, endpoint, **kwargs):
            # Auto-enable assistant_mode for RAG queries (unless explicitly disabled)
            # Assistant mode optimizes most RangerIO capabilities and should be the default
            if "/rag/query" in endpoint and "json" in kwargs:
                json_data = kwargs["json"]
                if isinstance(json_data, dict) and "assistant_mode" not in json_data:
                    json_data["assistant_mode"] = True
            return self.session.post(f"{self.base_url}{endpoint}", **kwargs)
        
        def put(self, endpoint, **kwargs):
            return self.session.put(f"{self.base_url}{endpoint}", **kwargs)
        
        def delete(self, endpoint, **kwargs):
            return self.session.delete(f"{self.base_url}{endpoint}", **kwargs)
        
        def upload_file(self, endpoint, file_path: Path, data=None, **kwargs):
            """Upload a file with optional form data"""
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f)}
                # FastAPI Form() requires data to be passed as 'data' parameter, not 'json'
                return self.post(endpoint, files=files, data=data, **kwargs)
    
    yield APIClient(rangerio_backend_url)
    session.close()


@pytest.fixture
def create_test_rag(api_client):
    """Create a test RAG with unique name and clean up after test"""
    created_rags = []
    
    def _create(name: str = "Test RAG", description: str = "Test RAG for automated testing"):
        # Add UUID to ensure unique name
        unique_name = f"{name}_{uuid.uuid4().hex[:8]}"
        response = api_client.post("/projects", json={"name": unique_name, "description": description})
        if response.status_code == 200:
            rag_id = response.json()["id"]
            created_rags.append(rag_id)
            return rag_id
        return None
    
    yield _create
    
    # Cleanup
    for rag_id in created_rags:
        try:
            api_client.delete(f"/projects/{rag_id}")
        except:
            pass


# ============================================================================
# Frontend E2E Fixtures (Playwright)
# ============================================================================

@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """Playwright browser instance"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.PLAYWRIGHT_HEADLESS)
        yield browser
        browser.close()


@pytest.fixture
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Browser context for isolated testing"""
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        record_video_dir=str(config.REPORTS_DIR / "videos") if not config.PLAYWRIGHT_HEADLESS else None
    )
    yield context
    context.close()


@pytest.fixture
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """Page instance for UI testing"""
    page = context.new_page()
    page.set_default_timeout(config.PLAYWRIGHT_TIMEOUT)
    yield page
    page.close()


@pytest.fixture
def authenticated_page(page: Page, rangerio_frontend_url: str) -> Page:
    """Page with authenticated session (if auth is implemented)"""
    page.goto(rangerio_frontend_url)
    page.wait_for_load_state("networkidle")
    return page


# ============================================================================
# Performance Monitoring Fixtures
# ============================================================================

@pytest.fixture
def performance_monitor():
    """Monitor performance metrics during tests"""
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None
            self.metrics = {}
            self.process = psutil.Process()
        
        def start(self):
            self.start_time = time.time()
            self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        def stop(self):
            if self.start_time:
                self.metrics['duration_s'] = time.time() - self.start_time
                current_memory = self.process.memory_info().rss / 1024 / 1024
                self.metrics['memory_delta_mb'] = current_memory - self.start_memory
                self.metrics['peak_memory_mb'] = current_memory
            return self.metrics
        
        def assert_performance(self, max_duration_s=None, max_memory_mb=None):
            if max_duration_s and self.metrics.get('duration_s', 0) > max_duration_s:
                raise AssertionError(
                    f"Performance: Took {self.metrics['duration_s']:.2f}s (max: {max_duration_s}s)"
                )
            if max_memory_mb and self.metrics.get('peak_memory_mb', 0) > max_memory_mb:
                raise AssertionError(
                    f"Performance: Used {self.metrics['peak_memory_mb']:.2f}MB (max: {max_memory_mb}MB)"
                )
    
    return PerformanceMonitor()


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_csv_small(test_data_dir) -> Path:
    """Small CSV file (100 rows)"""
    return test_data_dir / "csv" / "small_100rows.csv"


@pytest.fixture
def sample_csv_with_pii(test_data_dir) -> Path:
    """CSV with PII data for detection testing"""
    return test_data_dir / "csv" / "pii_data.csv"


@pytest.fixture
def sample_csv_large(test_data_dir) -> Path:
    """Medium CSV file (5K rows) for performance testing - within RangerIO's 500K char limit"""
    return test_data_dir / "csv" / "medium_5krows.csv"


@pytest.fixture
def sample_excel(test_data_dir) -> Path:
    """Excel file with multiple sheets"""
    return test_data_dir / "excel" / "multi_sheet.xlsx"


@pytest.fixture
def sample_json(test_data_dir) -> Path:
    """JSON file"""
    return test_data_dir / "json" / "data.json"


@pytest.fixture
def sample_pdf(test_data_dir) -> Path:
    """PDF document for unstructured data testing"""
    return test_data_dir / "pdf" / "sample_document.pdf"


@pytest.fixture
def sample_docx(test_data_dir) -> Path:
    """DOCX document for unstructured data testing"""
    return test_data_dir / "docx" / "sample_document.docx"


# ============================================================================
# User Test Files Fixtures (from /Users/vadim/Documents/RangerIO test files)
# ============================================================================

@pytest.fixture(scope="session")
def user_test_files_dir() -> Path:
    """User's test files directory"""
    return config.USER_TEST_FILES_DIR


@pytest.fixture(scope="session")
def user_generated_data_dir() -> Path:
    """User's generated test data directory"""
    return config.USER_GENERATED_DATA_DIR


@pytest.fixture(scope="session")
def financial_sample() -> Path:
    """Financial Sample.xlsx - main test file for sales queries"""
    path = config.USER_TEST_FILES_DIR / "Financial Sample.xlsx"
    if not path.exists():
        pytest.skip(f"Financial Sample.xlsx not found at {path}")
    return path


@pytest.fixture
def user_pii_csv() -> Path:
    """CSV file with PII data (customers_pii.csv)"""
    path = config.USER_GENERATED_DATA_DIR / "customers_pii.csv"
    if not path.exists():
        pytest.skip(f"customers_pii.csv not found")
    return path


@pytest.fixture
def user_pii_excel() -> Path:
    """Excel file with PII data (employees_pii.xlsx)"""
    path = config.USER_GENERATED_DATA_DIR / "employees_pii.xlsx"
    if not path.exists():
        pytest.skip(f"employees_pii.xlsx not found")
    return path


@pytest.fixture
def user_duplicates_csv() -> Path:
    """CSV file with duplicate records"""
    path = config.USER_GENERATED_DATA_DIR / "data_duplicates.csv"
    if not path.exists():
        pytest.skip(f"data_duplicates.csv not found")
    return path


@pytest.fixture
def user_missing_values_csv() -> Path:
    """CSV file with missing values"""
    path = config.USER_GENERATED_DATA_DIR / "data_missing_values.csv"
    if not path.exists():
        pytest.skip(f"data_missing_values.csv not found")
    return path


@pytest.fixture
def user_mixed_quality_csv() -> Path:
    """CSV file with mixed quality issues"""
    path = config.USER_GENERATED_DATA_DIR / "data_mixed_quality.csv"
    if not path.exists():
        pytest.skip(f"data_mixed_quality.csv not found")
    return path


@pytest.fixture
def user_patterns_csv() -> Path:
    """CSV file with data patterns"""
    path = config.USER_GENERATED_DATA_DIR / "data_patterns.csv"
    if not path.exists():
        pytest.skip(f"data_patterns.csv not found")
    return path


@pytest.fixture
def user_outliers_csv() -> Path:
    """CSV file with outliers"""
    path = config.USER_GENERATED_DATA_DIR / "data_outliers.csv"
    if not path.exists():
        pytest.skip(f"data_outliers.csv not found")
    return path


@pytest.fixture
def all_user_csv_files() -> List[Path]:
    """All CSV files from user test directory"""
    return list(config.USER_GENERATED_DATA_DIR.glob("*.csv"))


@pytest.fixture
def all_user_excel_files() -> List[Path]:
    """All Excel files from user test directory"""
    return list(config.USER_GENERATED_DATA_DIR.glob("*.xlsx"))


@pytest.fixture
def kaggle_sales_dir() -> Path:
    """Kaggle sales data directory"""
    return config.USER_TEST_FILES_DIR / "kaggle_datasets" / "sales"


@pytest.fixture
def pdf_test_dir() -> Path:
    """PDF test files directory"""
    return config.USER_TEST_FILES_DIR / "PDF"


# ============================================================================
# Realistic Use Case Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def sales_dataset(test_data_dir) -> Path:
    """
    5-year sales dataset with multiple tabs (for realistic use case testing)
    
    Downloads from Kaggle if available, otherwise generates synthetic data.
    Validated to meet testing requirements (min 1000 rows, 2+ years, realistic columns).
    """
    from rangerio_tests.utils.kaggle_dataset_downloader import download_sales_dataset
    
    sales_dir = test_data_dir / "sales_usecase"
    sales_dir.mkdir(parents=True, exist_ok=True)
    
    # Download or generate the dataset
    sales_file = download_sales_dataset(sales_dir)
    
    return sales_file


@pytest.fixture(scope="session")
def auditor_files(test_data_dir) -> Dict[str, Path]:
    """
    Mixed file types for auditor use case testing
    
    Returns dict with keys: 'excel', 'pdf', 'docx', 'txt'
    - Excel: Financial statements (multiple tabs)
    - PDF: Board meeting minutes (text-based)
    - DOCX: Audit findings draft
    - TXT: Email thread
    
    All files have cross-references for testing multi-document reasoning.
    """
    from rangerio_tests.utils.kaggle_dataset_downloader import create_auditor_scenario
    
    auditor_dir = test_data_dir / "auditor_usecase"
    auditor_dir.mkdir(parents=True, exist_ok=True)
    
    # Create all auditor scenario files
    files = create_auditor_scenario(test_data_dir)
    
    return files


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def wait_for_backend(api_client):
    """Wait for backend to be ready"""
    max_attempts = 30
    for _ in range(max_attempts):
        try:
            response = api_client.get("/health")
            if response.status_code == 200:
                return True
        except:
            time.sleep(1)
    raise RuntimeError("Backend not available after 30 seconds")


@pytest.fixture
def wait_for_frontend(authenticated_page):
    """Wait for frontend to be ready"""
    # Frontend should already be loaded by authenticated_page
    return True


@pytest.fixture
def rag_evaluator(rangerio_backend_url):
    """RAG evaluator with ragas integration"""
    from rangerio_tests.utils.rag_evaluator import RAGEvaluator
    return RAGEvaluator(backend_url=rangerio_backend_url, model_name=config.DEFAULT_MODEL)


@pytest.fixture(scope="session")  # Session-scoped: shared across all tests
def interactive_validator(request, golden_output_dir):
    """Interactive validator for human-in-the-loop validation - shared across all tests"""
    from rangerio_tests.utils.interactive_validator import InteractiveValidator
    validator = InteractiveValidator(golden_output_dir=golden_output_dir)
    
    # Store in config for access in pytest_sessionfinish
    if not hasattr(request.config, '_interactive_validator'):
        request.config._interactive_validator = validator
    
    return validator


# ============================================================================
# Pytest Hooks - Generate ONE Consolidated HTML Report at End
# ============================================================================

def pytest_sessionfinish(session, exitstatus):
    """Generate ONE consolidated HTML report with all validation items after all tests complete"""
    # Get validator from config
    if hasattr(session.config, '_interactive_validator'):
        validator = session.config._interactive_validator
        
        if len(validator.html_items) > 0:
            report_path = validator.generate_html_report()
            print(f"\n{'='*70}")
            print(f"✅ CONSOLIDATED Interactive HTML Report Generated!")
            print(f"{'='*70}")
            print(f"📊 Location: {report_path}")
            print(f"📝 Total Items: {len(validator.html_items)} queries")
            print(f"\n🔗 CLICK TO OPEN:")
            print(f"   file://{report_path}")
            print(f"\n📋 Instructions:")
            print(f"   1. Open the report in your browser")
            print(f"   2. Review all {len(validator.html_items)} queries and answers")
            print(f"   3. Rate each (Accurate/Partial/Inaccurate)")
            print(f"   4. Check issue boxes and add notes")
            print(f"   5. Click 'Export Results' when done")
            print(f"{'='*70}\n")


# ============================================================================
# Mode Configuration Fixtures
# ============================================================================

@pytest.fixture(params=['basic', 'assistant', 'deep', 'both'])
def mode_config(request):
    """
    Parameterize tests across all modes.
    Use with @pytest.mark.parametrize or as fixture.
    """
    return get_mode(request.param)


@pytest.fixture
def basic_mode():
    """Basic mode (no features) fixture"""
    return get_mode('basic')


@pytest.fixture
def assistant_mode():
    """Assistant mode (smart features) fixture"""
    return get_mode('assistant')


@pytest.fixture
def deep_search_mode():
    """Deep Search mode (thorough analysis) fixture"""
    return get_mode('deep')


@pytest.fixture
def both_modes():
    """Both modes enabled fixture"""
    return get_mode('both')


@pytest.fixture
def all_modes():
    """All available modes fixture"""
    return get_all_modes()

