"""
User Quality Scenarios - True E2E Testing
==========================================

Tests that simulate real user expectations for response quality.
Each scenario includes:
1. Data import with known content
2. RAG creation and indexing
3. Questions with expected answer patterns
4. Quality validation using LLM-as-judge

These tests validate that RangerIO delivers answers that meet user expectations,
not just that the system runs without errors.

Run with:
    PYTHONPATH=. pytest rangerio_tests/integration/test_user_quality_scenarios.py -v -s
"""
import pytest
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from rangerio_tests.config import config
from rangerio_tests.utils.accuracy_evaluator import (
    AccuracyEvaluator, QuerySpec, QueryType, AccuracyVerdict, EvaluationResult
)

logger = logging.getLogger("rangerio_tests.quality")

# Timeouts
IMPORT_TIMEOUT = 120
RAG_READY_TIMEOUT = 60
QUERY_TIMEOUT = 90


@dataclass
class QualityExpectation:
    """Define user expectations for a query"""
    query: str
    query_type: QueryType
    description: str
    
    # What the answer MUST contain (case-insensitive)
    must_contain: List[str] = field(default_factory=list)
    
    # What the answer must NOT contain
    must_not_contain: List[str] = field(default_factory=list)
    
    # Minimum quality scores (0-10)
    min_accuracy: float = 6.0
    min_relevance: float = 6.0
    
    # Allow "I don't know" responses?
    allow_no_answer: bool = False
    
    # Ground truth (if known)
    ground_truth: Optional[str] = None


