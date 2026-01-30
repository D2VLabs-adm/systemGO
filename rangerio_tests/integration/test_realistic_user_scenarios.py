"""
Realistic User Scenario Tests for RangerIO
============================================

Tests that simulate real user behavior with:
1. Using existing data sources (not creating new ones each time)
2. Random content questions about the data
3. Complex logic/calculation questions across fields
4. AI-powered accuracy validation of responses
5. Multiple data sources across 4 test batches (~10 min each)

Run individual batches:
    pytest test_realistic_user_scenarios.py -m batch1 -v
    pytest test_realistic_user_scenarios.py -m batch2 -v
    pytest test_realistic_user_scenarios.py -m batch3 -v
    pytest test_realistic_user_scenarios.py -m batch4 -v

Run all batches:
    pytest test_realistic_user_scenarios.py -v

Uses test files from: /Users/vadim/Documents/RangerIO test files/
"""

import pytest
import time
import json
import uuid
import os
import re
import logging
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from rangerio_tests.config import config
from rangerio_tests.utils.accuracy_evaluator import (
    AccuracyEvaluator, 
    QuerySpec, 
    QueryType, 
    EvaluationResult,
    BatchResult,
    StructuredReporter,
    AccuracyVerdict
)
from rangerio_tests.utils.wait_utils import wait_for_import_indexed

logger = logging.getLogger("rangerio_tests.user_scenarios")

# Test timeouts
QUERY_TIMEOUT = 120  # 2 minutes per query
BATCH_TIMEOUT = 600  # 10 minutes per batch

# =============================================================================
# MODEL & MODE CONFIGURATION
# =============================================================================

MODEL_CONFIGS = {
    "micro": "granite-4-0-h-micro-q4-k-m",
    "tiny": "granite-4-0-h-tiny-q4-k-m",
}

def get_test_config() -> Dict[str, Any]:
    """
    Get test configuration from environment variables (set by System GO UI)
    or use defaults.
    """
    return {
        "model": os.environ.get("SYSTEM_GO_MODEL", "tiny"),
        "assistant_mode": os.environ.get("SYSTEM_GO_ASSISTANT", "false").lower() == "true",
        "use_streaming": os.environ.get("SYSTEM_GO_STREAMING", "true").lower() == "true",
    }

def switch_model(model_key: str) -> str:
    """
    Switch RangerIO to use the specified model.
    Returns the model name that was activated.
    """
    model_name = MODEL_CONFIGS.get(model_key, MODEL_CONFIGS["tiny"])
    
    try:
        response = requests.post(
            f"{config.BACKEND_URL}/models/{model_name}/select",
            timeout=60
        )
        if response.status_code == 200:
            logger.info(f"✓ Switched to model: {model_name}")
        else:
            logger.warning(f"Model switch returned {response.status_code}, continuing with current model")
    except Exception as e:
        logger.warning(f"Could not switch model: {e}, continuing with current model")
    
    return model_name


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def evaluator():
    """Accuracy evaluator instance"""
    return AccuracyEvaluator(backend_url=config.BACKEND_URL)


@pytest.fixture(scope="session")
def reporter():
    """Structured reporter instance"""
    return StructuredReporter(output_dir=str(config.USER_GENERATED_DATA_DIR.parent / "reports" / "user_scenarios"))


@pytest.fixture(scope="session")
def financial_sample_path():
    """Path to Financial Sample.xlsx - Multi-column financial data"""
    path = config.FINANCIAL_SAMPLE
    if not path.exists():
        pytest.skip(f"Test file not found: {path}")
    return path


@pytest.fixture(scope="session")
def sales_trends_path():
    """Path to quarterly trends - 5 years of sales data for time series analysis"""
    path = config.SALES_TRENDS
    if not path.exists():
        pytest.skip(f"Test file not found: {path}")
    return path


@pytest.fixture(scope="session")
def customers_pii_path():
    """Path to customers PII data - Contains credit cards, CVV, emails, phones"""
    path = config.CUSTOMERS_PII
    if not path.exists():
        pytest.skip(f"Test file not found: {path}")
    return path


@pytest.fixture(scope="session")
def employees_pii_path():
    """Path to employees PII data - Contains SSN, bank accounts, passports, salaries"""
    path = config.EMPLOYEES_PII
    if not path.exists():
        pytest.skip(f"Test file not found: {path}")
    return path


@pytest.fixture(scope="session")
def mixed_quality_path():
    """Path to mixed quality data - Missing values, invalid data, quality issues"""
    path = config.DATA_MIXED_QUALITY
    if not path.exists():
        pytest.skip(f"Test file not found: {path}")
    return path


@pytest.fixture(scope="session")
def data_duplicates_path():
    """Path to duplicates test data"""
    path = config.DATA_DUPLICATES
    if not path.exists():
        pytest.skip(f"Test file not found: {path}")
    return path


