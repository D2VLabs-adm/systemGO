"""
Locust load testing scenarios for RangerIO
Simulates concurrent users for performance testing
"""
from locust import HttpUser, task, between, events
import random
import logging
import time

logger = logging.getLogger(__name__)


class RangerIOUser(HttpUser):
    """Simulates a RangerIO user"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    host = "http://127.0.0.1:9000"
    
    def on_start(self):
        """Called when a simulated user starts"""
        # Create a test RAG
        response = self.client.post("/projects", json={
            "name": f"Load Test RAG {random.randint(1000, 9999)}",
            "description": "Load testing"
        })
        if response.status_code == 200:
            self.rag_id = response.json()["id"]
        else:
            self.rag_id = 1  # Fallback
    
    @task(3)
    def query_rag(self):
        """Most frequent: Query RAG system"""
        self.client.post("/rag/query", json={
            "prompt": "What is the summary?",
            "project_id": self.rag_id
        }, timeout=30)
    
    @task(2)
    def list_datasources(self):
        """Frequent: List data sources"""
        self.client.get(f"/datasources/project/{self.rag_id}")
    
    @task(2)
    def list_projects(self):
        """Frequent: List all RAGs/projects"""
        self.client.get("/projects")
    
    @task(1)
    def get_health(self):
        """Regular: Check health"""
        self.client.get("/health")
    
    @task(1)
    def get_prompts(self):
        """Regular: List prompts"""
        self.client.get("/prompts")


# Performance tracking
response_times = []


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track response times"""
    if exception is None:
        response_times.append(response_time)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print stats when test completes"""
    if response_times:
        avg_response = sum(response_times) / len(response_times)
        max_response = max(response_times)
        min_response = min(response_times)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"LOAD TEST SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total Requests: {len(response_times)}")
        logger.info(f"Avg Response Time: {avg_response:.2f}ms")
        logger.info(f"Min Response Time: {min_response:.2f}ms")
        logger.info(f"Max Response Time: {max_response:.2f}ms")
        logger.info(f"{'='*60}\n")


# Run with: 
# locust -f rangerio_tests/load/locustfile.py --headless --users 20 --spawn-rate 5 --run-time 1m
# Or for interactive: locust -f rangerio_tests/load/locustfile.py --host http://127.0.0.1:9000