@dataclass  
class ScenarioResult:
    """Result of a complete scenario"""
    scenario_name: str
    passed: bool
    total_queries: int
    passed_queries: int
    failed_queries: int
    avg_accuracy: float
    avg_relevance: float
    details: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class QualityScenarioRunner:
    """Runs quality scenarios against RangerIO"""
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.evaluator = AccuracyEvaluator(config.BACKEND_URL)
        self.logger = logging.getLogger("rangerio_tests.quality")
    
    def import_and_create_rag(self, file_path: Path, project_name: str = "Quality Test") -> Optional[int]:
        """Import a file and create a RAG, return RAG ID"""
        try:
            # 1. Ensure project exists
            project_id = self._get_or_create_project(project_name)
            if not project_id:
                return None
            
            # 2. Import file
            with open(file_path, 'rb') as f:
                response = self.api_client.post(
                    "/datasources/import",
                    files={"file": (file_path.name, f)},
                    data={"project_id": project_id}
                )
            
            if response.status_code != 200:
                self.logger.error(f"Import failed: {response.status_code} - {response.text}")
                return None
            
            ds_id = response.json().get("id")
            self.logger.info(f"Imported {file_path.name} as datasource {ds_id}")
            
            # 3. Wait for import to complete
            if not self._wait_for_datasource_ready(ds_id):
                return None
            
            # 4. Create RAG
            rag_response = self.api_client.post(
                "/rags",
                json={
                    "name": f"Quality Test - {file_path.stem}",
                    "data_source_ids": [ds_id],
                    "project_id": project_id
                }
            )
            
            if rag_response.status_code != 200:
                self.logger.error(f"RAG creation failed: {rag_response.text}")
                return None
            
            rag_id = rag_response.json().get("id")
            self.logger.info(f"Created RAG {rag_id}")
            
            # 5. Wait for RAG to be ready
            if not self._wait_for_rag_ready(rag_id):
                return None
            
            return rag_id
            
        except Exception as e:
            self.logger.error(f"Import/RAG creation failed: {e}")
            return None
    
    def _get_or_create_project(self, name: str) -> Optional[int]:
        """Get existing project or create new one"""
        try:
            # Try to find existing
            response = self.api_client.get("/projects")
            if response.status_code == 200:
                for project in response.json():
                    if project.get("name") == name:
                        return project.get("id")
            
            # Create new
            response = self.api_client.post("/projects", json={"name": name})
            if response.status_code == 200:
                return response.json().get("id")
            
            return None
        except Exception as e:
            self.logger.error(f"Project creation failed: {e}")
            return None
    
    def _wait_for_datasource_ready(self, ds_id: int, timeout: int = IMPORT_TIMEOUT) -> bool:
        """Wait for datasource to be ready"""
        start = time.time()
        while time.time() - start < timeout:
            try:
                response = self.api_client.get(f"/datasources/{ds_id}")
                if response.status_code == 200:
                    status = response.json().get("status", "")
                    if status in ["ready", "completed", "indexed"]:
                        return True
                    if status in ["error", "failed"]:
                        self.logger.error(f"Datasource {ds_id} failed: {response.json()}")
                        return False
            except Exception:
                pass
            time.sleep(2)
        self.logger.error(f"Datasource {ds_id} timeout after {timeout}s")
        return False
    
    def _wait_for_rag_ready(self, rag_id: int, timeout: int = RAG_READY_TIMEOUT) -> bool:
        """Wait for RAG to be indexed and ready"""
        start = time.time()
        while time.time() - start < timeout:
            try:
                response = self.api_client.get(f"/rags/{rag_id}")
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status", "")
                    doc_count = data.get("document_count", 0)
                    if status in ["ready", "indexed"] or doc_count > 0:
                        self.logger.info(f"RAG {rag_id} ready with {doc_count} documents")
                        return True
            except Exception:
                pass
            time.sleep(2)
        self.logger.warning(f"RAG {rag_id} may not be fully indexed (timeout)")
        return True  # Continue anyway
    
    def query_rag(self, rag_id: int, query: str, mode: str = "assistant") -> Dict[str, Any]:
        """Query a RAG and return response"""
        try:
            response = self.api_client.post(
                "/rag/query",
                json={
                    "prompt": query,
                    "project_id": rag_id,
                    "assistant_mode": mode == "assistant",
                    "deep_search_mode": mode == "deep_search"
                },
                timeout=QUERY_TIMEOUT
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Query failed: {response.status_code}", "answer": ""}
                
        except Exception as e:
            return {"error": str(e), "answer": ""}
    
    def run_scenario(
        self,
        scenario_name: str,
        rag_id: int,
        expectations: List[QualityExpectation],
        data_context: Optional[str] = None
    ) -> ScenarioResult:
        """Run a complete quality scenario"""
        results = []
        errors = []
        
        for exp in expectations:
            self.logger.info(f"Testing: {exp.description}")
            
            # Query the RAG
            start_time = time.time()
            response = self.query_rag(rag_id, exp.query)
            response_time = time.time() - start_time
            
            answer = response.get("answer", response.get("response", ""))
            
            if response.get("error"):
                errors.append(f"{exp.description}: {response['error']}")
                results.append({
                    "query": exp.query,
                    "passed": False,
                    "error": response["error"]
                })
                continue
            
            # Build QuerySpec for evaluation
            query_spec = QuerySpec(
                query=exp.query,
                query_type=exp.query_type,
                description=exp.description,
                must_contain=exp.must_contain,
                must_not_contain=exp.must_not_contain,
                use_ai_eval=True
            )
            
            # Evaluate response
            eval_result = self.evaluator.evaluate_response(
                query_spec=query_spec,
                response=answer,
                response_time=response_time,
                data_context=data_context
            )
            
            # Check against expectations
            passed = True
            failure_reasons = []
            
            # Check "no answer" handling
            if eval_result.verdict == AccuracyVerdict.NO_ANSWER:
                if not exp.allow_no_answer:
                    passed = False
                    failure_reasons.append("Model refused to answer but answer was expected")
            else:
                # Check minimum scores
                if eval_result.accuracy_score < exp.min_accuracy:
                    passed = False
                    failure_reasons.append(f"Accuracy {eval_result.accuracy_score:.1f} < {exp.min_accuracy}")
                
                if eval_result.relevance_score < exp.min_relevance:
                    passed = False
                    failure_reasons.append(f"Relevance {eval_result.relevance_score:.1f} < {exp.min_relevance}")
                
                # Check required content
                answer_lower = answer.lower()
                for required in exp.must_contain:
                    if required.lower() not in answer_lower:
                        passed = False
                        failure_reasons.append(f"Missing required: '{required}'")
                
                # Check forbidden content
                for forbidden in exp.must_not_contain:
                    if forbidden.lower() in answer_lower:
                        passed = False
                        failure_reasons.append(f"Contains forbidden: '{forbidden}'")
            
            results.append({
                "query": exp.query,
                "description": exp.description,
                "passed": passed,
                "answer_preview": answer[:200] + "..." if len(answer) > 200 else answer,
                "accuracy_score": eval_result.accuracy_score,
                "relevance_score": eval_result.relevance_score,
                "verdict": eval_result.verdict.value,
                "response_time_s": response_time,
                "failure_reasons": failure_reasons,
                "ai_evaluation": eval_result.ai_evaluation
            })
            
            status = "✅" if passed else "❌"
            self.logger.info(f"  {status} Accuracy: {eval_result.accuracy_score:.1f}, Relevance: {eval_result.relevance_score:.1f}")
            if failure_reasons:
                for reason in failure_reasons:
                    self.logger.info(f"     ⚠️  {reason}")
        
        # Calculate summary
        passed_count = sum(1 for r in results if r.get("passed", False))
        accuracy_scores = [r["accuracy_score"] for r in results if "accuracy_score" in r]
        relevance_scores = [r["relevance_score"] for r in results if "relevance_score" in r]
        
        return ScenarioResult(
            scenario_name=scenario_name,
            passed=passed_count == len(expectations) and len(errors) == 0,
            total_queries=len(expectations),
            passed_queries=passed_count,
            failed_queries=len(expectations) - passed_count,
            avg_accuracy=sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0,
            avg_relevance=sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0,
            details=results,
            errors=errors
        )


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def quality_runner(api_client):
    """Quality scenario runner"""
    return QualityScenarioRunner(api_client)


@pytest.fixture(scope="module")
def sales_rag_id(quality_runner):
    """Create RAG from sales data for testing"""
    # Use existing sales test data
    sales_file = Path(__file__).parent.parent / "fixtures" / "test_data" / "sales_data_sample.csv"
    if not sales_file.exists():
        # Try alternative location
        sales_file = Path(__file__).parent.parent.parent / "fixtures" / "test_data" / "sales_usecase" / "sales_data_sample.csv"
    
    if not sales_file.exists():
        pytest.skip("Sales test data not found")
    
    rag_id = quality_runner.import_and_create_rag(sales_file, "Sales Quality Test")
    if not rag_id:
        pytest.skip("Could not create RAG for sales data")
    
    yield rag_id
    
    # Cleanup could be added here


# =============================================================================
# QUALITY SCENARIO TESTS
# =============================================================================

@pytest.mark.quality
class TestSalesAnalystScenario:
    """
    Scenario: A sales analyst imports company sales data and asks
    typical business questions. Tests that answers are accurate and helpful.
    """
    
    def test_basic_data_questions(self, quality_runner, sales_rag_id):
        """Test basic questions about the data"""
        expectations = [
            QualityExpectation(
                query="What columns are in this data?",
                query_type=QueryType.CONTENT_LOOKUP,
                description="Should list data columns",
                must_not_contain=["I don't know", "cannot determine"],
                min_accuracy=5.0,
                min_relevance=6.0
            ),
            QualityExpectation(
                query="How many rows of data are there?",
                query_type=QueryType.AGGREGATION,
                description="Should provide row count",
                must_not_contain=["I don't know"],
                min_accuracy=5.0,
                min_relevance=6.0
            ),
        ]
        
        result = quality_runner.run_scenario(
            "Basic Data Questions",
            sales_rag_id,
            expectations
        )
        
        print(f"\n{'='*60}")
        print(f"Scenario: {result.scenario_name}")
        print(f"Passed: {result.passed_queries}/{result.total_queries}")
        print(f"Avg Accuracy: {result.avg_accuracy:.1f}")
        print(f"Avg Relevance: {result.avg_relevance:.1f}")
        print(f"{'='*60}")
        
        assert result.passed_queries >= result.total_queries * 0.5, \
            f"Less than 50% of queries passed: {result.details}"
    
    def test_aggregation_questions(self, quality_runner, sales_rag_id):
        """Test aggregation/summary questions"""
        expectations = [
            QualityExpectation(
                query="What is the total revenue or sales amount?",
                query_type=QueryType.AGGREGATION,
                description="Should calculate total",
                must_not_contain=["I don't know", "cannot calculate"],
                min_accuracy=5.0,
                min_relevance=6.0
            ),
            QualityExpectation(
                query="What are the different categories or types in the data?",
                query_type=QueryType.CONTENT_LOOKUP,
                description="Should list categories",
                must_not_contain=["I don't know"],
                min_accuracy=5.0,
                min_relevance=6.0
            ),
        ]
        
        result = quality_runner.run_scenario(
            "Aggregation Questions",
            sales_rag_id,
            expectations
        )
        
        assert result.avg_accuracy >= 4.0, f"Average accuracy too low: {result.avg_accuracy}"
    
    def test_insight_questions(self, quality_runner, sales_rag_id):
        """Test insight/analysis questions"""
        expectations = [
            QualityExpectation(
                query="What patterns or trends do you see in this data?",
                query_type=QueryType.TREND_ANALYSIS,
                description="Should identify patterns",
                must_not_contain=["I cannot", "no data"],
                min_accuracy=4.0,
                min_relevance=5.0,
                allow_no_answer=False
            ),
            QualityExpectation(
                query="What recommendations would you make based on this data?",
                query_type=QueryType.COMPLEX_REASONING,
                description="Should provide recommendations",
                min_accuracy=4.0,
                min_relevance=5.0,
                allow_no_answer=False
            ),
        ]
        
        result = quality_runner.run_scenario(
            "Insight Questions",
            sales_rag_id,
            expectations
        )
        
        # More lenient for insight questions
        assert result.passed_queries >= 1, "At least one insight question should pass"


@pytest.mark.quality
class TestHallucinationDetection:
    """
    Scenario: Test that the system doesn't hallucinate information
    that isn't in the data.
    """
    
    def test_no_hallucination_on_unknown(self, quality_runner, sales_rag_id):
        """Test that model doesn't invent data for impossible questions"""
        expectations = [
            QualityExpectation(
                query="What was the CEO's salary last year?",
                query_type=QueryType.CONTENT_LOOKUP,
                description="Should not invent CEO salary (not in sales data)",
                must_not_contain=["$", "salary is", "earns"],
                min_accuracy=3.0,
                min_relevance=3.0,
                allow_no_answer=True  # It's OK to say "I don't know"
            ),
            QualityExpectation(
                query="What is the company's stock price?",
                query_type=QueryType.CONTENT_LOOKUP,
                description="Should not invent stock price",
                must_not_contain=["stock price is", "trading at"],
                min_accuracy=3.0,
                min_relevance=3.0,
                allow_no_answer=True
            ),
        ]
        
        result = quality_runner.run_scenario(
            "Hallucination Detection",
            sales_rag_id,
            expectations
        )
        
        # Check that no hallucinations were detected
        for detail in result.details:
            verdict = detail.get("verdict", "")
            assert verdict != "hallucinated", \
                f"Hallucination detected: {detail.get('query')}"


@pytest.mark.quality  
class TestResponseQualityMetrics:
    """
    Test overall response quality metrics meet minimum standards.
    """
    
    def test_minimum_quality_bar(self, quality_runner, sales_rag_id):
        """Test that responses meet minimum quality bar"""
        expectations = [
            QualityExpectation(
                query="Summarize this data in 2-3 sentences.",
                query_type=QueryType.CONTENT_LOOKUP,
                description="Should provide coherent summary",
                min_accuracy=5.0,
                min_relevance=6.0
            ),
            QualityExpectation(
                query="What is the most important insight from this data?",
                query_type=QueryType.COMPLEX_REASONING,
                description="Should identify key insight",
                min_accuracy=4.0,
                min_relevance=5.0
            ),
            QualityExpectation(
                query="Are there any data quality issues I should be aware of?",
                query_type=QueryType.CONTENT_LOOKUP,
                description="Should assess data quality",
                min_accuracy=4.0,
                min_relevance=5.0
            ),
        ]
        
        result = quality_runner.run_scenario(
            "Minimum Quality Bar",
            sales_rag_id,
            expectations
        )
        
        # Assert minimum standards
        assert result.avg_accuracy >= 4.0, \
            f"Average accuracy {result.avg_accuracy:.1f} below minimum 4.0"
        assert result.avg_relevance >= 4.0, \
            f"Average relevance {result.avg_relevance:.1f} below minimum 4.0"
        assert result.passed_queries >= result.total_queries * 0.5, \
            f"Pass rate below 50%"


# =============================================================================
# SUMMARY REPORT
# =============================================================================

@pytest.fixture(scope="module", autouse=True)
def quality_summary(request):
    """Print quality summary at end of module"""
    yield
    print("\n" + "="*70)
    print("QUALITY SCENARIO TESTING COMPLETE")
    print("="*70)
    print("See individual test output for detailed results.")
    print("="*70 + "\n")