def ensure_data_source_exists(api_client, file_path: Path, project_name: str) -> tuple:
    """
    Ensure a data source exists in the system.
    Returns (project_id, data_source_id)
    """
    # Check if project already exists with indexed data
    projects_resp = api_client.get("/projects")
    if projects_resp.status_code == 200:
        for proj in projects_resp.json():
            if project_name in proj.get("name", ""):
                # Check if it has indexed data sources
                ds_resp = api_client.get(f"/datasources?project_id={proj['id']}")
                if ds_resp.status_code == 200:
                    datasources = ds_resp.json()
                    if isinstance(datasources, list) and len(datasources) > 0:
                        ds = datasources[0]
                        # Verify the data source is actually indexed
                        rag_status = ds.get("rag_status", "")
                        if rag_status in ("ready", "indexed"):
                            logger.info(f"✅ Using existing indexed project: {proj['name']} with data source {ds['id']} (rag_status={rag_status})")
                            return proj['id'], ds['id']
                        else:
                            logger.info(f"Found project {proj['name']} but data source not indexed (rag_status={rag_status}), will create new")
    
    # Create new project and import
    unique_name = f"{project_name}_{uuid.uuid4().hex[:6]}"
    proj_resp = api_client.post("/projects", json={
        "name": unique_name,
        "description": f"User scenario test: {project_name}"
    })
    assert proj_resp.status_code == 200, f"Failed to create project: {proj_resp.text}"
    project_id = proj_resp.json()["id"]
    
    # Import file
    import_resp = api_client.upload_file(
        "/datasources/connect",
        file_path,
        data={'project_id': str(project_id), 'source_type': 'file'}
    )
    assert import_resp.status_code == 200, f"Failed to import: {import_resp.text}"
    ds_id = import_resp.json()["data_source_id"]
    
    # Wait for indexing (180s for first-time embedding model initialization)
    logger.info(f"Waiting for data source {ds_id} to be indexed...")
    assert wait_for_import_indexed(api_client, ds_id, max_wait=180), "Data source indexing timed out"
    
    logger.info(f"Created new project: {unique_name} with data source {ds_id}")
    return project_id, ds_id


# =============================================================================
# QUERY SPECIFICATIONS BY BATCH
# =============================================================================

BATCH1_QUERIES = [
    # Financial Sample - Basic to Complex
    QuerySpec(
        query="What products or segments are in this dataset?",
        query_type=QueryType.CONTENT_LOOKUP,
        description="Basic content discovery",
        must_contain=["segment", "product"],
        must_not_contain=["I don't know", "no data"],
    ),
    QuerySpec(
        query="What is the total gross sales amount?",
        query_type=QueryType.AGGREGATION,
        description="Simple aggregation",
        must_contain_pattern=r"[\d,]+\.?\d*",  # Must contain a number
    ),
    QuerySpec(
        query="Calculate the average profit margin percentage",
        query_type=QueryType.CALCULATION,
        description="Percentage calculation",
        must_contain=["%"],
    ),
    QuerySpec(
        query="Which country has the highest sales volume but lowest profit margin?",
        query_type=QueryType.CROSS_FIELD_LOGIC,
        description="Cross-field comparison requiring multi-field analysis",
    ),
    QuerySpec(
        query="Compare the performance between different segments. Which is most profitable?",
        query_type=QueryType.TREND_ANALYSIS,
        description="Comparative analysis",
    ),
    QuerySpec(
        query="Based on the data, which product-country combination should be prioritized for marketing investment and why?",
        query_type=QueryType.COMPLEX_REASONING,
        description="Strategic reasoning from data",
    ),
]

BATCH2_QUERIES = [
    # Sales Trends - Time Series Analysis over 5 years
    QuerySpec(
        query="What regions are covered in this sales data?",
        query_type=QueryType.CONTENT_LOOKUP,
        description="Region discovery",
        must_contain_pattern=r"(West|East|Central|North|South)",
    ),
    QuerySpec(
        query="What is the total revenue across all orders?",
        query_type=QueryType.AGGREGATION,
        description="Revenue aggregation",
        must_contain_pattern=r"[\d,]+",
    ),
    QuerySpec(
        query="Calculate the average profit margin percentage across all sales",
        query_type=QueryType.CALCULATION,
        description="Margin calculation",
        must_contain=["%"],
    ),
    QuerySpec(
        query="Which sales rep has the highest revenue but gives the most discounts?",
        query_type=QueryType.CROSS_FIELD_LOGIC,
        description="Multi-criteria analysis",
        must_contain_pattern=r"Rep\d+",
    ),
    QuerySpec(
        query="How has revenue changed year over year from 2021 to 2025?",
        query_type=QueryType.TREND_ANALYSIS,
        description="Multi-year trend analysis",
        must_contain_pattern=r"202[1-5]",
    ),
    QuerySpec(
        query="Analyze the correlation between discount rates and customer retention. What pricing strategy would you recommend?",
        query_type=QueryType.COMPLEX_REASONING,
        description="Strategic analysis with data correlation",
    ),
]

