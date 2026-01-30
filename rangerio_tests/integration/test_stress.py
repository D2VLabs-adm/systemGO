"""
Stress Tests for RangerIO

These tests push the system to its limits to identify:
- Scalability bottlenecks
- Failure modes under load
- Resource exhaustion points
- Concurrency issues

These tests are intentionally aggressive - failures indicate
real issues that need architectural improvements.
"""
import pytest
import time
import threading
import queue
from pathlib import Path
from typing import Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import statistics

from rangerio_tests.config import config, logger


# ============================================================================
# Stress Test Baselines
# ============================================================================

# Concurrent user simulation
MIN_CONCURRENT_SUCCESS_RATE = 0.70  # At least 70% should succeed under load
MAX_CONCURRENT_USERS = 10  # Test up to 10 concurrent users

# Batch processing
MAX_BATCH_FILES = 20  # Test batch import with 20 files
BATCH_TIMEOUT_S = 600  # 10 minutes for large batch

# Sustained load
SUSTAINED_LOAD_DURATION_S = 120  # 2 minutes of sustained load
MIN_SUSTAINED_SUCCESS_RATE = 0.80  # 80% success during sustained load

# Recovery
MAX_RECOVERY_TIME_S = 30  # Should recover within 30 seconds

# Ingestion wait
RAG_INGESTION_WAIT = 45


