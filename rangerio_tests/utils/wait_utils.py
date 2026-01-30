"""
Utility functions for smart waiting in tests.
Replaces fixed sleep() calls with intelligent polling.
"""
import time
import logging
from typing import Callable, Any, Optional

logger = logging.getLogger("rangerio_tests.wait")


def wait_for_condition(
    condition_fn: Callable[[], bool],
    timeout: float = 30,
    poll_interval: float = 1,
    description: str = "condition"
) -> bool:
    """
    Poll until condition is true or timeout.
    
    Args:
        condition_fn: Function that returns True when condition is met
        timeout: Maximum wait time in seconds
        poll_interval: Time between polls
        description: Description for logging
        
    Returns:
        True if condition met, False if timeout
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            if condition_fn():
                elapsed = time.time() - start
                logger.info(f"✓ {description} satisfied in {elapsed:.1f}s")
                return True
        except Exception as e:
            logger.debug(f"Condition check failed: {e}")
        time.sleep(poll_interval)
    
    logger.warning(f"✗ {description} timeout after {timeout}s")
    return False


def wait_for_rag_ready(api_client, rag_id: int, max_wait: float = 60) -> bool:
    """
    Wait for RAG to be indexed and ready for queries.
    
    Args:
        api_client: Test API client
        rag_id: RAG project ID
        max_wait: Maximum wait time
        
    Returns:
        True if RAG is ready, False if timeout
    """
    def check_ready():
        try:
            # Try a simple query to see if RAG responds
            resp = api_client.get(f"/projects/{rag_id}", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                # Check if has data sources
                ds_resp = api_client.get(f"/projects/{rag_id}/datasources", timeout=5)
                if ds_resp.status_code == 200:
                    sources = ds_resp.json()
                    if sources and len(sources) > 0:
                        return True
            return False
        except Exception:
            return False
    
    return wait_for_condition(
        check_ready,
        timeout=max_wait,
        poll_interval=2,
        description=f"RAG {rag_id} ready"
    )


def wait_for_task_complete(api_client, task_id: int, max_wait: float = 120) -> bool:
    """
    Wait for a background task to complete.
    
    Args:
        api_client: Test API client
        task_id: Task ID to monitor
        max_wait: Maximum wait time
        
    Returns:
        True if task completed, False if timeout or failed
    """
    def check_complete():
        try:
            resp = api_client.get(f"/tasks/{task_id}", timeout=5)
            if resp.status_code == 200:
                task = resp.json()
                status = task.get("status", "")
                if status in ["completed", "success"]:
                    return True
                if status in ["failed", "error", "cancelled"]:
                    logger.warning(f"Task {task_id} failed with status: {status}")
                    return True  # Return true to stop waiting
            return False
        except Exception:
            return False
    
    return wait_for_condition(
        check_complete,
        timeout=max_wait,
        poll_interval=2,
        description=f"Task {task_id} complete"
    )


def wait_for_import_indexed(api_client, ds_id: int, max_wait: float = 90) -> bool:
    """
    Wait for a data source import to be fully indexed AND queryable.
    
    Args:
        api_client: Test API client  
        ds_id: Data source ID
        max_wait: Maximum wait time
        
    Returns:
        True if indexed and queryable, False if timeout
    """
    def check_indexed():
        try:
            resp = api_client.get(f"/datasources/{ds_id}", timeout=5)
            if resp.status_code == 200:
                ds = resp.json()
                # Check for actual RangerIO indexing status
                # API returns: rag_status: "ready" (not "indexed"), profiling_status: "success"
                rag_status = ds.get("rag_status", "")
                profiling_status = ds.get("profiling_status", "")
                
                # Accept "ready" or "indexed" as valid indexed states
                if rag_status in ("ready", "indexed") and profiling_status == "success":
                    logger.info(f"DataSource {ds_id}: rag_status={rag_status}, profiling_status={profiling_status}")
                    return True
                    
                # Fallback checks
                if ds.get("indexed", False):
                    return True
                if ds.get("row_count", 0) > 0 and rag_status in ("ready", "indexed"):
                    return True
            return False
        except Exception as e:
            logger.debug(f"check_indexed error: {e}")
            return False
    
    # First wait for basic indexing flags
    if not wait_for_condition(
        check_indexed,
        timeout=max_wait,
        poll_interval=3,
        description=f"DataSource {ds_id} indexed"
    ):
        return False
    
    # Then verify data is actually queryable in RAG
    def check_queryable():
        try:
            resp = api_client.post("/rag/query", json={
                "prompt": "How many columns?",
                "data_source_ids": [ds_id]
            }, timeout=30)
            if resp.status_code == 200:
                answer = resp.json().get("answer", "")
                # Check if we got a real answer, not "I don't have profile"
                if "don't have profile" not in answer.lower():
                    logger.info(f"DataSource {ds_id} is queryable")
                    return True
            return False
        except Exception as e:
            logger.debug(f"check_queryable error: {e}")
            return False
    
    return wait_for_condition(
        check_queryable,
        timeout=60,  # Additional wait for vector store
        poll_interval=5,
        description=f"DataSource {ds_id} queryable"
    )


def check_backend_healthy(api_client, timeout: float = 5) -> bool:
    """
    Quick health check for backend.
    
    Args:
        api_client: Test API client
        timeout: Request timeout
        
    Returns:
        True if healthy, False otherwise
    """
    try:
        resp = api_client.get("/health", timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("status") == "healthy"
        return False
    except Exception:
        return False


# Timeout constants - tiered by operation type
class Timeouts:
    """Centralized timeout configuration."""
    
    # Quick API operations
    API_QUICK = 10
    
    # Health/status checks
    HEALTH_CHECK = 5
    
    # Import operations - tiered by file size
    IMPORT_SMALL = 30   # < 1MB files
    IMPORT_MEDIUM = 60  # 1-10MB files
    IMPORT_LARGE = 120  # > 10MB files
    
    # Query operations - tiered by complexity
    QUERY_SIMPLE = 15   # Column listing, counts
    QUERY_MEDIUM = 45   # Aggregations, filters
    QUERY_LLM = 90      # Full LLM inference
    
    # Waiting for background processes
    RAG_INDEX = 45      # RAG indexing
    TASK_COMPLETE = 60  # Task completion
    
    # Stress test limits
    STRESS_QUERY = 120
    STRESS_IMPORT = 180