BATCH3_QUERIES = [
    # PII Detection - Tests ability to identify sensitive data
    QuerySpec(
        query="What types of personal information (PII) are present in this dataset?",
        query_type=QueryType.CONTENT_LOOKUP,
        description="PII type identification",
        must_contain_pattern=r"(SSN|social security|credit card|email|phone|address|passport|bank)",
    ),
    QuerySpec(
        query="How many employees have their SSN (Social Security Number) exposed?",
        query_type=QueryType.AGGREGATION,
        description="PII count aggregation",
        must_contain_pattern=r"\d+",
    ),
    QuerySpec(
        query="What percentage of records contain financial PII like credit cards or bank accounts?",
        query_type=QueryType.CALCULATION,
        description="PII percentage calculation",
        must_contain=["%"],
    ),
    QuerySpec(
        query="Which departments have employees with the highest salaries exposed?",
        query_type=QueryType.CROSS_FIELD_LOGIC,
        description="Cross-field PII analysis",
        must_contain_pattern=r"(Marketing|HR|Operations|Engineering|Sales|Finance)",
    ),
    QuerySpec(
        query="List the types of sensitive data fields: SSN, credit card numbers, bank accounts, passport numbers",
        query_type=QueryType.TREND_ANALYSIS,
        description="Comprehensive PII inventory",
        must_contain_pattern=r"(SSN|credit|bank|passport)",
    ),
    QuerySpec(
        query="What privacy or compliance risks exist with this data being exposed? Consider GDPR, HIPAA, PCI-DSS",
        query_type=QueryType.COMPLEX_REASONING,
        description="Privacy risk assessment",
        must_contain_pattern=r"(risk|compliance|privacy|sensitive|protect)",
    ),
]

BATCH4_QUERIES = [
    # Mixed Quality Data - Tests RAG with imperfect data
    QuerySpec(
        query="What columns are available in this dataset?",
        query_type=QueryType.CONTENT_LOOKUP,
        description="Schema discovery on messy data",
    ),
    QuerySpec(
        query="How many records are in this dataset?",
        query_type=QueryType.AGGREGATION,
        description="Count with potential missing values",
        must_contain_pattern=r"\d+",
    ),
    QuerySpec(
        query="What percentage of the data appears to have quality issues?",
        query_type=QueryType.CALCULATION,
        description="Quality assessment calculation",
    ),
    QuerySpec(
        query="Are there any patterns in which fields have the most missing or inconsistent values?",
        query_type=QueryType.CROSS_FIELD_LOGIC,
        description="Quality pattern detection",
    ),
    QuerySpec(
        query="Compare the quality of different sections of the data. Which needs most attention?",
        query_type=QueryType.TREND_ANALYSIS,
        description="Quality comparison",
    ),
    QuerySpec(
        query="Given the quality issues identified, what data cleaning steps would you prioritize and why?",
        query_type=QueryType.COMPLEX_REASONING,
        description="Quality-aware recommendations",
    ),
]


# =============================================================================
# BATCH 5: MULTI-SOURCE RAG TESTING
# =============================================================================

BATCH5_QUERIES = [
    # Multi-Source Cross-Document Analysis
    # These queries REQUIRE information from multiple data sources to answer correctly
    QuerySpec(
        query="Compare the customer PII data with the employee PII data. Are there any individuals who appear in both datasets?",
        query_type=QueryType.CROSS_FIELD_LOGIC,
        description="Cross-document entity matching between customers and employees",
        must_not_contain=["I don't have", "unable to access", "only one"],
    ),
    QuerySpec(
        query="What types of PII are unique to customers vs unique to employees? Which dataset has more sensitive data?",
        query_type=QueryType.COMPLEX_REASONING,
        description="Comparative PII analysis across sources",
        must_contain_pattern=r"(customer|employee|credit|SSN|passport|bank)",
    ),
    QuerySpec(
        query="Looking at both datasets together, what is the total count of unique individuals with exposed PII?",
        query_type=QueryType.AGGREGATION,
        description="Aggregation across multiple sources",
        must_contain_pattern=r"\d+",
    ),
    QuerySpec(
        query="Which dataset - customers or employees - poses a higher compliance risk for GDPR, and why?",
        query_type=QueryType.COMPLEX_REASONING,
        description="Comparative risk analysis requiring both sources",
        must_contain_pattern=r"(GDPR|compliance|risk|privacy|sensitive)",
    ),
    QuerySpec(
        query="Synthesize findings from both datasets: What are the top 3 data protection priorities for this organization?",
        query_type=QueryType.COMPLEX_REASONING,
        description="Executive summary from multi-source analysis",
        must_contain_pattern=r"(1|2|3|first|second|third|priority|recommend)",
    ),
    QuerySpec(
        query="If there are overlapping individuals between customers and employees, what combined PII exposure risk do they face?",
        query_type=QueryType.CROSS_FIELD_LOGIC,
        description="Individual-level risk from combined sources",
    ),
]


@dataclass
class MultiSourceResult:
    """Result for multi-source query with coverage tracking"""
    query: str
    response: str
    response_time_s: float
    sources_queried: List[str]
    sources_referenced: List[str]
    coverage_score: float  # 0-100%
    cross_reference_detected: bool
    accuracy_score: float
    relevance_score: float
    passed: bool
    issues: List[str] = field(default_factory=list)


# =============================================================================
# TEST RUNNER HELPER
# =============================================================================