@dataclass
class StressResult:
    """Results from a stress test operation."""
    operation: str
    total_requests: int
    successful: int
    failed: int
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    errors: List[str]
    
    @property
    def success_rate(self) -> float:
        return self.successful / self.total_requests if self.total_requests > 0 else 0


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def stress_rag(api_client, financial_sample):
    """Create a RAG with data for stress testing."""
    import uuid
    response = api_client.post("/projects", json={
        "name": f"Stress Test RAG_{uuid.uuid4().hex[:8]}",
        "description": "RAG for stress testing"
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
    
    logger.info(f"Created stress test RAG: {rag_id}")
    yield rag_id
    
    try:
        api_client.delete(f"/projects/{rag_id}")
    except Exception as e:
        logger.warning(f"Failed to cleanup RAG {rag_id}: {e}")


# ============================================================================
# Concurrent User Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.stress
class TestConcurrentUsers:
    """Tests that simulate multiple concurrent users."""
    
    def test_concurrent_query_requests(self, api_client, stress_rag):
        """
        Simulate multiple users querying simultaneously.
        
        At least 70% of concurrent requests should succeed.
        Failures indicate:
        - LLM request queuing issues
        - Database connection exhaustion
        - Thread safety problems
        """
        concurrent_users = MAX_CONCURRENT_USERS
        results_queue = queue.Queue()
        
        def make_query(user_id: int) -> Tuple[int, float, str]:
            """Make a query and return (status_code, response_time, error)."""
            start = time.time()
            try:
                response = api_client.post("/rag/query", json={
                    "prompt": f"User {user_id}: What is the total sales?",
                    "project_id": stress_rag
                }, timeout=180)
                elapsed = time.time() - start
                return (response.status_code, elapsed, "")
            except Exception as e:
                elapsed = time.time() - start
                return (0, elapsed, str(e))
        
        # Run concurrent requests
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_query, i) for i in range(concurrent_users)]
            
            for future in as_completed(futures):
                results_queue.put(future.result())
        
        # Analyze results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        successful = sum(1 for r in results if r[0] == 200)
        failed = len(results) - successful
        response_times = [r[1] for r in results if r[0] == 200]
        errors = [r[2] for r in results if r[2]]
        
        success_rate = successful / len(results)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"CONCURRENT USERS TEST ({concurrent_users} users)")
        logger.info(f"{'='*60}")
        logger.info(f"  Success rate: {success_rate*100:.1f}% (min: {MIN_CONCURRENT_SUCCESS_RATE*100:.0f}%)")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        if response_times:
            logger.info(f"  Avg response time: {statistics.mean(response_times):.2f}s")
            logger.info(f"  Max response time: {max(response_times):.2f}s")
        if errors:
            logger.info(f"  Errors: {errors[:3]}")  # First 3 errors
        logger.info(f"{'='*60}\n")
        
        assert success_rate >= MIN_CONCURRENT_SUCCESS_RATE, \
            f"Concurrent success rate too low: {success_rate*100:.1f}% < {MIN_CONCURRENT_SUCCESS_RATE*100:.0f}%"
    
    def test_concurrent_mixed_operations(self, api_client, stress_rag):
        """
        Simulate mixed operations (queries, health checks, task status).
        
        Tests that different endpoints can handle concurrent access.
        """
        operations = [
            ("query", lambda: api_client.post("/rag/query", json={
                "prompt": "What are the sales figures?",
                "project_id": stress_rag
            }, timeout=180)),
            ("health", lambda: api_client.get("/health")),
            ("tasks", lambda: api_client.get("/tasks/summary")),
            ("projects", lambda: api_client.get("/projects")),
        ]
        
        results = []
        
        def run_operation(op_name: str, op_func):
            start = time.time()
            try:
                response = op_func()
                return (op_name, response.status_code, time.time() - start, "")
            except Exception as e:
                return (op_name, 0, time.time() - start, str(e))
        
        # Run all operations concurrently, twice
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for _ in range(2):
                for op_name, op_func in operations:
                    futures.append(executor.submit(run_operation, op_name, op_func))
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze by operation type
        by_operation = {}
        for op_name, status, elapsed, error in results:
            if op_name not in by_operation:
                by_operation[op_name] = {'success': 0, 'fail': 0, 'times': []}
            if status == 200:
                by_operation[op_name]['success'] += 1
                by_operation[op_name]['times'].append(elapsed)
            else:
                by_operation[op_name]['fail'] += 1
        
        logger.info("\nMixed operations results:")
        for op_name, stats in by_operation.items():
            total = stats['success'] + stats['fail']
            rate = stats['success'] / total if total > 0 else 0
            avg_time = statistics.mean(stats['times']) if stats['times'] else 0
            logger.info(f"  {op_name}: {rate*100:.0f}% success, avg {avg_time:.2f}s")
        
        # All non-query operations should have 100% success
        for op_name in ['health', 'tasks', 'projects']:
            if op_name in by_operation:
                stats = by_operation[op_name]
                total = stats['success'] + stats['fail']
                rate = stats['success'] / total if total > 0 else 0
                assert rate >= 0.9, f"{op_name} endpoint failed under concurrent load"
    
    def test_scaling_concurrent_users(self, api_client, stress_rag):
        """
        Test how success rate degrades as concurrent users increase.
        
        This helps identify the system's capacity limits.
        """
        scaling_results = []
        
        for num_users in [2, 5, 8, 10]:
            results = []
            
            def query(user_id):
                try:
                    response = api_client.post("/rag/query", json={
                        "prompt": f"User {user_id}: summarize",
                        "project_id": stress_rag
                    }, timeout=180)
                    return response.status_code == 200
                except:
                    return False
            
            with ThreadPoolExecutor(max_workers=num_users) as executor:
                futures = [executor.submit(query, i) for i in range(num_users)]
                results = [f.result() for f in as_completed(futures)]
            
            success_rate = sum(results) / len(results)
            scaling_results.append((num_users, success_rate))
            
            logger.info(f"  {num_users} users: {success_rate*100:.0f}% success")
        
        logger.info("\n📊 Scaling analysis:")
        for users, rate in scaling_results:
            bar = "█" * int(rate * 20)
            logger.info(f"  {users:2d} users: {bar} {rate*100:.0f}%")
        
        # Success rate should not drop below 50% even at max users
        final_rate = scaling_results[-1][1]
        assert final_rate >= 0.50, \
            f"System degrades too much under load: {final_rate*100:.0f}% at {MAX_CONCURRENT_USERS} users"


