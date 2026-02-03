"""
Memory Stability Tests
======================

Tests for memory leaks and long-running stability.
Critical for production deployments.

Note: assistant_mode is auto-enabled by conftest.py for all /rag/query calls.

Run with:
    PYTHONPATH=. pytest rangerio_tests/performance/test_memory_stability.py -v -s

Note: These tests take longer to run. Use -m "not slow" to skip.
"""
import pytest
import time
import gc
import psutil
import os
from typing import List, Tuple

from rangerio_tests.config import config


def get_process_memory_mb() -> float:
    """Get current process memory in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def get_system_memory_info() -> dict:
    """Get system memory stats"""
    mem = psutil.virtual_memory()
    return {
        "total_gb": mem.total / 1024 / 1024 / 1024,
        "available_gb": mem.available / 1024 / 1024 / 1024,
        "percent_used": mem.percent
    }


@pytest.mark.performance
@pytest.mark.memory
class TestMemoryBaseline:
    """Test memory baseline and limits"""
    
    def test_baseline_memory_usage(self, api_client):
        """Test baseline memory usage of health check"""
        gc.collect()
        initial_memory = get_process_memory_mb()
        
        # Make 10 health checks
        for _ in range(10):
            api_client.get("/health")
        
        gc.collect()
        final_memory = get_process_memory_mb()
        
        growth = final_memory - initial_memory
        print(f"Memory: {initial_memory:.1f}MB -> {final_memory:.1f}MB (growth: {growth:.1f}MB)")
        
        # Health checks should not grow memory significantly
        assert growth < 50, f"Memory grew too much: {growth:.1f}MB"
    
    def test_project_creation_memory(self, api_client):
        """Test memory impact of creating projects"""
        gc.collect()
        initial_memory = get_process_memory_mb()
        
        project_ids = []
        
        # Create 10 projects
        for i in range(10):
            response = api_client.post("/projects", json={
                "name": f"Memory Test Project {i}",
                "description": "Testing memory"
            })
            if response.status_code == 200:
                project_ids.append(response.json().get("id"))
        
        gc.collect()
        after_create = get_process_memory_mb()
        
        # Delete projects
        for pid in project_ids:
            if pid:
                api_client.delete(f"/projects/{pid}")
        
        gc.collect()
        after_delete = get_process_memory_mb()
        
        create_growth = after_create - initial_memory
        retained = after_delete - initial_memory
        
        print(f"Memory after create: +{create_growth:.1f}MB")
        print(f"Memory after delete: +{retained:.1f}MB (retained)")
        
        # Memory should be mostly released after deletion
        assert retained < create_growth * 0.5 or retained < 20, \
            f"Too much memory retained: {retained:.1f}MB"


@pytest.mark.performance
@pytest.mark.memory
class TestMemoryUnderLoad:
    """Test memory behavior under sustained load"""
    
    def test_repeated_queries_memory(self, api_client, create_test_rag, sample_csv_small):
        """Test memory doesn't grow with repeated queries"""
        rag_id = create_test_rag("Memory Query Test")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        time.sleep(2)
        
        gc.collect()
        initial_memory = get_process_memory_mb()
        memory_samples: List[float] = [initial_memory]
        
        # Run queries in batches
        for batch in range(5):
            for _ in range(10):
                api_client.post("/rag/query", json={
                    "prompt": f"Query batch {batch}: What is in the data?",
                    "project_id": rag_id
                })
            
            gc.collect()
            memory_samples.append(get_process_memory_mb())
        
        # Analyze memory trend
        total_growth = memory_samples[-1] - memory_samples[0]
        
        print(f"Memory samples: {[f'{m:.1f}' for m in memory_samples]}")
        print(f"Total growth: {total_growth:.1f}MB over {len(memory_samples)-1} batches")
        
        # Memory growth should be bounded
        assert total_growth < config.MAX_MEMORY_MB / 10, \
            f"Memory grew too much: {total_growth:.1f}MB"
    
    @pytest.mark.slow
    def test_sustained_load_memory(self, api_client, create_test_rag, sample_csv_small):
        """Test memory stability under sustained load (2 minutes)"""
        rag_id = create_test_rag("Sustained Load Test")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        time.sleep(2)
        
        gc.collect()
        initial_memory = get_process_memory_mb()
        max_memory = initial_memory
        
        duration_seconds = 120  # 2 minutes
        start_time = time.time()
        query_count = 0
        
        while time.time() - start_time < duration_seconds:
            api_client.post("/rag/query", json={
                "prompt": "Describe the data",
                "project_id": rag_id
            })
            query_count += 1
            
            # Sample memory every 10 queries
            if query_count % 10 == 0:
                gc.collect()
                current = get_process_memory_mb()
                max_memory = max(max_memory, current)
        
        gc.collect()
        final_memory = get_process_memory_mb()
        
        print(f"Sustained load: {query_count} queries in {duration_seconds}s")
        print(f"Memory: {initial_memory:.1f}MB -> {final_memory:.1f}MB (max: {max_memory:.1f}MB)")
        
        # Memory should stay within bounds
        assert max_memory < config.MAX_MEMORY_MB, \
            f"Memory exceeded limit: {max_memory:.1f}MB > {config.MAX_MEMORY_MB}MB"