class ScenarioTestRunner:
    """Runs a batch of queries and collects results"""
    
    def __init__(self, api_client, evaluator: AccuracyEvaluator, reporter: StructuredReporter):
        self.api_client = api_client
        self.evaluator = evaluator
        self.reporter = reporter
        self.config = get_test_config()
    
    def run_batch(
        self,
        batch_name: str,
        data_source_name: str,
        project_id: int,
        data_source_id: int,
        queries: List[QuerySpec],
        model_key: Optional[str] = None,
        assistant_mode: Optional[bool] = None,
    ) -> BatchResult:
        """Run a batch of queries and return results"""
        results: List[EvaluationResult] = []
        batch_start = time.time()
        
        # Use provided values or fall back to config
        model = model_key or self.config["model"]
        use_assistant = assistant_mode if assistant_mode is not None else self.config["assistant_mode"]
        use_streaming = self.config["use_streaming"]
        
        # Switch model before running batch
        active_model = switch_model(model)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"BATCH: {batch_name}")
        logger.info(f"Data Source: {data_source_name}")
        logger.info(f"Model: {active_model}")
        logger.info(f"Assistant Mode: {use_assistant}")
        logger.info(f"Streaming: {use_streaming}")
        logger.info(f"Queries: {len(queries)}")
        logger.info(f"{'='*60}\n")
        
        for i, query_spec in enumerate(queries, 1):
            logger.info(f"  [{i}/{len(queries)}] {query_spec.query_type.value}: {query_spec.query[:60]}...")
            
            start_time = time.time()
            
            try:
                if use_streaming:
                    # Execute query via streaming endpoint (what UI uses)
                    response = self.api_client.session.post(
                        f"{self.api_client.base_url}/rag/query/stream",
                        json={
                            "prompt": query_spec.query,
                            "project_id": project_id,
                            "data_source_ids": [data_source_id],
                            "assistant_mode": use_assistant,
                        },
                        stream=True,
                        timeout=QUERY_TIMEOUT
                    )
                else:
                    # Use non-streaming endpoint for comparison
                    response = self.api_client.post(
                        "/rag/query",
                        json={
                            "prompt": query_spec.query,
                            "project_id": project_id,
                            "data_source_ids": [data_source_id],
                            "assistant_mode": use_assistant,
                        },
                        timeout=QUERY_TIMEOUT
                    )
                
                # Collect response (streaming or non-streaming)
                full_response = ""
                
                if use_streaming:
                    # Parse SSE stream
                    for line in response.iter_lines(decode_unicode=True):
                        if line.startswith('data: '):
                            json_str = line[6:]
                            if json_str == '[DONE]':
                                break
                            try:
                                event = json.loads(json_str)
                                if event.get('type') == 'content' and event.get('chunk'):
                                    full_response += event['chunk']
                            except json.JSONDecodeError:
                                continue
                else:
                    # Non-streaming response
                    if response.status_code == 200:
                        data = response.json()
                        full_response = data.get('answer', data.get('response', ''))
                    else:
                        full_response = f"Error: {response.status_code}"
                
                response_time = time.time() - start_time
                
                # Evaluate response
                result = self.evaluator.evaluate_response(
                    query_spec=query_spec,
                    response=full_response,
                    response_time=response_time,
                    data_context=None  # Could fetch profile for context
                )
                
                status = "✓" if result.passed else "✗"
                logger.info(f"       {status} Response: {len(full_response)} chars in {response_time:.1f}s")
                logger.info(f"         Accuracy: {result.accuracy_score}/10, Relevance: {result.relevance_score}/10")
                if result.issues:
                    for issue in result.issues[:2]:
                        logger.info(f"         ⚠ {issue}")
                
            except Exception as e:
                response_time = time.time() - start_time
                logger.error(f"       ✗ Query failed: {e}")
                result = EvaluationResult(
                    query=query_spec.query,
                    query_type=query_spec.query_type.value,
                    response=f"ERROR: {e}",
                    response_time_s=response_time,
                    verdict=AccuracyVerdict.ERROR,
                    accuracy_score=0,
                    relevance_score=0,
                    issues=[str(e)]
                )
            
            results.append(result)
        
        batch_time = time.time() - batch_start
        
        # Calculate batch statistics
        passed = sum(1 for r in results if r.passed)
        avg_accuracy = sum(r.accuracy_score for r in results) / len(results) if results else 0
        avg_relevance = sum(r.relevance_score for r in results) / len(results) if results else 0
        avg_response_time = sum(r.response_time_s for r in results) / len(results) if results else 0
        
        batch_result = BatchResult(
            batch_name=batch_name,
            data_source=data_source_name,
            total_queries=len(queries),
            passed_queries=passed,
            failed_queries=len(queries) - passed,
            total_time_s=batch_time,
            avg_response_time_s=avg_response_time,
            avg_accuracy_score=avg_accuracy,
            avg_relevance_score=avg_relevance,
            results=results
        )
        
        # Print and save report
        self.reporter.print_console_summary(batch_result)
        report_file = self.reporter.generate_batch_report(batch_result)
        logger.info(f"Report saved: {report_file}")
        
        return batch_result


# =============================================================================
# BATCH 1: FINANCIAL SAMPLE (~10 min)
# =============================================================================