# ============================================================================
# Batch Processing Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.stress
class TestBatchProcessing:
    """Tests for large batch operations."""
    
    def test_large_batch_import(self, api_client):
        """
        Import a large batch of files.
        
        Tests:
        - Task queue capacity
        - Memory management
        - Progress tracking accuracy
        """
        # Find available files
        csv_files = list(Path(config.USER_GENERATED_DATA_DIR).glob("*.csv"))[:MAX_BATCH_FILES]
        if len(csv_files) < 5:
            pytest.skip(f"Not enough CSV files for batch test (found {len(csv_files)})")
        
        # Create test RAG
        response = api_client.post("/projects", json={
            "name": f"Batch Stress Test_{uuid.uuid4().hex[:8]}",
            "description": "Large batch import test"
        })
        assert response.status_code == 200
        rag_id = response.json()["id"]
        
        try:
            # Start batch import
            start_time = time.time()
            response = api_client.post("/datasources/import/start", json={
                "files": [str(f) for f in csv_files],
                "project_id": rag_id,
                "skip_profiling": True
            })
            assert response.status_code == 200, f"Batch import failed to start: {response.text}"
            
            job_id = response.json()["job_id"]
            logger.info(f"Started batch import of {len(csv_files)} files, job: {job_id}")
            
            # Monitor progress
            progress_history = []
            while time.time() - start_time < BATCH_TIMEOUT_S:
                status_resp = api_client.get(f"/datasources/import/{job_id}/status")
                if status_resp.status_code != 200:
                    logger.warning(f"Status check failed: {status_resp.status_code}")
                    break
                
                status = status_resp.json()
                progress = status.get("progress", 0)
                progress_history.append(progress)
                
                if status.get("status") == "completed":
                    logger.info("Batch import completed")
                    break
                elif status.get("status") == "failed":
                    logger.error(f"Batch import failed: {status.get('error')}")
                    break
                
                time.sleep(5)
            
            elapsed = time.time() - start_time
            files_per_minute = (len(csv_files) / elapsed) * 60 if elapsed > 0 else 0
            
            logger.info(f"\n{'='*60}")
            logger.info(f"BATCH IMPORT RESULTS ({len(csv_files)} files)")
            logger.info(f"{'='*60}")
            logger.info(f"  Duration: {elapsed:.1f}s")
            logger.info(f"  Rate: {files_per_minute:.1f} files/min")
            logger.info(f"  Final status: {status.get('status')}")
            logger.info(f"{'='*60}\n")
            
            assert status.get("status") == "completed", \
                f"Batch import did not complete: {status.get('status')}"
            assert elapsed < BATCH_TIMEOUT_S, \
                f"Batch import too slow: {elapsed:.1f}s > {BATCH_TIMEOUT_S}s"
        
        finally:
            api_client.delete(f"/projects/{rag_id}")
    
    def test_batch_import_cancellation(self, api_client):
        """
        Test that batch imports can be cancelled.
        
        Important for user control and resource management.
        """
        csv_files = list(Path(config.USER_GENERATED_DATA_DIR).glob("*.csv"))[:10]
        if len(csv_files) < 5:
            pytest.skip("Not enough files for cancellation test")
        
        # Create test RAG
        response = api_client.post("/projects", json={
            "name": f"Cancellation Test_{uuid.uuid4().hex[:8]}",
            "description": "Testing import cancellation"
        })
        assert response.status_code == 200
        rag_id = response.json()["id"]
        
        try:
            # Start import
            response = api_client.post("/datasources/import/start", json={
                "files": [str(f) for f in csv_files],
                "project_id": rag_id,
                "skip_profiling": False  # Include profiling to make it slower
            })
            assert response.status_code == 200
            job_id = response.json()["job_id"]
            
            # Wait a moment then cancel
            time.sleep(3)
            
            # Find the task and cancel it
            tasks_resp = api_client.get("/tasks/active")
            if tasks_resp.status_code == 200:
                active = tasks_resp.json()
                if isinstance(active, dict):
                    active = active.get('tasks', [])
                
                for task in active:
                    if 'import' in task.get('type', '').lower():
                        cancel_resp = api_client.post(f"/tasks/{task['id']}/cancel")
                        logger.info(f"Cancel response: {cancel_resp.status_code}")
                        break
            
            # Verify cancellation or completion
            time.sleep(2)
            status_resp = api_client.get(f"/datasources/import/{job_id}/status")
            if status_resp.status_code == 200:
                status = status_resp.json()
                # Accept cancelled, completed, or interrupted as valid outcomes
                assert status.get("status") in ["cancelled", "completed", "interrupted", "failed"], \
                    f"Unexpected status after cancel: {status.get('status')}"
        
        finally:
            api_client.delete(f"/projects/{rag_id}")


