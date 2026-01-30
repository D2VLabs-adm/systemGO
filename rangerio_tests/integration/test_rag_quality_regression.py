"""
RAG Quality Regression Tests for RangerIO

These tests maintain a golden dataset of queries that MUST work correctly.
Failures indicate quality regressions that need to be fixed in:
- Embedding model
- Retrieval strategy
- Prompt engineering
- LLM configuration

The tests are strict by design - they catch real quality issues.
"""
import pytest
import time
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from rangerio_tests.config import config, logger


# ============================================================================
# Golden Dataset - Queries that MUST work
# ============================================================================

@dataclass
class GoldenQuery:
    """A query in the golden dataset with expected characteristics."""
    id: str
    query: str
    category: str
    must_contain: List[str] = None
    must_contain_any: List[str] = None
    must_not_contain: List[str] = None
    must_be_numeric: bool = False
    must_reference_data: bool = True
    min_answer_length: int = 20
    max_response_time_s: float = 60.0
    description: str = ""
    
    def __post_init__(self):
        self.must_contain = self.must_contain or []
        self.must_contain_any = self.must_contain_any or []
        self.must_not_contain = self.must_not_contain or []


# Golden queries organized by category
GOLDEN_QUERIES = [
    # === FACTUAL QUERIES ===
    # These should return specific facts from the data
    GoldenQuery(
        id="fact_001",
        query="How many rows or records are in this dataset?",
        category="factual",
        must_contain_any=["700", "record", "row", "entries"],
        must_not_contain=["don't know", "cannot", "unable"],
        description="Basic row count - fundamental data awareness"
    ),
    GoldenQuery(
        id="fact_002",
        query="What columns or fields are in the data?",
        category="factual",
        must_contain_any=["segment", "country", "product", "sales", "profit", "column", "field"],
        must_not_contain=["don't know"],
        description="Column awareness - must know data structure"
    ),
    GoldenQuery(
        id="fact_003",
        query="What are the unique segments in this data?",
        category="factual",
        must_contain_any=["government", "small business", "enterprise", "midmarket", "channel partners"],
        must_not_contain=["don't know"],
        min_answer_length=30,
        description="Categorical value extraction"
    ),
    GoldenQuery(
        id="fact_004",
        query="What countries are represented in the dataset?",
        category="factual",
        must_contain_any=["united states", "canada", "france", "germany", "mexico", "country"],
        must_not_contain=["don't know"],
        description="Geographic data awareness"
    ),
    
    # === NUMERIC QUERIES ===
    # These should return numeric calculations
    GoldenQuery(
        id="num_001",
        query="What is the total sales revenue?",
        category="numeric",
        must_be_numeric=True,
        must_not_contain=["don't know", "cannot calculate"],
        description="Basic aggregation - sum of sales"
    ),
    GoldenQuery(
        id="num_002",
        query="What is the total profit?",
        category="numeric",
        must_be_numeric=True,
        must_not_contain=["don't know"],
        description="Profit aggregation"
    ),
    GoldenQuery(
        id="num_003",
        query="What is the average discount percentage?",
        category="numeric",
        must_be_numeric=True,
        must_contain_any=["discount", "%", "percent", "average"],
        description="Mean calculation with percentage"
    ),
    
    # === ANALYTICAL QUERIES ===
    # These require reasoning about the data
    GoldenQuery(
        id="anal_001",
        query="Which segment has the highest sales?",
        category="analytical",
        must_contain_any=["government", "enterprise", "small business", "highest", "most"],
        must_not_contain=["don't know"],
        min_answer_length=30,
        description="Max aggregation by category"
    ),
    GoldenQuery(
        id="anal_002",
        query="What product category is most profitable?",
        category="analytical",
        must_reference_data=True,
        must_not_contain=["don't know"],
        min_answer_length=30,
        description="Profit analysis by product"
    ),
    GoldenQuery(
        id="anal_003",
        query="How does government segment compare to enterprise segment in terms of sales?",
        category="analytical",
        must_contain_any=["government", "enterprise", "compare", "higher", "lower", "more", "less"],
        must_not_contain=["don't know"],
        min_answer_length=50,
        max_response_time_s=90.0,
        description="Comparative analysis between segments"
    ),
    
    # === SUMMARY QUERIES ===
    # These require synthesizing information
    GoldenQuery(
        id="sum_001",
        query="Summarize the key insights from this financial data.",
        category="summary",
        must_reference_data=True,
        min_answer_length=100,
        max_response_time_s=90.0,
        description="High-level data summary"
    ),
    GoldenQuery(
        id="sum_002",
        query="What are the main trends visible in this data?",
        category="summary",
        must_reference_data=True,
        must_contain_any=["trend", "pattern", "growth", "increase", "decrease", "sales", "profit"],
        min_answer_length=50,
        description="Trend identification"
    ),
    
    # === EDGE CASES ===
    # Queries that should be handled gracefully
    GoldenQuery(
        id="edge_001",
        query="What is the CEO's salary?",
        category="edge_case",
        must_not_contain=["$50,000", "$100,000", "$1,000,000"],  # Should not hallucinate
        must_reference_data=False,
        description="Out of scope query - should not hallucinate"
    ),
    GoldenQuery(
        id="edge_002",
        query="Predict next year's sales.",
        category="edge_case",
        must_not_contain=["will be exactly", "definitely will"],  # Should express uncertainty
        must_reference_data=True,
        description="Prediction request - should use available data and express uncertainty"
    ),
]