@pytest.mark.batch1
@pytest.mark.user_scenario
@pytest.mark.timeout(BATCH_TIMEOUT)
class TestBatch1_Financial:
    """Batch 1: Financial Sample - Basic to Complex queries (~10 min)"""
    
    @pytest.fixture(scope="class")
    def financial_rag(self, api_client, financial_sample_path):
        """Setup RAG with financial data"""
        project_id, ds_id = ensure_data_source_exists(
            api_client, 
            financial_sample_path, 
            "UserScenario_Financial"
        )
        yield project_id, ds_id
    
    def test_batch1_all_queries(self, api_client, financial_rag, evaluator, reporter):
        """Run all Batch 1 queries"""
        project_id, ds_id = financial_rag
        
        runner = ScenarioTestRunner(api_client, evaluator, reporter)
        batch_result = runner.run_batch(
            batch_name="Batch1_Financial",
            data_source_name="Financial Sample.xlsx",
            project_id=project_id,
            data_source_id=ds_id,
            queries=BATCH1_QUERIES
        )
        
        # Assert minimum pass rate
        pass_rate = batch_result.passed_queries / batch_result.total_queries
        assert pass_rate >= 0.5, f"Batch 1 pass rate {pass_rate:.0%} below 50% threshold"
        assert batch_result.avg_accuracy_score >= 5.0, f"Batch 1 avg accuracy {batch_result.avg_accuracy_score} below 5.0"


# =============================================================================
# BATCH 2: SALES 5-YEAR COMPREHENSIVE (~10 min)
# =============================================================================

@pytest.mark.batch2
@pytest.mark.user_scenario
@pytest.mark.timeout(BATCH_TIMEOUT)
class TestBatch2_SalesTrends:
    """Batch 2: Sales Trends - Time Series Analysis over 5 years (~10 min)"""
    
    @pytest.fixture(scope="class")
    def sales_rag(self, api_client, sales_trends_path):
        """Setup RAG with sales trends data"""
        project_id, ds_id = ensure_data_source_exists(
            api_client, 
            sales_trends_path, 
            "UserScenario_SalesTrends"
        )
        yield project_id, ds_id
    
    def test_batch2_all_queries(self, api_client, sales_rag, evaluator, reporter):
        """Run all Batch 2 queries"""
        project_id, ds_id = sales_rag
        
        runner = ScenarioTestRunner(api_client, evaluator, reporter)
        batch_result = runner.run_batch(
            batch_name="Batch2_SalesTrends",
            data_source_name="sales_16_quarterly_trends_5years.csv",
            project_id=project_id,
            data_source_id=ds_id,
            queries=BATCH2_QUERIES
        )
        
        pass_rate = batch_result.passed_queries / batch_result.total_queries
        assert pass_rate >= 0.5, f"Batch 2 pass rate {pass_rate:.0%} below 50% threshold"


# =============================================================================
# BATCH 3: QUARTERLY TRENDS (~10 min)
# =============================================================================

@pytest.mark.batch3
@pytest.mark.user_scenario
@pytest.mark.timeout(BATCH_TIMEOUT)
class TestBatch3_PIIDetection:
    """Batch 3: PII Detection - Identify sensitive personal data (~10 min)"""
    
    @pytest.fixture(scope="class")
    def pii_rag(self, api_client, employees_pii_path):
        """Setup RAG with employee PII data (SSN, credit cards, bank accounts, passports)"""
        project_id, ds_id = ensure_data_source_exists(
            api_client, 
            employees_pii_path, 
            "UserScenario_PIIDetection"
        )
        yield project_id, ds_id
    
    def test_batch3_all_queries(self, api_client, pii_rag, evaluator, reporter):
        """Run all Batch 3 PII detection queries"""
        project_id, ds_id = pii_rag
        
        runner = ScenarioTestRunner(api_client, evaluator, reporter)
        batch_result = runner.run_batch(
            batch_name="Batch3_PIIDetection",
            data_source_name="employees_pii.csv",
            project_id=project_id,
            data_source_id=ds_id,
            queries=BATCH3_QUERIES
        )
        
        pass_rate = batch_result.passed_queries / batch_result.total_queries
        assert pass_rate >= 0.5, f"Batch 3 pass rate {pass_rate:.0%} below 50% threshold"


# =============================================================================
# BATCH 4: MIXED QUALITY DATA (~10 min)
# =============================================================================

@pytest.mark.batch4
@pytest.mark.user_scenario
@pytest.mark.timeout(BATCH_TIMEOUT)
class TestBatch4_MixedQuality:
    """Batch 4: Mixed Quality Data - Tests RAG with imperfect data (~10 min)"""
    
    @pytest.fixture(scope="class")
    def quality_rag(self, api_client, mixed_quality_path):
        """Setup RAG with mixed quality data"""
        project_id, ds_id = ensure_data_source_exists(
            api_client, 
            mixed_quality_path, 
            "UserScenario_MixedQuality"
        )
        yield project_id, ds_id
    
    def test_batch4_all_queries(self, api_client, quality_rag, evaluator, reporter):
        """Run all Batch 4 queries"""
        project_id, ds_id = quality_rag
        
        runner = ScenarioTestRunner(api_client, evaluator, reporter)
        batch_result = runner.run_batch(
            batch_name="Batch4_MixedQuality",
            data_source_name="data_mixed_quality.csv",
            project_id=project_id,
            data_source_id=ds_id,
            queries=BATCH4_QUERIES
        )
        
        pass_rate = batch_result.passed_queries / batch_result.total_queries
        # Lower threshold for quality data (harder to answer accurately)
        assert pass_rate >= 0.4, f"Batch 4 pass rate {pass_rate:.0%} below 40% threshold"