# ============================================================================
# Sustained Load Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.stress
class TestSustainedLoad:
    """Tests for sustained load over time."""
    
    def test_sustained_query_load(self, api_client, stress_rag):
        """
        Run continuous queries for 2 minutes.
        
        Tests:
        - Memory stability over time
        - Error rate under sustained load
        - Response time consistency
        """
        start_time = time.time()
        results = []
        
        logger.info(f"Starting sustained load test ({SUSTAINED_LOAD_DURATION_S}s)")
        
        while time.time() - start_time < SUSTAINED_LOAD_DURATION_S:
            query_start = time.time()
            try:
                response = api_client.post("/rag/query", json={
                    "prompt": "Summarize the financial data briefly",
                    "project_id": stress_rag
                }, timeout=120)
                
                results.append({
                    'success': response.status_code == 200,
                    'time': time.time() - query_start,
                    'elapsed': time.time() - start_time
                })
            except Exception as e:
                results.append({
                    'success': False,
                    'time': time.time() - query_start,
                    'elapsed': time.time() - start_time,
                    'error': str(e)
                })
        
        # Analyze results
        total = len(results)
        successful = sum(1 for r in results if r['success'])
        success_rate = successful / total if total > 0 else 0
        
        response_times = [r['time'] for r in results if r['success']]
        
        # Check for degradation over time
        first_half = [r for r in results if r['elapsed'] < SUSTAINED_LOAD_DURATION_S / 2]
        second_half = [r for r in results if r['elapsed'] >= SUSTAINED_LOAD_DURATION_S / 2]
        
        first_half_success = sum(1 for r in first_half if r['success']) / len(first_half) if first_half else 0
        second_half_success = sum(1 for r in second_half if r['success']) / len(second_half) if second_half else 0
        
        logger.info(f"\n{'='*60}")
        logger.info(f"SUSTAINED LOAD TEST ({SUSTAINED_LOAD_DURATION_S}s)")
        logger.info(f"{'='*60}")
        logger.info(f"  Total queries: {total}")
        logger.info(f"  Overall success rate: {success_rate*100:.1f}%")
        logger.info(f"  First half success: {first_half_success*100:.1f}%")
        logger.info(f"  Second half success: {second_half_success*100:.1f}%")
        if response_times:
            logger.info(f"  Avg response time: {statistics.mean(response_times):.2f}s")
            logger.info(f"  Response time std dev: {statistics.stdev(response_times) if len(response_times) > 1 else 0:.2f}s")
        logger.info(f"{'='*60}\n")
        
        # Assertions
        assert success_rate >= MIN_SUSTAINED_SUCCESS_RATE, \
            f"Sustained load success rate too low: {success_rate*100:.1f}%"
        
        # Check for degradation (second half shouldn't be significantly worse)
        if first_half_success > 0:
            degradation = first_half_success - second_half_success
            assert degradation < 0.2, \
                f"Significant degradation over time: {degradation*100:.1f}% drop"