# Ingestion wait
RAG_INGESTION_WAIT = 45


@dataclass
class QueryResult:
    """Result of running a golden query."""
    query: GoldenQuery
    answer: str
    response_time: float
    passed: bool
    failures: List[str]
    status_code: int


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def golden_rag(api_client, financial_sample):
    """Create a RAG with financial data for golden query testing.
    
    Returns a dict with:
        - project_id: The RAG project ID
        - data_source_ids: List of data source IDs (needed for RAG query filtering!)
    
    Uses intelligent polling to ensure data is indexed before returning.
    """
    import uuid
    from rangerio_tests.utils.wait_utils import wait_for_import_indexed, wait_for_task_complete
    
    response = api_client.post("/projects", json={
        "name": f"Golden Query Test RAG_{uuid.uuid4().hex[:8]}",
        "description": "RAG for quality regression testing"
    })
    assert response.status_code == 200
    rag_id = response.json()["id"]
    
    response = api_client.upload_file(
        "/datasources/connect",
        financial_sample,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    assert response.status_code == 200
    
    # Extract data_source_id and task_id from the upload response
    upload_result = response.json()
    data_source_id = upload_result.get("id") or upload_result.get("data_source_id")
    task_id = upload_result.get("task_id")
    
    if not data_source_id:
        # Fallback: Query the datasources endpoint
        ds_response = api_client.get(f"/datasources?project_id={rag_id}")
        if ds_response.status_code == 200:
            datasources = ds_response.json()
            if datasources:
                data_source_id = datasources[0].get("id")
    
    logger.info(f"Upload complete: data_source_id={data_source_id}, task_id={task_id}")
    
    # Wait for indexing using intelligent polling
    if task_id:
        logger.info(f"Waiting for profiling task {task_id} to complete...")
        wait_for_task_complete(api_client, task_id, max_wait=90)
    
    if data_source_id:
        logger.info(f"Waiting for data source {data_source_id} to be indexed...")
        wait_for_import_indexed(api_client, data_source_id, max_wait=90)
    else:
        # Fallback: fixed wait if we can't get data source ID
        logger.warning("No data_source_id found, using fixed wait")
        time.sleep(RAG_INGESTION_WAIT)
    
    logger.info(f"Created golden query RAG: project_id={rag_id}, data_source_id={data_source_id}")
    
    yield {
        "project_id": rag_id,
        "data_source_ids": [data_source_id] if data_source_id else []
    }
    
    try:
        api_client.delete(f"/projects/{rag_id}")
    except Exception as e:
        logger.warning(f"Failed to cleanup RAG {rag_id}: {e}")


# ============================================================================
# Query Validation
# ============================================================================

class QueryValidator:
    """Validates query results against golden expectations."""
    
    @staticmethod
    def validate(query: GoldenQuery, answer: str, response_time: float) -> List[str]:
        """
        Validate an answer against golden query expectations.
        Returns list of failure reasons (empty if passed).
        """
        failures = []
        answer_lower = answer.lower()
        
        # Response time check
        if response_time > query.max_response_time_s:
            failures.append(
                f"Response time {response_time:.1f}s > max {query.max_response_time_s}s"
            )
        
        # Minimum length check
        if len(answer) < query.min_answer_length:
            failures.append(
                f"Answer too short: {len(answer)} chars < {query.min_answer_length}"
            )
        
        # Must contain checks
        for term in query.must_contain:
            if term.lower() not in answer_lower:
                failures.append(f"Missing required term: '{term}'")
        
        # Must contain any checks
        if query.must_contain_any:
            found_any = any(term.lower() in answer_lower for term in query.must_contain_any)
            if not found_any:
                failures.append(f"Missing all of: {query.must_contain_any}")
        
        # Must not contain checks
        for term in query.must_not_contain:
            if term.lower() in answer_lower:
                failures.append(f"Contains forbidden term: '{term}'")
        
        # Numeric check
        if query.must_be_numeric:
            if not re.search(r'\d+\.?\d*', answer):
                failures.append("Answer should contain numeric values")
        
        # Data reference check
        if query.must_reference_data:
            data_indicators = ['data', 'dataset', 'table', 'record', 'row', 'column',
                             'sales', 'profit', 'segment', 'country', 'product']
            if not any(ind in answer_lower for ind in data_indicators):
                failures.append("Answer should reference the data")
        
        return failures


# ============================================================================
# Test Classes
# ============================================================================

@pytest.mark.integration
@pytest.mark.quality
@pytest.mark.regression
class TestGoldenQueries:
    """Run all golden queries and validate results."""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client, golden_rag):
        """Setup for each test."""
        self.api_client = api_client
        self.project_id = golden_rag["project_id"]
        self.data_source_ids = golden_rag["data_source_ids"]
    
    def run_query(self, query: GoldenQuery) -> QueryResult:
        """Execute a golden query and validate the result."""
        start = time.time()
        
        try:
            # CRITICAL FIX: Pass data_source_ids for proper RAG filtering
            # Without this, the query searches ALL documents and returns "I don't know"
            response = self.api_client.post("/rag/query", json={
                "prompt": query.query,
                "project_id": self.project_id,
                "data_source_ids": self.data_source_ids  # This is the key fix!
            }, timeout=int(query.max_response_time_s) + 30)
            
            response_time = time.time() - start
            
            if response.status_code != 200:
                return QueryResult(
                    query=query,
                    answer="",
                    response_time=response_time,
                    passed=False,
                    failures=[f"HTTP {response.status_code}: {response.text[:200]}"],
                    status_code=response.status_code
                )
            
            answer = response.json().get("answer", "")
            failures = QueryValidator.validate(query, answer, response_time)
            
            return QueryResult(
                query=query,
                answer=answer,
                response_time=response_time,
                passed=len(failures) == 0,
                failures=failures,
                status_code=response.status_code
            )
        
        except Exception as e:
            return QueryResult(
                query=query,
                answer="",
                response_time=time.time() - start,
                passed=False,
                failures=[f"Exception: {str(e)}"],
                status_code=0
            )
    
    # === Factual Query Tests ===
    
    @pytest.mark.parametrize("query", 
        [q for q in GOLDEN_QUERIES if q.category == "factual"],
        ids=lambda q: q.id
    )
    def test_factual_queries(self, query):
        """
        Factual queries must return correct facts from the data.
        
        Failures indicate:
        - Poor retrieval (context not found)
        - Poor answer extraction (facts not extracted from context)
        """
        result = self.run_query(query)
        
        logger.info(f"\n[{query.id}] {query.query}")
        logger.info(f"  Answer: {result.answer[:100]}..." if len(result.answer) > 100 else f"  Answer: {result.answer}")
        logger.info(f"  Time: {result.response_time:.2f}s")
        
        if not result.passed:
            logger.error(f"  FAILURES: {result.failures}")
        
        assert result.passed, f"Golden query {query.id} failed: {result.failures}"
    
    # === Numeric Query Tests ===
    
    @pytest.mark.parametrize("query",
        [q for q in GOLDEN_QUERIES if q.category == "numeric"],
        ids=lambda q: q.id
    )
    def test_numeric_queries(self, query):
        """
        Numeric queries must return calculated values.
        
        Failures indicate:
        - Inability to perform calculations
        - Data not being used for computation
        """
        result = self.run_query(query)
        
        logger.info(f"\n[{query.id}] {query.query}")
        logger.info(f"  Answer: {result.answer[:100]}...")
        logger.info(f"  Time: {result.response_time:.2f}s")
        
        if not result.passed:
            logger.error(f"  FAILURES: {result.failures}")
        
        assert result.passed, f"Golden query {query.id} failed: {result.failures}"
    
    # === Analytical Query Tests ===
    
    @pytest.mark.parametrize("query",
        [q for q in GOLDEN_QUERIES if q.category == "analytical"],
        ids=lambda q: q.id
    )
    def test_analytical_queries(self, query):
        """
        Analytical queries must show reasoning about the data.
        
        Failures indicate:
        - Poor comparative analysis
        - Inability to synthesize information
        """
        result = self.run_query(query)
        
        logger.info(f"\n[{query.id}] {query.query}")
        logger.info(f"  Answer: {result.answer[:150]}...")
        logger.info(f"  Time: {result.response_time:.2f}s")
        
        if not result.passed:
            logger.error(f"  FAILURES: {result.failures}")
        
        assert result.passed, f"Golden query {query.id} failed: {result.failures}"
    
    # === Summary Query Tests ===
    
    @pytest.mark.parametrize("query",
        [q for q in GOLDEN_QUERIES if q.category == "summary"],
        ids=lambda q: q.id
    )
    def test_summary_queries(self, query):
        """
        Summary queries must provide coherent overviews.
        
        Failures indicate:
        - Poor information synthesis
        - Missing key data points
        """
        result = self.run_query(query)
        
        logger.info(f"\n[{query.id}] {query.query}")
        logger.info(f"  Answer: {result.answer[:200]}...")
        logger.info(f"  Time: {result.response_time:.2f}s")
        
        if not result.passed:
            logger.error(f"  FAILURES: {result.failures}")
        
        assert result.passed, f"Golden query {query.id} failed: {result.failures}"
    
    # === Edge Case Tests ===
    
    @pytest.mark.parametrize("query",
        [q for q in GOLDEN_QUERIES if q.category == "edge_case"],
        ids=lambda q: q.id
    )
    def test_edge_cases(self, query):
        """
        Edge cases must be handled gracefully without hallucination.
        
        Failures indicate:
        - Hallucination (making up facts)
        - Overconfident predictions
        """
        result = self.run_query(query)
        
        logger.info(f"\n[{query.id}] {query.query}")
        logger.info(f"  Answer: {result.answer[:150]}...")
        logger.info(f"  Time: {result.response_time:.2f}s")
        
        if not result.passed:
            logger.error(f"  FAILURES: {result.failures}")
        
        assert result.passed, f"Golden query {query.id} failed: {result.failures}"