# =============================================================================
# BATCH 5: MULTI-SOURCE RAG (~15 min)
# =============================================================================

class MultiSourceTestRunner:
    """Runs multi-source queries that require cross-document analysis"""
    
    def __init__(self, api_client, evaluator: AccuracyEvaluator, reporter: StructuredReporter):
        self.api_client = api_client
        self.evaluator = evaluator
        self.reporter = reporter
        self.config = get_test_config()
    
    def detect_source_references(self, response: str, source_names: List[str]) -> List[str]:
        """Detect which sources are referenced in the response"""
        referenced = []
        response_lower = response.lower()
        
        for source in source_names:
            # Check for various forms of source reference
            source_lower = source.lower()
            if source_lower in response_lower:
                referenced.append(source)
            # Also check for key terms that indicate the source type
            elif "customer" in source_lower and ("customer" in response_lower or "client" in response_lower):
                referenced.append(source)
            elif "employee" in source_lower and ("employee" in response_lower or "staff" in response_lower or "worker" in response_lower):
                referenced.append(source)
        
        return list(set(referenced))
    
    def detect_cross_reference(self, response: str) -> bool:
        """Detect if the response cross-references multiple sources"""
        cross_ref_patterns = [
            r"(both|comparing|versus|vs\.?|compared to|in contrast|while|whereas)",
            r"(customer.*employee|employee.*customer)",
            r"(dataset.*dataset|source.*source|file.*file)",
            r"(together|combined|across both|in both|neither)",
            r"(first dataset.*second dataset|one.*other)",
        ]
        
        response_lower = response.lower()
        for pattern in cross_ref_patterns:
            if re.search(pattern, response_lower):
                return True
        return False
    
    def run_multi_source_batch(
        self,
        batch_name: str,
        project_id: int,
        data_source_ids: List[int],
        source_names: List[str],
        queries: List[QuerySpec],
    ) -> BatchResult:
        """Run a batch of multi-source queries"""
        results: List[EvaluationResult] = []
        multi_source_results: List[MultiSourceResult] = []
        batch_start = time.time()
        
        # Get config
        model = self.config["model"]
        use_assistant = self.config["assistant_mode"]
        use_streaming = self.config["use_streaming"]
        
        # Switch model
        active_model = switch_model(model)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"MULTI-SOURCE BATCH: {batch_name}")
        logger.info(f"Data Sources: {', '.join(source_names)}")
        logger.info(f"Model: {active_model}")
        logger.info(f"{'='*60}\n")
        
        for i, query_spec in enumerate(queries, 1):
            logger.info(f"  [{i}/{len(queries)}] Multi-Source: {query_spec.query[:60]}...")
            
            start_time = time.time()
            
            try:
                if use_streaming:
                    response = self.api_client.session.post(
                        f"{self.api_client.base_url}/rag/query/stream",
                        json={
                            "prompt": query_spec.query,
                            "project_id": project_id,
                            "data_source_ids": data_source_ids,  # Multiple sources!
                            "assistant_mode": use_assistant,
                        },
                        stream=True,
                        timeout=QUERY_TIMEOUT
                    )
                else:
                    response = self.api_client.post(
                        "/rag/query",
                        json={
                            "prompt": query_spec.query,
                            "project_id": project_id,
                            "data_source_ids": data_source_ids,  # Multiple sources!
                            "assistant_mode": use_assistant,
                        },
                        timeout=QUERY_TIMEOUT
                    )
                
                # Collect response
                full_response = ""
                if use_streaming:
                    for line in response.iter_lines(decode_unicode=True):
                        if line.startswith('data: '):
                            json_str = line[6:]
                            if json_str == '[DONE]':
                                break
                            try:
                                event = json.loads(json_str)
                                if event.get('type') == 'content' and event.get('chunk'):
                                    full_response += event['chunk']
                            except json.JSONDecodeError:
                                continue
                else:
                    if response.status_code == 200:
                        data = response.json()
                        full_response = data.get('answer', data.get('response', ''))
                    else:
                        full_response = f"Error: {response.status_code}"
                
                response_time = time.time() - start_time
                
                # Multi-source analysis
                sources_referenced = self.detect_source_references(full_response, source_names)
                cross_ref_detected = self.detect_cross_reference(full_response)
                coverage_score = (len(sources_referenced) / len(source_names)) * 100 if source_names else 0
                
                # Standard evaluation
                result = self.evaluator.evaluate_response(
                    query_spec=query_spec,
                    response=full_response,
                    response_time=response_time,
                    data_context=None
                )
                
                # Add multi-source issues
                if coverage_score < 50:
                    result.issues.append(f"Low source coverage: {coverage_score:.0f}% (only {len(sources_referenced)}/{len(source_names)} sources)")
                if not cross_ref_detected and len(source_names) > 1:
                    result.issues.append("No cross-reference detected between sources")
                
                # Log results
                status = "✓" if result.passed else "✗"
                logger.info(f"       {status} Coverage: {coverage_score:.0f}%, Cross-ref: {cross_ref_detected}")
                logger.info(f"         Sources: {sources_referenced}")
                logger.info(f"         Accuracy: {result.accuracy_score}/10, Response: {len(full_response)} chars in {response_time:.1f}s")
                
                # Create multi-source result
                ms_result = MultiSourceResult(
                    query=query_spec.query,
                    response=full_response,
                    response_time_s=response_time,
                    sources_queried=source_names,
                    sources_referenced=sources_referenced,
                    coverage_score=coverage_score,
                    cross_reference_detected=cross_ref_detected,
                    accuracy_score=result.accuracy_score,
                    relevance_score=result.relevance_score,
                    passed=result.passed and coverage_score >= 50,
                    issues=result.issues
                )
                multi_source_results.append(ms_result)
                
            except Exception as e:
                response_time = time.time() - start_time
                logger.error(f"       ✗ Query failed: {e}")
                result = EvaluationResult(
                    query=query_spec.query,
                    query_type=query_spec.query_type.value,
                    response=f"ERROR: {e}",
                    response_time_s=response_time,
                    verdict=AccuracyVerdict.ERROR,
                    accuracy_score=0,
                    relevance_score=0,
                    issues=[str(e)]
                )
            
            results.append(result)
        
        batch_time = time.time() - batch_start
        
        # Calculate batch statistics with multi-source weighting
        passed = sum(1 for r in multi_source_results if r.passed)
        avg_accuracy = sum(r.accuracy_score for r in multi_source_results) / len(multi_source_results) if multi_source_results else 0
        avg_relevance = sum(r.relevance_score for r in multi_source_results) / len(multi_source_results) if multi_source_results else 0
        avg_coverage = sum(r.coverage_score for r in multi_source_results) / len(multi_source_results) if multi_source_results else 0
        avg_response_time = sum(r.response_time_s for r in results) / len(results) if results else 0
        
        logger.info(f"\n  Multi-Source Metrics:")
        logger.info(f"    Avg Source Coverage: {avg_coverage:.0f}%")
        logger.info(f"    Cross-Ref Rate: {sum(1 for r in multi_source_results if r.cross_reference_detected)}/{len(multi_source_results)}")
        
        batch_result = BatchResult(
            batch_name=batch_name,
            data_source=f"Multi-Source: {', '.join(source_names)}",
            total_queries=len(queries),
            passed_queries=passed,
            failed_queries=len(queries) - passed,
            total_time_s=batch_time,
            avg_response_time_s=avg_response_time,
            avg_accuracy_score=avg_accuracy,
            avg_relevance_score=avg_relevance,
            results=results
        )
        
        # Print and save report
        self.reporter.print_console_summary(batch_result)
        report_file = self.reporter.generate_batch_report(batch_result)
        logger.info(f"Report saved: {report_file}")
        
        return batch_result


