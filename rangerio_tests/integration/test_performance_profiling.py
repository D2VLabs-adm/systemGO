"""
Performance Profiling Tests for RangerIO

These tests measure and enforce performance baselines to catch regressions
and identify optimization opportunities. They are NOT lenient - failures
indicate real issues that need to be addressed in the application.

Test Categories:
- Memory profiling during operations
- Response time percentiles (P50, P95, P99)
- Throughput measurements
- Resource utilization tracking
"""
import pytest
import time
import psutil
import statistics
from pathlib import Path
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime

from rangerio_tests.config import config, logger


# ============================================================================
# Constants - Strict Performance Baselines
# ============================================================================

# Response Time Baselines (seconds)
QUERY_P50_MAX = 15.0  # 50th percentile should be under 15s
QUERY_P95_MAX = 45.0  # 95th percentile should be under 45s
QUERY_P99_MAX = 90.0  # 99th percentile should be under 90s

# Memory Baselines (MB)
BASELINE_MEMORY_MAX = 1500  # Max baseline memory usage
IMPORT_MEMORY_SPIKE_MAX = 2000  # Max memory spike during import
QUERY_MEMORY_SPIKE_MAX = 500  # Max memory increase per query batch

# Throughput Baselines
MIN_QUERIES_PER_MINUTE = 5  # Minimum queries per minute
MIN_IMPORTS_PER_MINUTE = 10  # Minimum file imports per minute (small files)

# Import Performance
SMALL_FILE_IMPORT_MAX_S = 10  # Max seconds for <1MB file import
LARGE_FILE_IMPORT_MAX_S = 60  # Max seconds for 10-50MB file import

# Ingestion wait
RAG_INGESTION_WAIT = 45  # seconds to wait for RAG indexing


@dataclass
class PerformanceMetrics:
    """Container for performance measurement results."""
    operation: str
    start_time: datetime
    end_time: datetime
    duration_s: float
    memory_start_mb: float
    memory_end_mb: float
    memory_peak_mb: float
    success: bool
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'operation': self.operation,
            'duration_s': self.duration_s,
            'memory_delta_mb': self.memory_end_mb - self.memory_start_mb,
            'memory_peak_mb': self.memory_peak_mb,
            'success': self.success,
            'details': self.details or {}
        }