# ============================================================================
# Recovery Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.stress
class TestRecovery:
    """Tests for system recovery after stress."""
    
    def test_recovery_after_load(self, api_client, stress_rag):
        """
        System should recover quickly after heavy load.
        
        Tests that resources are properly released.
        """
        # Generate some load
        logger.info("Generating load...")
        for _ in range(5):
            try:
                api_client.post("/rag/query", json={
                    "prompt": "Heavy query to stress system",
                    "project_id": stress_rag
                }, timeout=120)
            except:
                pass
        
        # Wait a moment
        time.sleep(5)
        
        # Test recovery with a simple request
        start = time.time()
        response = api_client.get("/health")
        recovery_time = time.time() - start
        
        logger.info(f"Recovery test - health endpoint response in {recovery_time*1000:.0f}ms")
        
        assert response.status_code == 200, "Health check failed after load"
        assert recovery_time < 1.0, f"Health check too slow after load: {recovery_time:.2f}s"
        
        # Verify a query works
        start = time.time()
        response = api_client.post("/rag/query", json={
            "prompt": "Simple test query",
            "project_id": stress_rag
        }, timeout=120)
        query_time = time.time() - start
        
        logger.info(f"Post-recovery query completed in {query_time:.2f}s")
        
        assert response.status_code == 200, "Query failed after recovery"
    
    def test_error_handling_under_stress(self, api_client):
        """
        System should handle errors gracefully under stress.
        
        Invalid requests shouldn't crash the system.
        """
        # Send a burst of invalid requests
        errors_handled = 0
        crashes = 0
        
        for _ in range(10):
            try:
                # Invalid project ID
                response = api_client.post("/rag/query", json={
                    "prompt": "Test",
                    "project_id": 999999
                }, timeout=30)
                
                if response.status_code in [400, 404, 422]:
                    errors_handled += 1
                elif response.status_code >= 500:
                    crashes += 1
            except:
                crashes += 1
        
        logger.info(f"Error handling: {errors_handled}/10 handled gracefully, {crashes} crashes")
        
        # System should still be responsive
        health_response = api_client.get("/health")
        assert health_response.status_code == 200, "System unresponsive after error burst"
        
        # Most errors should be handled gracefully (4xx not 5xx)
        assert errors_handled >= 7, \
            f"Too many crashes under stress: {crashes}/10"


# ============================================================================
# Resource Limit Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.stress
class TestResourceLimits:
    """Tests that verify resource limits are enforced."""
    
    def test_query_timeout_enforcement(self, api_client, stress_rag):
        """
        Very long queries should timeout gracefully.
        """
        # Send a query that might take a long time
        start = time.time()
        try:
            response = api_client.post("/rag/query", json={
                "prompt": "Provide an extremely detailed, comprehensive, "
                         "exhaustive analysis of every single data point, "
                         "relationship, trend, pattern, anomaly, and insight "
                         "in the entire dataset with full explanations",
                "project_id": stress_rag
            }, timeout=180)  # 3 minute timeout
            
            elapsed = time.time() - start
            logger.info(f"Long query completed in {elapsed:.2f}s")
            
            # Should either complete or return gracefully
            assert response.status_code in [200, 408, 504], \
                f"Unexpected status for long query: {response.status_code}"
        
        except Exception as e:
            elapsed = time.time() - start
            logger.info(f"Long query timed out after {elapsed:.2f}s: {e}")
            # Timeout is acceptable
            assert elapsed >= 60, "Query timed out too quickly"
    
    def test_request_size_limits(self, api_client, stress_rag):
        """
        System should handle large request payloads gracefully.
        """
        # Very long prompt
        long_prompt = "What is the total sales? " * 1000  # ~25KB prompt
        
        response = api_client.post("/rag/query", json={
            "prompt": long_prompt,
            "project_id": stress_rag
        }, timeout=60)
        
        # Should either handle or reject gracefully
        assert response.status_code in [200, 400, 413, 422], \
            f"Unexpected response to large payload: {response.status_code}"
        
        if response.status_code != 200:
            logger.info(f"Large payload rejected with {response.status_code} (expected)")
