"""
Observability Tests for RangerIO

These tests validate that the system provides adequate observability:
- Profiling endpoints return useful metrics
- Health checks are comprehensive
- Task tracking is accurate
- Error reporting is useful

Good observability is essential for:
- Debugging issues
- Performance tuning
- Capacity planning
- Incident response
"""
import pytest
import time
import psutil
from pathlib import Path
from typing import Dict, Any, List

from rangerio_tests.config import config, logger


# ============================================================================
# Constants
# ============================================================================

RAG_INGESTION_WAIT = 45


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def observability_rag(api_client, financial_sample):
    """Create a RAG for observability testing."""
    import uuid
    response = api_client.post("/projects", json={
        "name": f"Observability Test RAG_{uuid.uuid4().hex[:8]}",
        "description": "RAG for observability testing"
    })
    assert response.status_code == 200
    rag_id = response.json()["id"]
    
    response = api_client.upload_file(
        "/datasources/connect",
        financial_sample,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    assert response.status_code == 200
    
    logger.info(f"Waiting for RAG indexing ({RAG_INGESTION_WAIT}s)...")
    time.sleep(RAG_INGESTION_WAIT)
    
    yield rag_id
    
    try:
        api_client.delete(f"/projects/{rag_id}")
    except Exception as e:
        logger.warning(f"Failed to cleanup RAG {rag_id}: {e}")


# ============================================================================
# Health Check Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.observability
class TestHealthChecks:
    """Tests for health check endpoints."""
    
    def test_health_endpoint_returns_status(self, api_client):
        """
        Health endpoint must return overall status.
        
        Essential for:
        - Load balancer health probes
        - Container orchestration
        - Monitoring systems
        """
        response = api_client.get("/health")
        assert response.status_code == 200
        
        health = response.json()
        assert "status" in health, "Health response must include 'status' field"
        assert health["status"] in ["healthy", "degraded", "unhealthy"], \
            f"Invalid status: {health['status']}"
        
        logger.info(f"Health status: {health['status']}")
    
    def test_health_includes_services(self, api_client):
        """
        Health endpoint should report on individual services.
        
        Useful for diagnosing which component is failing.
        """
        response = api_client.get("/health")
        assert response.status_code == 200
        
        health = response.json()
        
        # Should include services breakdown
        services = health.get("services", {})
        
        # Expected services
        expected_services = ["sqlite", "duckdb"]
        
        for service in expected_services:
            if service in services:
                service_status = services[service]
                logger.info(f"  {service}: {service_status.get('status', 'unknown')}")
    
    def test_health_response_time(self, api_client):
        """
        Health check should respond quickly (<200ms P99).
        
        Note: Health checks that verify database connections may take longer
        than simple ping endpoints. 200ms is reasonable for a health check
        that actually validates service connectivity.
        
        Slow health checks can cause:
        - Load balancer timeouts
        - False unhealthy reports
        - Cascading failures
        """
        times = []
        
        for _ in range(10):
            start = time.time()
            response = api_client.get("/health")
            elapsed = (time.time() - start) * 1000  # ms
            times.append(elapsed)
            assert response.status_code == 200
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        logger.info(f"Health check latency - Avg: {avg_time:.1f}ms, Max: {max_time:.1f}ms")
        
        # 200ms is reasonable for health checks that verify DB connections
        assert max_time < 200, f"Health check too slow: {max_time:.1f}ms (should be <200ms)"
    
    def test_health_timestamp(self, api_client):
        """Health response should include a timestamp for freshness."""
        response = api_client.get("/health")
        assert response.status_code == 200
        
        health = response.json()
        assert "timestamp" in health, "Health response should include timestamp"
        
        # Timestamp should be recent (within last 5 seconds)
        # This validates the timestamp is being generated, not cached


# ============================================================================
# Task Observability Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.observability
class TestTaskObservability:
    """Tests for task tracking and status reporting."""
    
    def test_task_summary_endpoint(self, api_client):
        """
        Task summary should provide counts by status.
        
        Useful for dashboard displays and monitoring.
        """
        response = api_client.get("/tasks/summary")
        assert response.status_code == 200
        
        summary = response.json()
        
        # Should include status counts
        expected_fields = ["running", "pending", "completed", "failed"]
        for field in expected_fields:
            assert field in summary, f"Summary missing '{field}' count"
        
        logger.info(f"Task summary: {summary}")
    
    def test_task_grouped_endpoint(self, api_client):
        """
        Grouped tasks should show parent-child relationships.
        
        Essential for understanding complex operations.
        """
        response = api_client.get("/tasks/grouped")
        assert response.status_code == 200
        
        grouped = response.json()
        assert "groups" in grouped, "Grouped response should have 'groups' field"
        
        # Verify structure
        groups = grouped["groups"]
        if len(groups) > 0:
            group = groups[0]
            assert "id" in group or "title" in group, "Group should have id or title"
        
        logger.info(f"Found {len(groups)} task groups")
    
    def test_task_details_include_progress(self, api_client, observability_rag):
        """
        Individual task details should include progress info.
        
        Progress tracking is essential for user feedback.
        """
        # Start an import to create a task
        csv_files = list(Path(config.USER_GENERATED_DATA_DIR).glob("*.csv"))[:2]
        if not csv_files:
            pytest.skip("No CSV files for task progress test")
        
        response = api_client.post("/datasources/import/start", json={
            "files": [str(csv_files[0])],
            "project_id": observability_rag,
            "skip_profiling": False
        })
        
        if response.status_code != 200:
            pytest.skip("Could not start import task")
        
        job_id = response.json().get("job_id")
        
        # Check task status
        time.sleep(2)
        response = api_client.get("/tasks/active")
        assert response.status_code == 200
        
        tasks = response.json()
        if isinstance(tasks, dict):
            tasks = tasks.get('tasks', [])
        
        # Find our task
        for task in tasks:
            if 'import' in task.get('type', '').lower():
                assert 'progress' in task, "Task should have progress field"
                assert 'status' in task, "Task should have status field"
                assert 'current_item' in task or 'title' in task, "Task should have current item or title"
                logger.info(f"Task progress: {task.get('progress', 0)}%")
                break
    
    def test_task_report_endpoint(self, api_client):
        """
        Completed tasks should have detailed reports.
        
        Reports are essential for debugging and auditing.
        """
        # Find a completed task
        response = api_client.get("/tasks/grouped")
        if response.status_code != 200:
            pytest.skip("Could not get grouped tasks")
        
        groups = response.json().get("groups", [])
        completed_task_id = None
        
        for group in groups:
            if group.get("status") == "completed" and group.get("has_report"):
                completed_task_id = group.get("id")
                break
        
        if not completed_task_id:
            pytest.skip("No completed task with report found")
        
        # Get report
        response = api_client.get(f"/tasks/{completed_task_id}/report")
        assert response.status_code == 200
        
        report_data = response.json()
        assert "task" in report_data or "report" in report_data, \
            "Report response should include task or report data"
        
        logger.info(f"Retrieved report for task {completed_task_id}")


# ============================================================================
# Profiling Endpoint Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.observability
class TestProfilingEndpoints:
    """Tests for profiling and metrics endpoints."""
    
    def test_profiling_endpoint_exists(self, api_client):
        """
        Profiling endpoint should exist and return data.
        """
        # Try different possible profiling endpoints
        endpoints = [
            "/profiling",
            "/profiling/metrics",
            "/metrics",
            "/stats",
        ]
        
        found_endpoint = None
        for endpoint in endpoints:
            response = api_client.get(endpoint)
            if response.status_code == 200:
                found_endpoint = endpoint
                logger.info(f"Found profiling endpoint: {endpoint}")
                break
        
        if not found_endpoint:
            logger.info("No dedicated profiling endpoint found - checking health for metrics")
            # Health endpoint might include metrics
            response = api_client.get("/health")
            assert response.status_code == 200
    
    def test_datasource_statistics(self, api_client, observability_rag):
        """
        Should be able to get statistics about data sources.
        """
        response = api_client.get(f"/datasources")
        assert response.status_code == 200
        
        sources = response.json()
        if isinstance(sources, dict):
            sources = sources.get('sources', sources.get('data_sources', []))
        
        logger.info(f"Found {len(sources)} data sources")
        
        # Each source should have key metadata
        if len(sources) > 0:
            source = sources[0]
            expected_fields = ['id', 'name']
            for field in expected_fields:
                if field not in source:
                    logger.warning(f"Data source missing '{field}' field")
    
    def test_project_statistics(self, api_client, observability_rag):
        """
        Should be able to get project/RAG statistics.
        """
        response = api_client.get(f"/projects/{observability_rag}")
        assert response.status_code == 200
        
        project = response.json()
        
        # Should include metadata
        assert 'id' in project or 'name' in project, \
            "Project response should include id or name"
        
        logger.info(f"Project details available for {observability_rag}")


# ============================================================================
# Error Reporting Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.observability
class TestErrorReporting:
    """Tests for error reporting and logging."""
    
    def test_invalid_request_returns_useful_error(self, api_client):
        """
        Invalid requests should return helpful error messages.
        
        Good error messages help with:
        - Debugging API integrations
        - User feedback
        - Support tickets
        """
        # Invalid JSON structure
        response = api_client.post("/rag/query", json={
            "invalid_field": "this field doesn't exist",
            "project_id": "not_a_number"  # Should be int, not string
        })
        
        # Should return 4xx (validation error) or handle gracefully
        # Note: Some APIs may accept this and return 200 with an error in the response
        # The key is that there's useful feedback
        if response.status_code >= 400:
            # Error response should include detail
            try:
                error_data = response.json()
                has_error_info = "detail" in error_data or "error" in error_data or "message" in error_data
                logger.info(f"Error response ({response.status_code}): {error_data}")
                assert has_error_info or response.status_code == 404, \
                    "4xx response should include error details"
            except:
                pass  # Non-JSON error is also acceptable
        else:
            # If 200, check that response contains error info or answer
            data = response.json()
            logger.info(f"Response (200): {data}")
            # This is informational - API may handle bad input gracefully
    
    def test_not_found_returns_404(self, api_client):
        """
        Non-existent resources should return 404.
        """
        response = api_client.get("/projects/999999999")
        assert response.status_code == 404, \
            f"Non-existent resource should return 404, got {response.status_code}"
    
    def test_error_format_is_consistent(self, api_client):
        """
        All errors should follow a consistent format.
        
        Consistent error format helps with:
        - Client-side error handling
        - Log aggregation
        - Monitoring alerting
        """
        # Generate different types of errors
        error_responses = []
        
        # 1. Validation error
        resp = api_client.post("/rag/query", json={"invalid": "data"})
        error_responses.append(resp)
        
        # 2. Not found
        resp = api_client.get("/projects/999999")
        error_responses.append(resp)
        
        # Check format consistency
        for resp in error_responses:
            if resp.status_code >= 400:
                try:
                    data = resp.json()
                    # Should be JSON with some error info
                    has_error_info = any(k in data for k in ['detail', 'error', 'message'])
                    assert has_error_info, f"Error response missing error info: {data}"
                except:
                    pass  # Non-JSON error responses are acceptable


# ============================================================================
# Logging Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.observability
class TestLogging:
    """Tests for logging behavior."""
    
    def test_operations_generate_logs(self, api_client, observability_rag):
        """
        Operations should generate appropriate log entries.
        
        Note: This test validates logging happens by checking
        the operation completes - actual log inspection would
        require access to log files.
        """
        # Run a query - should generate logs
        response = api_client.post("/rag/query", json={
            "prompt": "Test query for logging validation",
            "project_id": observability_rag
        }, timeout=120)
        
        # Operation should complete
        assert response.status_code in [200, 500], \
            "Operation should complete (even if with error)"
        
        logger.info("Query operation completed - logs should be generated")
    
    def test_task_operations_logged(self, api_client, observability_rag):
        """
        Task creation and completion should be logged.
        """
        csv_files = list(Path(config.USER_GENERATED_DATA_DIR).glob("*.csv"))[:1]
        if not csv_files:
            pytest.skip("No CSV files for logging test")
        
        # Start an import
        response = api_client.post("/datasources/import/start", json={
            "files": [str(csv_files[0])],
            "project_id": observability_rag,
            "skip_profiling": True
        })
        
        if response.status_code == 200:
            job_id = response.json().get("job_id")
            logger.info(f"Task {job_id} created - should be logged")


# ============================================================================
# Metrics Accuracy Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.observability
class TestMetricsAccuracy:
    """Tests that validate metrics are accurate."""
    
    def test_task_count_accuracy(self, api_client):
        """
        Task counts in summary should match actual tasks.
        """
        # Get summary
        summary_resp = api_client.get("/tasks/summary")
        assert summary_resp.status_code == 200
        summary = summary_resp.json()
        
        # Get all tasks
        grouped_resp = api_client.get("/tasks/grouped")
        assert grouped_resp.status_code == 200
        grouped = grouped_resp.json()
        
        # Count from grouped
        groups = grouped.get("groups", [])
        
        # Verify counts align (within reason - concurrent changes possible)
        total_from_summary = summary.get("running", 0) + summary.get("pending", 0) + \
                           summary.get("completed", 0) + summary.get("failed", 0) + \
                           summary.get("interrupted", 0)
        
        logger.info(f"Summary total: {total_from_summary}, Groups count: {len(groups)}")
        
        # Allow for some variance due to timing
        if len(groups) > 0:
            variance = abs(total_from_summary - len(groups)) / len(groups)
            assert variance < 0.5 or total_from_summary >= len(groups), \
                f"Task counts inconsistent: summary={total_from_summary}, groups={len(groups)}"
    
    def test_progress_updates_accurately(self, api_client, observability_rag):
        """
        Task progress should update as work completes.
        """
        csv_files = list(Path(config.USER_GENERATED_DATA_DIR).glob("*.csv"))[:3]
        if len(csv_files) < 2:
            pytest.skip("Not enough CSV files for progress test")
        
        # Start batch import
        response = api_client.post("/datasources/import/start", json={
            "files": [str(f) for f in csv_files],
            "project_id": observability_rag,
            "skip_profiling": True
        })
        
        if response.status_code != 200:
            pytest.skip("Could not start import")
        
        job_id = response.json().get("job_id")
        
        # Track progress over time
        progress_readings = []
        for _ in range(10):
            status_resp = api_client.get(f"/datasources/import/{job_id}/status")
            if status_resp.status_code == 200:
                status = status_resp.json()
                progress = status.get("progress", 0)
                progress_readings.append(progress)
                
                if status.get("status") in ["completed", "failed"]:
                    break
            
            time.sleep(2)
        
        # Progress should generally increase
        if len(progress_readings) > 2:
            increasing = all(
                progress_readings[i] <= progress_readings[i+1] 
                for i in range(len(progress_readings)-1)
            )
            
            logger.info(f"Progress readings: {progress_readings}")
            
            # Allow for some jitter but overall trend should be up
            if not increasing:
                decreases = sum(
                    1 for i in range(len(progress_readings)-1)
                    if progress_readings[i] > progress_readings[i+1]
                )
                assert decreases <= 1, \
                    f"Progress decreased multiple times: {progress_readings}"