# ============================================================================
# Quality Metrics Aggregation
# ============================================================================

@pytest.mark.integration
@pytest.mark.quality
@pytest.mark.regression
class TestQualityMetrics:
    """Aggregate quality metrics across all golden queries."""
    
    def test_overall_quality_score(self, api_client, golden_rag):
        """
        Run all golden queries and calculate overall quality score.
        
        This provides a single metric for RAG quality.
        Minimum passing score: 80%
        """
        results = []
        
        for query in GOLDEN_QUERIES:
            start = time.time()
            try:
                response = api_client.post("/rag/query", json={
                    "prompt": query.query,
                    "project_id": golden_rag
                }, timeout=120)
                
                response_time = time.time() - start
                answer = response.json().get("answer", "") if response.status_code == 200 else ""
                failures = QueryValidator.validate(query, answer, response_time)
                
                results.append({
                    'id': query.id,
                    'category': query.category,
                    'passed': len(failures) == 0,
                    'failures': failures,
                    'response_time': response_time
                })
            except Exception as e:
                results.append({
                    'id': query.id,
                    'category': query.category,
                    'passed': False,
                    'failures': [str(e)],
                    'response_time': time.time() - start
                })
        
        # Calculate metrics
        total = len(results)
        passed = sum(1 for r in results if r['passed'])
        overall_score = passed / total if total > 0 else 0
        
        # By category
        categories = {}
        for r in results:
            cat = r['category']
            if cat not in categories:
                categories[cat] = {'passed': 0, 'total': 0}
            categories[cat]['total'] += 1
            if r['passed']:
                categories[cat]['passed'] += 1
        
        # Report
        logger.info(f"\n{'='*70}")
        logger.info(f"GOLDEN QUERY QUALITY REPORT")
        logger.info(f"{'='*70}")
        logger.info(f"\nOVERALL SCORE: {overall_score*100:.1f}% ({passed}/{total})")
        logger.info(f"\nBy Category:")
        for cat, stats in categories.items():
            cat_score = stats['passed'] / stats['total'] if stats['total'] > 0 else 0
            bar = "█" * int(cat_score * 20) + "░" * (20 - int(cat_score * 20))
            logger.info(f"  {cat:12s} {bar} {cat_score*100:.0f}% ({stats['passed']}/{stats['total']})")
        
        logger.info(f"\nFailed Queries:")
        for r in results:
            if not r['passed']:
                logger.info(f"  ✗ [{r['id']}] {r['failures'][:2]}")
        
        logger.info(f"{'='*70}\n")
        
        # Assertion - minimum 80% quality score
        assert overall_score >= 0.80, \
            f"Overall quality score {overall_score*100:.1f}% is below minimum 80%"
        
        # Category-specific minimums
        for cat, stats in categories.items():
            cat_score = stats['passed'] / stats['total'] if stats['total'] > 0 else 0
            if cat == "edge_case":
                min_score = 0.50  # Edge cases are harder
            else:
                min_score = 0.70  # Other categories need 70%
            
            assert cat_score >= min_score, \
                f"Category '{cat}' score {cat_score*100:.1f}% below minimum {min_score*100:.0f}%"