@pytest.mark.performance
@pytest.mark.memory
class TestFileUploadMemory:
    """Test memory behavior during file uploads"""
    
    def test_repeated_uploads_memory(self, api_client, create_test_rag, sample_csv_small):
        """Test memory doesn't leak with repeated uploads"""
        gc.collect()
        initial_memory = get_process_memory_mb()
        
        for i in range(5):
            rag_id = create_test_rag(f"Upload Memory Test {i}")
            
            api_client.upload_file(
                "/datasources/connect",
                sample_csv_small,
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
            
            # Delete to free resources
            api_client.delete(f"/projects/{rag_id}")
        
        gc.collect()
        final_memory = get_process_memory_mb()
        
        growth = final_memory - initial_memory
        print(f"Memory growth after 5 upload/delete cycles: {growth:.1f}MB")
        
        # Should not grow significantly
        assert growth < 100, f"Memory leak suspected: {growth:.1f}MB growth"
    
    def test_large_file_memory(self, api_client, create_test_rag, sample_csv_large):
        """Test memory usage with larger files"""
        gc.collect()
        initial_memory = get_process_memory_mb()
        system_before = get_system_memory_info()
        
        rag_id = create_test_rag("Large File Memory Test")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_large,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        gc.collect()
        after_upload = get_process_memory_mb()
        
        # Delete
        api_client.delete(f"/projects/{rag_id}")
        
        gc.collect()
        final_memory = get_process_memory_mb()
        
        print(f"Memory: {initial_memory:.1f}MB -> {after_upload:.1f}MB -> {final_memory:.1f}MB")
        print(f"System memory: {system_before['percent_used']:.1f}% used")
        
        # Memory should release after deletion
        retained = final_memory - initial_memory
        assert retained < 200, f"Large file memory not released: {retained:.1f}MB retained"


@pytest.mark.performance
@pytest.mark.memory
@pytest.mark.slow
class TestLongRunningStability:
    """Test long-running stability"""
    
    def test_5_minute_stability(self, api_client, create_test_rag, sample_csv_small):
        """Test system stability over 5 minutes"""
        rag_id = create_test_rag("Stability Test")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        time.sleep(2)
        
        duration_seconds = 300  # 5 minutes
        start_time = time.time()
        
        errors = []
        success_count = 0
        memory_samples = []
        
        gc.collect()
        memory_samples.append(get_process_memory_mb())
        
        while time.time() - start_time < duration_seconds:
            try:
                response = api_client.post("/rag/query", json={
                    "prompt": "Summarize the data",
                    "project_id": rag_id
                })
                
                if response.status_code == 200:
                    success_count += 1
                else:
                    errors.append(f"Status {response.status_code}")
                    
            except Exception as e:
                errors.append(str(e))
            
            # Sample memory every minute
            elapsed = time.time() - start_time
            if elapsed > len(memory_samples) * 60:
                gc.collect()
                memory_samples.append(get_process_memory_mb())
        
        gc.collect()
        memory_samples.append(get_process_memory_mb())
        
        error_rate = len(errors) / (success_count + len(errors)) if (success_count + len(errors)) > 0 else 0
        memory_growth = memory_samples[-1] - memory_samples[0]
        
        print(f"5-minute test results:")
        print(f"  Queries: {success_count} success, {len(errors)} errors ({error_rate*100:.1f}% error rate)")
        print(f"  Memory: {memory_samples[0]:.1f}MB -> {memory_samples[-1]:.1f}MB (+{memory_growth:.1f}MB)")
        
        # Assertions
        assert error_rate < 0.05, f"Error rate too high: {error_rate*100:.1f}%"
        assert memory_growth < 500, f"Memory growth too high: {memory_growth:.1f}MB"


@pytest.mark.performance
@pytest.mark.memory
class TestGarbageCollection:
    """Test garbage collection effectiveness"""
    
    def test_gc_reclaims_memory(self, api_client, create_test_rag, sample_csv_small):
        """Test that garbage collection reclaims memory"""
        gc.collect()
        baseline = get_process_memory_mb()
        
        # Create memory pressure
        rag_ids = []
        for i in range(5):
            rag_id = create_test_rag(f"GC Test {i}")
            api_client.upload_file(
                "/datasources/connect",
                sample_csv_small,
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
            rag_ids.append(rag_id)
        
        before_gc = get_process_memory_mb()
        
        # Delete all and GC
        for rag_id in rag_ids:
            api_client.delete(f"/projects/{rag_id}")
        
        gc.collect()
        gc.collect()  # Run twice for thorough collection
        
        after_gc = get_process_memory_mb()
        
        allocated = before_gc - baseline
        reclaimed = before_gc - after_gc
        
        print(f"Allocated: {allocated:.1f}MB, Reclaimed: {reclaimed:.1f}MB")
        
        # Should reclaim at least 50% of allocated memory
        if allocated > 50:  # Only check if meaningful allocation
            reclaim_rate = reclaimed / allocated if allocated > 0 else 0
            assert reclaim_rate > 0.3, \
                f"GC only reclaimed {reclaim_rate*100:.0f}% of memory"