@pytest.mark.batch5
@pytest.mark.multisource
@pytest.mark.user_scenario
@pytest.mark.timeout(900)  # 15 minutes for multi-source
class TestBatch5_MultiSource:
    """Batch 5: Multi-Source RAG - Cross-document analysis (~15 min)"""
    
    @pytest.fixture(scope="class")
    def multi_source_rag(self, api_client, customers_pii_path, employees_pii_path):
        """Setup RAG with MULTIPLE data sources for cross-document testing"""
        # Create a single project with multiple data sources
        unique_name = f"MultiSource_RAG_{uuid.uuid4().hex[:6]}"
        proj_resp = api_client.post("/projects", json={
            "name": unique_name,
            "description": "Multi-source RAG for cross-document analysis"
        })
        assert proj_resp.status_code == 200, f"Failed to create project: {proj_resp.text}"
        project_id = proj_resp.json()["id"]
        
        data_source_ids = []
        source_names = []
        
        # Import customers PII
        logger.info(f"Importing customers PII to multi-source RAG...")
        import_resp = api_client.upload_file(
            "/datasources/connect",
            customers_pii_path,
            data={'project_id': str(project_id), 'source_type': 'file'}
        )
        assert import_resp.status_code == 200, f"Failed to import customers: {import_resp.text}"
        ds_id = import_resp.json()["data_source_id"]
        data_source_ids.append(ds_id)
        source_names.append("customers_pii.csv")
        
        # Wait for indexing
        assert wait_for_import_indexed(api_client, ds_id, max_wait=120), "Customers indexing timed out"
        
        # Import employees PII
        logger.info(f"Importing employees PII to multi-source RAG...")
        import_resp = api_client.upload_file(
            "/datasources/connect",
            employees_pii_path,
            data={'project_id': str(project_id), 'source_type': 'file'}
        )
        assert import_resp.status_code == 200, f"Failed to import employees: {import_resp.text}"
        ds_id = import_resp.json()["data_source_id"]
        data_source_ids.append(ds_id)
        source_names.append("employees_pii.csv")
        
        # Wait for indexing
        assert wait_for_import_indexed(api_client, ds_id, max_wait=120), "Employees indexing timed out"
        
        logger.info(f"Multi-source RAG ready: {unique_name} with {len(data_source_ids)} sources")
        
        yield project_id, data_source_ids, source_names
        
        # Cleanup
        try:
            api_client.delete(f"/projects/{project_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup multi-source RAG: {e}")
    
    def test_batch5_multi_source_queries(self, api_client, multi_source_rag, evaluator, reporter):
        """Run all Batch 5 multi-source queries"""
        project_id, data_source_ids, source_names = multi_source_rag
        
        runner = MultiSourceTestRunner(api_client, evaluator, reporter)
        batch_result = runner.run_multi_source_batch(
            batch_name="Batch5_MultiSource",
            project_id=project_id,
            data_source_ids=data_source_ids,
            source_names=source_names,
            queries=BATCH5_QUERIES
        )
        
        # Multi-source pass rate - require 40% (harder task)
        pass_rate = batch_result.passed_queries / batch_result.total_queries
        assert pass_rate >= 0.4, f"Multi-source batch pass rate {pass_rate:.0%} below 40% threshold"


