"""
Diagnostic Performance Tests for RangerIO

These tests run performance profiling and generate actionable
optimization recommendations at the end.

Run with:
    pytest rangerio_tests/integration/test_with_diagnostics.py -v -s

The -s flag is important to see the diagnostic report output.
"""
import pytest
import time
from pathlib import Path
from typing import Dict, Any

from rangerio_tests.config import config, logger
from rangerio_tests.utils.performance_diagnostics import PerformanceDiagnostics
from rangerio_tests.utils.diagnostic_reporter import DiagnosticReporter, print_diagnostic_report


# ============================================================================
# Module-level diagnostics (shared across all tests in this file)
# ============================================================================

_diagnostics = PerformanceDiagnostics()
RAG_INGESTION_WAIT = 45


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def diagnostics():
    """Shared diagnostics instance for the test module."""
    _diagnostics.reset()
    return _diagnostics


@pytest.fixture(scope="module")
def diagnostic_rag(api_client, financial_sample):
    """Create a RAG with data for diagnostic testing."""
    _diagnostics.snapshot_memory("before_rag_creation")
    
    import uuid
    response = api_client.post("/projects", json={
        "name": f"Diagnostic Test RAG_{uuid.uuid4().hex[:8]}",
        "description": "RAG for diagnostic performance testing"
    })
    assert response.status_code == 200
    rag_id = response.json()["id"]
    
    _diagnostics.snapshot_memory("after_rag_creation")
    
    response = api_client.upload_file(
        "/datasources/connect",
        financial_sample,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    assert response.status_code == 200
    
    _diagnostics.snapshot_memory("after_data_import")
    
    logger.info(f"Waiting for RAG indexing ({RAG_INGESTION_WAIT}s)...")
    time.sleep(RAG_INGESTION_WAIT)
    
    _diagnostics.snapshot_memory("after_indexing")
    
    logger.info(f"Created diagnostic test RAG: {rag_id}")
    yield rag_id
    
    try:
        api_client.delete(f"/projects/{rag_id}")
    except Exception as e:
        logger.warning(f"Failed to cleanup RAG {rag_id}: {e}")


# ============================================================================
# Diagnostic Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.diagnostics
class TestDiagnosticPerformance:
    """
    Performance tests that collect diagnostic data.
    
    Run these tests to get optimization recommendations.
    """
    
    def test_baseline_memory(self, api_client, diagnostics):
        """Record baseline memory usage."""
        diagnostics.snapshot_memory("baseline")
        
        # Simple health check
        response = api_client.get("/health")
        assert response.status_code == 200
        
        diagnostics.snapshot_memory("after_health_check")
        
        memory = diagnostics.analyze_memory_trend()
        logger.info(f"Baseline memory: {memory.get('baseline_mb', 0):.0f}MB")
    
    def test_query_timing_collection(self, api_client, diagnostic_rag, diagnostics):
        """
        Run multiple queries to collect timing data.
        
        This test collects data for the diagnostic report.
        """
        test_queries = [
            "What is the total sales revenue?",
            "How many rows are in the dataset?",
            "What are the main segments?",
            "Summarize the financial data.",
            "What is the average profit margin?",
            "List the top products by sales.",
            "What countries are in the data?",
            "What is the total profit?",
            "Show monthly trends.",
            "What is the discount analysis?",
        ]
        
        for query in test_queries:
            with diagnostics.profile_query(api_client, diagnostic_rag, query) as result:
                pass
            
            timing = result["timing"]
            status = "✓" if timing.success else "✗"
            logger.info(f"  {status} [{timing.total_ms/1000:.1f}s] {query[:40]}...")
        
        # Verify we collected data
        assert len(diagnostics.query_timings) >= len(test_queries)
    
    def test_memory_stability(self, api_client, diagnostic_rag, diagnostics):
        """
        Test memory stability over multiple queries.
        
        Memory should not grow significantly.
        """
        diagnostics.snapshot_memory("before_stability_test")
        
        # Run queries
        for i in range(5):
            with diagnostics.profile_query(
                api_client, diagnostic_rag, 
                f"Query {i}: What is the revenue?"
            ) as result:
                pass
            
            diagnostics.snapshot_memory(f"after_query_{i}")
        
        memory = diagnostics.analyze_memory_trend()
        logger.info(f"Memory trend: {memory.get('trend', 'unknown')} "
                   f"({memory.get('growth_mb', 0):+.0f}MB)")
    
    def test_response_time_distribution(self, api_client, diagnostic_rag, diagnostics):
        """
        Analyze response time distribution.
        
        Checks P50, P95, P99 percentiles.
        """
        # Run varied queries
        queries = [
            "Simple: row count?",
            "Medium: summarize sales by segment",
            "Complex: analyze trends and provide recommendations",
        ] * 3
        
        for query in queries:
            with diagnostics.profile_query(api_client, diagnostic_rag, query) as result:
                pass
        
        percentiles = diagnostics.calculate_percentiles()
        
        logger.info(f"\nResponse Time Distribution:")
        logger.info(f"  P50: {percentiles['p50']/1000:.1f}s")
        logger.info(f"  P95: {percentiles['p95']/1000:.1f}s")
        logger.info(f"  P99: {percentiles['p99']/1000:.1f}s")


@pytest.mark.integration
@pytest.mark.diagnostics
class TestBackendMetrics:
    """
    Tests that fetch metrics from the backend's metrics endpoints.
    """
    
    def test_fetch_query_breakdown(self, api_client, diagnostic_rag, diagnostics):
        """
        Fetch query breakdown from backend metrics endpoint.
        """
        # First, run a query to generate metrics
        with diagnostics.profile_query(
            api_client, diagnostic_rag, 
            "Generate metrics: What is total sales?"
        ) as result:
            pass
        
        # Fetch breakdown from backend
        response = api_client.get("/metrics/query-breakdown?limit=10")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"\nBackend Query Breakdown:")
            logger.info(f"  Queries tracked: {data.get('averages', {}).get('query_count', 0)}")
            logger.info(f"  Avg total: {data.get('averages', {}).get('avg_total_ms', 0)/1000:.1f}s")
            logger.info(f"  LLM %: {data.get('averages', {}).get('llm_pct', 0):.0f}%")
            logger.info(f"  Retrieval %: {data.get('averages', {}).get('retrieval_pct', 0):.0f}%")
            
            if data.get("recommendations"):
                logger.info(f"\nBackend Recommendations:")
                for rec in data["recommendations"]:
                    logger.info(f"  [{rec['priority']}] {rec['category']}: {rec['issue']}")
        else:
            logger.info(f"Query breakdown endpoint returned {response.status_code}")
    
    def test_fetch_performance_report(self, api_client, diagnostics):
        """
        Fetch comprehensive performance report from backend.
        """
        response = api_client.get("/metrics/performance-report")
        
        if response.status_code == 200:
            report = response.json()
            logger.info(f"\nBackend Performance Report:")
            logger.info(f"  Grade: {report.get('grade', 'N/A')} - {report.get('grade_description', '')}")
            logger.info(f"  Total operations: {report.get('summary', {}).get('total_operations', 0)}")
            
            if report.get("bottlenecks"):
                logger.info(f"\nIdentified Bottlenecks:")
                for bn in report["bottlenecks"]:
                    logger.info(f"  [{bn['severity'].upper()}] {bn['type']}: {bn['description']}")
        else:
            logger.info(f"Performance report endpoint returned {response.status_code}")


# ============================================================================
# Session-End Diagnostic Report
# ============================================================================

@pytest.fixture(scope="module", autouse=True)
def print_diagnostic_report_at_end(request):
    """
    Print the diagnostic report when all tests in this module complete.
    """
    yield
    
    # After all tests
    if _diagnostics.query_timings:
        print("\n")
        print_diagnostic_report(_diagnostics)
        
        # Save report to file
        reporter = DiagnosticReporter(_diagnostics)
        report_dir = Path(config.REPORTS_DIR) / "diagnostics"
        paths = reporter.save_report(report_dir, format="both")
        
        print(f"\n📁 Reports saved to:")
        for fmt, path in paths.items():
            print(f"   {fmt}: {path}")