# ============================================================================
# Hallucination Detection Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.quality
@pytest.mark.regression
class TestHallucinationPrevention:
    """Tests specifically for hallucination prevention."""
    
    HALLUCINATION_QUERIES = [
        {
            "query": "What was the exact revenue on January 15, 2014?",
            "forbidden": ["$12,345", "$98,765", "exactly $"],  # Made up specific values
            "description": "Should not invent specific daily figures"
        },
        {
            "query": "Who is the sales manager mentioned in the data?",
            "forbidden": ["john", "jane", "mike", "sarah", "manager named"],  # Made up names
            "description": "Should not invent people"
        },
        {
            "query": "What percentage growth did we see in Q4?",
            "forbidden": ["exactly 15%", "precisely 23%", "growth of 47%"],  # Made up percentages
            "description": "Should not invent specific growth figures"
        },
    ]
    
    def test_hallucination_queries(self, api_client, golden_rag):
        """
        These queries should NOT produce made-up specific facts.
        
        The system should either:
        - Admit it doesn't have that specific information
        - Provide general information without making up specifics
        """
        hallucinations_detected = 0
        
        for test in self.HALLUCINATION_QUERIES:
            response = api_client.post("/rag/query", json={
                "prompt": test["query"],
                "project_id": golden_rag
            }, timeout=90)
            
            if response.status_code != 200:
                continue
            
            answer = response.json().get("answer", "").lower()
            
            for forbidden in test["forbidden"]:
                if forbidden.lower() in answer:
                    hallucinations_detected += 1
                    logger.warning(f"HALLUCINATION: '{forbidden}' found in answer to '{test['query']}'")
                    logger.warning(f"  Answer: {answer[:200]}...")
        
        total_checks = len(self.HALLUCINATION_QUERIES) * 3  # ~3 forbidden per query
        hallucination_rate = hallucinations_detected / total_checks if total_checks > 0 else 0
        
        logger.info(f"Hallucination rate: {hallucination_rate*100:.1f}% ({hallucinations_detected}/{total_checks})")
        
        # Hallucination rate should be under 10%
        assert hallucination_rate < 0.10, \
            f"Hallucination rate {hallucination_rate*100:.1f}% exceeds 10% threshold"