# =============================================================================
# FULL SUITE - ALL BATCHES
# =============================================================================

@pytest.mark.all_batches
@pytest.mark.user_scenario
class TestAllBatches:
    """Run all batches and generate summary report"""
    
    def test_full_suite_summary(
        self, 
        api_client, 
        evaluator, 
        reporter,
        financial_sample_path,
        sales_trends_path,
        employees_pii_path,
        mixed_quality_path,
        customers_pii_path
    ):
        """Run all batches and generate comprehensive summary"""
        all_results: List[BatchResult] = []
        runner = ScenarioTestRunner(api_client, evaluator, reporter)
        
        # Batch 1: Financial Analysis
        proj_id, ds_id = ensure_data_source_exists(api_client, financial_sample_path, "UserScenario_Financial")
        result1 = runner.run_batch("Batch1_Financial", "Financial Sample.xlsx", proj_id, ds_id, BATCH1_QUERIES)
        all_results.append(result1)
        
        # Batch 2: Sales Trends (Time Series)
        proj_id, ds_id = ensure_data_source_exists(api_client, sales_trends_path, "UserScenario_SalesTrends")
        result2 = runner.run_batch("Batch2_SalesTrends", "sales_16_quarterly_trends_5years.csv", proj_id, ds_id, BATCH2_QUERIES)
        all_results.append(result2)
        
        # Batch 3: PII Detection
        proj_id, ds_id = ensure_data_source_exists(api_client, employees_pii_path, "UserScenario_PIIDetection")
        result3 = runner.run_batch("Batch3_PIIDetection", "employees_pii.csv", proj_id, ds_id, BATCH3_QUERIES)
        all_results.append(result3)
        
        # Batch 4: Data Quality
        proj_id, ds_id = ensure_data_source_exists(api_client, mixed_quality_path, "UserScenario_MixedQuality")
        result4 = runner.run_batch("Batch4_MixedQuality", "data_mixed_quality.csv", proj_id, ds_id, BATCH4_QUERIES)
        all_results.append(result4)
        
        # Batch 5: Multi-Source (requires special handling)
        logger.info("\n" + "="*60)
        logger.info("BATCH 5: Multi-Source RAG Testing")
        logger.info("="*60)
        
        # Create multi-source project
        unique_name = f"MultiSource_FullSuite_{uuid.uuid4().hex[:6]}"
        proj_resp = api_client.post("/projects", json={
            "name": unique_name,
            "description": "Multi-source RAG for full suite"
        })
        if proj_resp.status_code == 200:
            ms_project_id = proj_resp.json()["id"]
            ms_ds_ids = []
            ms_source_names = []
            
            # Import both PII files
            for path, name in [(customers_pii_path, "customers_pii.csv"), (employees_pii_path, "employees_pii.csv")]:
                import_resp = api_client.upload_file(
                    "/datasources/connect",
                    path,
                    data={'project_id': str(ms_project_id), 'source_type': 'file'}
                )
                if import_resp.status_code == 200:
                    ds_id = import_resp.json()["data_source_id"]
                    ms_ds_ids.append(ds_id)
                    ms_source_names.append(name)
                    wait_for_import_indexed(api_client, ds_id, max_wait=120)
            
            if len(ms_ds_ids) >= 2:
                ms_runner = MultiSourceTestRunner(api_client, evaluator, reporter)
                result5 = ms_runner.run_multi_source_batch(
                    batch_name="Batch5_MultiSource",
                    project_id=ms_project_id,
                    data_source_ids=ms_ds_ids,
                    source_names=ms_source_names,
                    queries=BATCH5_QUERIES
                )
                all_results.append(result5)
        
        # Generate summary report
        summary_file = reporter.generate_summary_report(all_results)
        logger.info(f"\n{'='*60}")
        logger.info(f"FULL SUITE COMPLETE (5 Batches)")
        logger.info(f"Summary report: {summary_file}")
        logger.info(f"{'='*60}")
        
        # Overall assertions
        total_passed = sum(r.passed_queries for r in all_results)
        total_queries = sum(r.total_queries for r in all_results)
        overall_rate = total_passed / total_queries if total_queries > 0 else 0
        
        assert overall_rate >= 0.5, f"Overall pass rate {overall_rate:.0%} below 50% threshold"