class PerformanceProfiler:
    """Utility class for performance profiling."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.metrics: List[PerformanceMetrics] = []
        
    def measure(self, operation: str):
        """Context manager for measuring an operation."""
        return PerformanceMeasurement(self, operation)
    
    def get_memory_mb(self) -> float:
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / (1024 * 1024)
    
    def get_cpu_percent(self) -> float:
        """Get current CPU usage percentage."""
        return self.process.cpu_percent(interval=0.1)
    
    def record_metric(self, metric: PerformanceMetrics):
        """Record a performance metric."""
        self.metrics.append(metric)
        logger.info(f"[PERF] {metric.operation}: {metric.duration_s:.2f}s, "
                   f"Memory: {metric.memory_start_mb:.0f}MB -> {metric.memory_end_mb:.0f}MB")
    
    def calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """Calculate P50, P95, P99 percentiles."""
        if not values:
            return {'p50': 0, 'p95': 0, 'p99': 0}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        return {
            'p50': sorted_values[int(n * 0.50)] if n > 1 else sorted_values[0],
            'p95': sorted_values[int(n * 0.95)] if n > 19 else sorted_values[-1],
            'p99': sorted_values[int(n * 0.99)] if n > 99 else sorted_values[-1],
            'min': sorted_values[0],
            'max': sorted_values[-1],
            'mean': statistics.mean(sorted_values),
            'stdev': statistics.stdev(sorted_values) if n > 1 else 0
        }


class PerformanceMeasurement:
    """Context manager for individual performance measurements."""
    
    def __init__(self, profiler: PerformanceProfiler, operation: str):
        self.profiler = profiler
        self.operation = operation
        self.start_time = None
        self.start_memory = None
        self.peak_memory = None
        self.success = True
        self.details = {}
        
    def __enter__(self):
        self.start_time = datetime.now()
        self.start_memory = self.profiler.get_memory_mb()
        self.peak_memory = self.start_memory
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.now()
        end_memory = self.profiler.get_memory_mb()
        
        # Track peak memory
        current_memory = end_memory
        if current_memory > self.peak_memory:
            self.peak_memory = current_memory
        
        if exc_type is not None:
            self.success = False
        
        metric = PerformanceMetrics(
            operation=self.operation,
            start_time=self.start_time,
            end_time=end_time,
            duration_s=(end_time - self.start_time).total_seconds(),
            memory_start_mb=self.start_memory,
            memory_end_mb=end_memory,
            memory_peak_mb=self.peak_memory,
            success=self.success,
            details=self.details
        )
        
        self.profiler.record_metric(metric)
        return False  # Don't suppress exceptions


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def profiler():
    """Fresh performance profiler for each test."""
    return PerformanceProfiler()


@pytest.fixture
def profiling_rag(api_client, financial_sample):
    """Create a RAG with financial data for profiling tests."""
    import uuid
    response = api_client.post("/projects", json={
        "name": f"Performance Profiling RAG_{uuid.uuid4().hex[:8]}",
        "description": "RAG for performance baseline testing"
    })
    assert response.status_code == 200, f"Failed to create RAG: {response.text}"
    rag_id = response.json()["id"]
    
    # Import test data
    response = api_client.upload_file(
        "/datasources/connect",
        financial_sample,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    assert response.status_code == 200, f"Failed to import: {response.text}"
    
    # Wait for indexing
    logger.info(f"Waiting for RAG indexing ({RAG_INGESTION_WAIT}s)...")
    time.sleep(RAG_INGESTION_WAIT)
    
    logger.info(f"Created profiling RAG: {rag_id}")
    yield rag_id
    
    # Cleanup
    try:
        api_client.delete(f"/projects/{rag_id}")
    except Exception as e:
        logger.warning(f"Failed to cleanup RAG {rag_id}: {e}")


# ============================================================================
# Response Time Percentile Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.profiling
class TestResponseTimePercentiles:
    """Tests that measure and enforce response time percentiles."""
    
    def test_query_response_time_percentiles(self, api_client, profiling_rag, profiler):
        """
        P50 should be under 15s, P95 under 45s, P99 under 90s.
        
        This is a strict test - failures indicate the RAG system is too slow
        and needs optimization (better retrieval, faster LLM, caching).
        """
        queries = [
            "What is the total sales revenue?",
            "How many products are in the dataset?",
            "What are the main categories?",
            "Summarize the financial performance",
            "What is the profit margin?",
            "List the top selling products",
            "What is the average discount?",
            "Show monthly sales trends",
            "What are the key metrics?",
            "Describe the dataset",
            "What is the total profit?",
            "How many transactions are there?",
            "What is the highest sale?",
            "What is the lowest sale?",
            "What are the segments?",
            "Show country breakdown",
            "What is year over year growth?",
            "What is the manufacturing cost?",
            "What products have highest margin?",
            "What is the sales distribution?",
        ]
        
        response_times = []
        
        for query in queries:
            with profiler.measure(f"query: {query[:30]}..."):
                start = time.time()
                response = api_client.post("/rag/query", json={
                    "prompt": query,
                    "project_id": profiling_rag
                }, timeout=120)
                elapsed = time.time() - start
                response_times.append(elapsed)
                
                # Log individual results
                status = "✓" if response.status_code == 200 else "✗"
                logger.info(f"  {status} [{elapsed:.2f}s] {query[:40]}...")
        
        # Calculate percentiles
        percentiles = profiler.calculate_percentiles(response_times)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"RESPONSE TIME PERCENTILES ({len(response_times)} queries)")
        logger.info(f"{'='*60}")
        logger.info(f"  P50: {percentiles['p50']:.2f}s (max: {QUERY_P50_MAX}s)")
        logger.info(f"  P95: {percentiles['p95']:.2f}s (max: {QUERY_P95_MAX}s)")
        logger.info(f"  P99: {percentiles['p99']:.2f}s (max: {QUERY_P99_MAX}s)")
        logger.info(f"  Min: {percentiles['min']:.2f}s")
        logger.info(f"  Max: {percentiles['max']:.2f}s")
        logger.info(f"  Mean: {percentiles['mean']:.2f}s")
        logger.info(f"  StdDev: {percentiles['stdev']:.2f}s")
        logger.info(f"{'='*60}\n")
        
        # Strict assertions - these should fail if performance degrades
        assert percentiles['p50'] <= QUERY_P50_MAX, \
            f"P50 too slow: {percentiles['p50']:.2f}s > {QUERY_P50_MAX}s"
        assert percentiles['p95'] <= QUERY_P95_MAX, \
            f"P95 too slow: {percentiles['p95']:.2f}s > {QUERY_P95_MAX}s"
        assert percentiles['p99'] <= QUERY_P99_MAX, \
            f"P99 too slow: {percentiles['p99']:.2f}s > {QUERY_P99_MAX}s"
    
    def test_health_endpoint_latency(self, api_client, profiler):
        """Health endpoint should respond in under 100ms (P99)."""
        response_times = []
        
        for _ in range(50):
            start = time.time()
            response = api_client.get("/health")
            elapsed = time.time() - start
            response_times.append(elapsed * 1000)  # Convert to ms
            assert response.status_code == 200
        
        percentiles = profiler.calculate_percentiles(response_times)
        
        logger.info(f"Health endpoint latency - P50: {percentiles['p50']:.2f}ms, "
                   f"P99: {percentiles['p99']:.2f}ms")
        
        assert percentiles['p99'] < 100, \
            f"Health endpoint P99 latency too high: {percentiles['p99']:.2f}ms"


# ============================================================================
# Memory Profiling Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.profiling
class TestMemoryProfiling:
    """Tests that measure and enforce memory usage limits."""
    
    def test_baseline_memory_usage(self, api_client, profiler):
        """
        Baseline memory should not exceed 1.5GB.
        
        High baseline memory indicates:
        - Memory leaks from previous operations
        - Models loaded that should be unloaded
        - Excessive caching
        """
        # Make a simple request to ensure system is initialized
        api_client.get("/health")
        time.sleep(1)
        
        baseline_memory = profiler.get_memory_mb()
        logger.info(f"Baseline memory usage: {baseline_memory:.2f}MB (max: {BASELINE_MEMORY_MAX}MB)")
        
        assert baseline_memory < BASELINE_MEMORY_MAX, \
            f"Baseline memory too high: {baseline_memory:.2f}MB > {BASELINE_MEMORY_MAX}MB. " \
            f"Check for memory leaks or models that should be unloaded."
    
    def test_memory_during_import(self, api_client, financial_sample, profiler):
        """
        Memory during import should not spike more than 2GB above baseline.
        
        Excessive memory spike indicates:
        - File loaded entirely into memory instead of streaming
        - Inefficient data structures
        - Missing garbage collection
        """
        # Get baseline
        baseline_memory = profiler.get_memory_mb()
        
        # Create a test RAG for this import
        response = api_client.post("/projects", json={
            "name": f"Memory Test RAG_{uuid.uuid4().hex[:8]}",
            "description": "For memory profiling"
        })
        assert response.status_code == 200
        rag_id = response.json()["id"]
        
        try:
            # Measure memory during import
            with profiler.measure("file_import"):
                response = api_client.upload_file(
                    "/datasources/connect",
                    financial_sample,
                    data={'project_id': str(rag_id), 'source_type': 'file'}
                )
                assert response.status_code == 200
                
                # Check memory at multiple points
                peak_memory = baseline_memory
                for _ in range(10):
                    current = profiler.get_memory_mb()
                    if current > peak_memory:
                        peak_memory = current
                    time.sleep(0.5)
            
            memory_spike = peak_memory - baseline_memory
            logger.info(f"Memory spike during import: {memory_spike:.2f}MB "
                       f"(max: {IMPORT_MEMORY_SPIKE_MAX}MB)")
            
            assert memory_spike < IMPORT_MEMORY_SPIKE_MAX, \
                f"Memory spike during import too high: {memory_spike:.2f}MB > {IMPORT_MEMORY_SPIKE_MAX}MB"
        
        finally:
            api_client.delete(f"/projects/{rag_id}")
    
    def test_memory_after_query_batch(self, api_client, profiling_rag, profiler):
        """
        Memory should not grow significantly after a batch of queries.
        
        Growing memory indicates:
        - Queries not releasing resources
        - Response caching without limits
        - LLM context accumulation
        """
        # Get baseline after system is warmed up
        api_client.post("/rag/query", json={
            "prompt": "warmup query",
            "project_id": profiling_rag
        }, timeout=120)
        time.sleep(2)
        baseline_memory = profiler.get_memory_mb()
        
        # Run batch of queries
        for i in range(10):
            api_client.post("/rag/query", json={
                "prompt": f"Query {i}: What are the sales figures?",
                "project_id": profiling_rag
            }, timeout=120)
        
        # Check memory growth
        time.sleep(2)
        final_memory = profiler.get_memory_mb()
        memory_growth = final_memory - baseline_memory
        
        logger.info(f"Memory growth after 10 queries: {memory_growth:.2f}MB "
                   f"(max: {QUERY_MEMORY_SPIKE_MAX}MB)")
        
        assert memory_growth < QUERY_MEMORY_SPIKE_MAX, \
            f"Memory growth after queries too high: {memory_growth:.2f}MB. " \
            f"Check for memory leaks in query processing."


# ============================================================================
# Throughput Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.profiling
class TestThroughput:
    """Tests that measure system throughput."""
    
    def test_query_throughput(self, api_client, profiling_rag, profiler):
        """
        Should handle at least 5 queries per minute.
        
        Lower throughput indicates:
        - LLM bottleneck (model too slow)
        - No request queuing
        - Database contention
        """
        start_time = time.time()
        successful_queries = 0
        failed_queries = 0
        
        # Run queries for 60 seconds
        while time.time() - start_time < 60:
            response = api_client.post("/rag/query", json={
                "prompt": "What is the total revenue?",
                "project_id": profiling_rag
            }, timeout=120)
            
            if response.status_code == 200:
                successful_queries += 1
            else:
                failed_queries += 1
        
        qpm = successful_queries  # Queries per minute
        error_rate = failed_queries / (successful_queries + failed_queries) if (successful_queries + failed_queries) > 0 else 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"THROUGHPUT RESULTS (60 second window)")
        logger.info(f"{'='*60}")
        logger.info(f"  Queries per minute: {qpm} (min: {MIN_QUERIES_PER_MINUTE})")
        logger.info(f"  Successful: {successful_queries}")
        logger.info(f"  Failed: {failed_queries}")
        logger.info(f"  Error rate: {error_rate*100:.1f}%")
        logger.info(f"{'='*60}\n")
        
        assert qpm >= MIN_QUERIES_PER_MINUTE, \
            f"Query throughput too low: {qpm} qpm < {MIN_QUERIES_PER_MINUTE} qpm"
        assert error_rate < 0.1, \
            f"Error rate too high: {error_rate*100:.1f}% >= 10%"
    
    def test_import_throughput(self, api_client, user_test_files_dir, profiler):
        """
        Should handle at least 10 small file imports per minute.
        
        Lower throughput indicates:
        - File processing bottleneck
        - Database write contention
        - Task queue saturation
        """
        # Create test RAG
        response = api_client.post("/projects", json={
            "name": f"Import Throughput Test_{uuid.uuid4().hex[:8]}",
            "description": "For measuring import throughput"
        })
        assert response.status_code == 200
        rag_id = response.json()["id"]
        
        try:
            # Find small CSV files
            csv_files = list(Path(config.USER_GENERATED_DATA_DIR).glob("*.csv"))[:15]
            if len(csv_files) < 5:
                pytest.skip("Not enough CSV files for throughput test")
            
            start_time = time.time()
            successful_imports = 0
            
            # Import files for up to 60 seconds
            for csv_file in csv_files:
                if time.time() - start_time >= 60:
                    break
                
                response = api_client.upload_file(
                    "/datasources/connect",
                    csv_file,
                    data={'project_id': str(rag_id), 'source_type': 'file'}
                )
                if response.status_code == 200:
                    successful_imports += 1
            
            elapsed = time.time() - start_time
            imports_per_minute = (successful_imports / elapsed) * 60
            
            logger.info(f"Import throughput: {imports_per_minute:.1f} files/min "
                       f"(min: {MIN_IMPORTS_PER_MINUTE})")
            
            assert imports_per_minute >= MIN_IMPORTS_PER_MINUTE, \
                f"Import throughput too low: {imports_per_minute:.1f} < {MIN_IMPORTS_PER_MINUTE}/min"
        
        finally:
            api_client.delete(f"/projects/{rag_id}")


# ============================================================================
# Resource Utilization Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.profiling
class TestResourceUtilization:
    """Tests that monitor CPU, memory, and I/O utilization patterns."""
    
    def test_cpu_during_query(self, api_client, profiling_rag, profiler):
        """
        Monitor CPU utilization during queries.
        
        This test collects data rather than asserting limits,
        to help identify optimization opportunities.
        """
        cpu_samples = []
        
        # Sample CPU during a query
        def sample_cpu():
            for _ in range(30):
                cpu_samples.append(psutil.cpu_percent(interval=0.1))
        
        import threading
        sampler = threading.Thread(target=sample_cpu)
        sampler.start()
        
        # Run query while sampling
        response = api_client.post("/rag/query", json={
            "prompt": "Provide a comprehensive analysis of the financial data",
            "project_id": profiling_rag
        }, timeout=120)
        
        sampler.join()
        
        if cpu_samples:
            avg_cpu = statistics.mean(cpu_samples)
            max_cpu = max(cpu_samples)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"CPU UTILIZATION DURING QUERY")
            logger.info(f"{'='*60}")
            logger.info(f"  Average: {avg_cpu:.1f}%")
            logger.info(f"  Peak: {max_cpu:.1f}%")
            logger.info(f"  Samples: {len(cpu_samples)}")
            logger.info(f"{'='*60}\n")
            
            # This is informational - high CPU during LLM inference is expected
            # But sustained 100% might indicate issues
            if avg_cpu > 95:
                logger.warning("CPU consistently at 100% - potential bottleneck")
    
    def test_memory_stability_over_time(self, api_client, profiling_rag, profiler):
        """
        Memory should remain stable over multiple operations.
        
        Increasing memory over time indicates memory leaks.
        """
        memory_readings = []
        
        # Baseline
        memory_readings.append(profiler.get_memory_mb())
        
        # Run 5 queries with memory checks
        for i in range(5):
            api_client.post("/rag/query", json={
                "prompt": f"Query {i}: summarize the data",
                "project_id": profiling_rag
            }, timeout=120)
            time.sleep(2)
            memory_readings.append(profiler.get_memory_mb())
        
        # Calculate trend
        first_half_avg = statistics.mean(memory_readings[:3])
        second_half_avg = statistics.mean(memory_readings[3:])
        trend = second_half_avg - first_half_avg
        
        logger.info(f"Memory trend: {trend:+.2f}MB (first half: {first_half_avg:.0f}MB, "
                   f"second half: {second_half_avg:.0f}MB)")
        
        # Allow some growth but flag significant increases
        assert trend < 200, \
            f"Memory growing over time: {trend:+.2f}MB. Potential memory leak."


# ============================================================================
# Import Performance Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.profiling
class TestImportPerformance:
    """Tests that validate import speed for different file sizes."""
    
    def test_small_file_import_speed(self, api_client, financial_sample, profiler):
        """Small files (<1MB) should import in under 10 seconds."""
        # Create test RAG
        response = api_client.post("/projects", json={
            "name": f"Small File Speed Test_{uuid.uuid4().hex[:8]}",
            "description": "Testing small file import speed"
        })
        assert response.status_code == 200
        rag_id = response.json()["id"]
        
        try:
            with profiler.measure("small_file_import"):
                start = time.time()
                response = api_client.upload_file(
                    "/datasources/connect",
                    financial_sample,
                    data={'project_id': str(rag_id), 'source_type': 'file'}
                )
                elapsed = time.time() - start
            
            assert response.status_code == 200
            
            file_size_mb = financial_sample.stat().st_size / (1024 * 1024)
            logger.info(f"Small file ({file_size_mb:.2f}MB) imported in {elapsed:.2f}s "
                       f"(max: {SMALL_FILE_IMPORT_MAX_S}s)")
            
            assert elapsed < SMALL_FILE_IMPORT_MAX_S, \
                f"Small file import too slow: {elapsed:.2f}s > {SMALL_FILE_IMPORT_MAX_S}s"
        
        finally:
            api_client.delete(f"/projects/{rag_id}")
    
    def test_batch_import_efficiency(self, api_client, profiler):
        """Batch import should be more efficient than individual imports."""
        # Find multiple files
        csv_files = list(Path(config.USER_GENERATED_DATA_DIR).glob("*.csv"))[:5]
        if len(csv_files) < 3:
            pytest.skip("Not enough CSV files for batch test")
        
        # Create test RAG
        response = api_client.post("/projects", json={
            "name": f"Batch Import Test_{uuid.uuid4().hex[:8]}",
            "description": "Testing batch import efficiency"
        })
        assert response.status_code == 200
        rag_id = response.json()["id"]
        
        try:
            # Time batch import
            with profiler.measure("batch_import"):
                response = api_client.post("/datasources/import/start", json={
                    "files": [str(f) for f in csv_files],
                    "project_id": rag_id,
                    "skip_profiling": True
                })
                assert response.status_code == 200
                job_id = response.json()["job_id"]
                
                # Wait for completion
                start = time.time()
                while time.time() - start < 120:
                    status_resp = api_client.get(f"/datasources/import/{job_id}/status")
                    if status_resp.status_code != 200:
                        break
                    status = status_resp.json()
                    if status.get("status") in ["completed", "failed"]:
                        break
                    time.sleep(2)
            
            batch_time = time.time() - start
            files_per_second = len(csv_files) / batch_time if batch_time > 0 else 0
            
            logger.info(f"Batch import of {len(csv_files)} files in {batch_time:.2f}s "
                       f"({files_per_second:.2f} files/sec)")
            
            # Should process at least 0.1 files/second
            assert files_per_second >= 0.1, \
                f"Batch import too slow: {files_per_second:.2f} files/sec"
        
        finally:
            api_client.delete(f"/projects/{rag_id}")
