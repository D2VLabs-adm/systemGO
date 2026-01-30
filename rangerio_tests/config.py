"""
Test configuration pointing to RangerIO workspace
"""
import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any

# Configure logging for E2E tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("rangerio_tests")


@dataclass
class TestConfig:
    """Central test configuration for all test suites"""
    
    # RangerIO Paths
    RANGERIO_WORKSPACE: Path = Path("/Users/vadim/.cursor/worktrees/rangerio-backend__Workspace_/udp")
    RANGERIO_BACKEND_URL: str = "http://127.0.0.1:9000"
    BACKEND_URL: str = "http://127.0.0.1:9000"  # Alias for compatibility
    RANGERIO_FRONTEND_URL: str = "http://localhost:5173"
    
    # Test Suite Paths (relative to this file for portability)
    TEST_ROOT: Path = Path(__file__).parent.parent
    FIXTURES_DIR: Path = Path(__file__).parent / "fixtures"  # rangerio_tests/fixtures
    TEST_DATA_DIR: Path = FIXTURES_DIR / "test_data"
    GOLDEN_OUTPUT_DIR: Path = FIXTURES_DIR / "golden_outputs"
    REPORTS_DIR: Path = TEST_ROOT / "reports"
    
    # Test Data Files - bundled with System GO (portable)
    # These are the primary test data files used by user scenario tests
    FINANCIAL_SAMPLE: Path = TEST_DATA_DIR / "Financial Sample.xlsx"
    SALES_TRENDS: Path = TEST_DATA_DIR / "sales_16_quarterly_trends_5years.csv"
    SALES_COMPREHENSIVE: Path = TEST_DATA_DIR / "sales_comprehensive_5year_full_company.xlsx"
    CUSTOMERS_PII: Path = TEST_DATA_DIR / "customers_pii.csv"
    EMPLOYEES_PII: Path = TEST_DATA_DIR / "employees_pii.csv"
    PATIENTS_PII: Path = TEST_DATA_DIR / "patients_pii.xlsx"
    DATA_MIXED_QUALITY: Path = TEST_DATA_DIR / "data_mixed_quality.csv"
    DATA_DUPLICATES: Path = TEST_DATA_DIR / "data_duplicates.csv"
    DATA_MISSING_VALUES: Path = TEST_DATA_DIR / "data_missing_values.csv"
    
    # Legacy: External test files (optional, for extended testing)
    USER_TEST_FILES_DIR: Path = Path(os.getenv("TEST_FILES_DIR", "/Users/vadim/Documents/RangerIO test files"))
    USER_GENERATED_DATA_DIR: Path = USER_TEST_FILES_DIR / "Generated data"
    USER_KAGGLE_DIR: Path = USER_TEST_FILES_DIR / "kaggle_datasets"
    
    # Logging
    LOG_DIR: Path = TEST_ROOT / "logs"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_API_REQUESTS: bool = True  # Log all API requests/responses
    
    # Performance Thresholds - optimized for fast Granite models
    MAX_RESPONSE_TIME_MS: int = 60000   # 1 minute for LLM queries (fast models)
    MAX_RESPONSE_TIME_QUALITY_MS: int = 90000  # 1.5 min for quality tests (tiny model)
    MAX_IMPORT_TIME_S: int = 120  # 2 minutes for imports
    MAX_MEMORY_MB: int = 2048  # 2GB max memory (small models)
    MIN_RAG_FAITHFULNESS: float = 0.70  # 70% minimum faithfulness
    MIN_RAG_RELEVANCY: float = 0.70  # 70% minimum relevancy
    MIN_PII_DETECTION_RATE: float = 0.95  # 95% PII detection rate
    
    # Multi-Source RAG Thresholds
    MIN_SOURCE_COVERAGE: float = 0.50  # At least 50% of sources should be referenced
    MIN_CROSS_REFERENCE_RATE: float = 0.30  # At least 30% of responses should cross-reference
    MULTI_SOURCE_TIMEOUT_S: int = 180  # 3 minutes for multi-source queries
    
    # Interactive Validation
    INTERACTIVE_MODE: bool = True
    AUTO_SAVE_GOLDEN_DATASET: bool = True
    
    # Model Configs - Using fast Granite models for testing
    # Micro (~500MB) for general E2E tests - very fast (3-10s per query)
    # Tiny (~700MB) for quality regression tests - fast (5-15s per query)
    DEFAULT_MODEL: str = "granite-4-0-h-micro-q4-k-m"  # Fast model for general tests
    QUALITY_MODEL: str = "granite-4-0-h-tiny-q4-k-m"   # Quality model for regression tests
    SECONDARY_MODEL: str = "granite-4-0-h-tiny-q4-k-m"  # Fallback model
    
    # Test File Sizes
    SMALL_FILE_ROWS: int = 100
    MEDIUM_FILE_ROWS: int = 10000
    LARGE_FILE_ROWS: int = 50000
    XLARGE_FILE_ROWS: int = 200000
    
    # Playwright Config
    PLAYWRIGHT_HEADLESS: bool = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
    PLAYWRIGHT_TIMEOUT: int = 30000  # 30 seconds
    
    # Locust Config
    LOCUST_USERS: int = 100
    LOCUST_SPAWN_RATE: int = 10
    LOCUST_RUN_TIME: str = "5m"
    
    def __post_init__(self):
        """Ensure directories exist"""
        self.FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        self.TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.GOLDEN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Verify user test files exist
        if not self.USER_TEST_FILES_DIR.exists():
            logger.warning(f"User test files directory not found: {self.USER_TEST_FILES_DIR}")
        else:
            logger.info(f"User test files directory: {self.USER_TEST_FILES_DIR}")
            
    def get_user_test_file(self, filename: str) -> Path:
        """Get path to a user test file"""
        # Check Generated data first
        path = self.USER_GENERATED_DATA_DIR / filename
        if path.exists():
            return path
        # Check root directory
        path = self.USER_TEST_FILES_DIR / filename
        if path.exists():
            return path
        raise FileNotFoundError(f"Test file not found: {filename}")
    
    def list_user_test_files(self, pattern: str = "*") -> List[Path]:
        """List user test files matching pattern"""
        files = []
        if self.USER_GENERATED_DATA_DIR.exists():
            files.extend(self.USER_GENERATED_DATA_DIR.glob(pattern))
        if self.USER_TEST_FILES_DIR.exists():
            files.extend(self.USER_TEST_FILES_DIR.glob(pattern))
        return files


# Global config instance
config = TestConfig()

