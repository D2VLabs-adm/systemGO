"""
Assistant Mode E2E Tests for RangerIO
=====================================

Tests for smart assistant features including:
1. Clarification generation for ambiguous queries
2. Follow-up suggestions after queries
3. Quick-start prompts based on data profiles
4. Response confidence calculation
5. Smart query routing (DSPy integration)

Uses test files from: /Users/vadim/Documents/RangerIO test files/

Run with:
    PYTHONPATH=. pytest rangerio_tests/integration/test_assistant_mode.py -v --tb=long
"""
import pytest
import time
import json
import re
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from rangerio_tests.config import config, logger

# Test timeouts
QUERY_TIMEOUT = 180  # 3 minutes for LLM queries
RAG_INGESTION_WAIT = 45  # seconds to wait for RAG indexing


# =============================================================================
# ASSISTANT MODE TESTS
# =============================================================================

@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.assistant
class TestAssistantMode:
    """
    Test smart assistant features.
    
    These tests validate the intelligent features that help users
    get better results from their data analysis.
    """
    
    @pytest.fixture(scope="function")
    def assistant_rag(self, api_client, financial_sample):
        """Create RAG with financial data for assistant mode testing"""
        # Create RAG
        import uuid
        response = api_client.post("/projects", json={
            "name": f"Assistant Mode Test RAG_{uuid.uuid4().hex[:8]}",
            "description": "RAG for testing smart assistant features"
        })
        assert response.status_code == 200
        rag_id = response.json()["id"]
        
        # Import financial data
        response = api_client.upload_file(
            "/datasources/connect",
            financial_sample,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        assert response.status_code == 200
        
        # Wait for ingestion
        logger.info(f"Waiting for RAG ingestion ({RAG_INGESTION_WAIT}s)...")
        time.sleep(RAG_INGESTION_WAIT)
        
        logger.info(f"Created assistant test RAG: {rag_id}")
        yield rag_id
        
        # Cleanup
        try:
            api_client.delete(f"/projects/{rag_id}")
        except:
            pass
    
    def test_basic_assistant_query(self, api_client, assistant_rag):
        """Test basic query with assistant mode enabled"""
        response = api_client.post(
            "/rag/query",
            json={
                "prompt": "What is the total revenue?",
                "project_id": assistant_rag,
                "assistant_mode": True
            },
            timeout=QUERY_TIMEOUT
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Check response structure
        answer = result.get('answer', '')
        assert len(answer) > 0, "Should return an answer"
        
        # Log assistant mode response details
        logger.info(f"Assistant mode response keys: {list(result.keys())}")
        logger.info(f"Answer length: {len(answer)}")
        
        # Check for confidence if available
        if 'confidence' in result:
            logger.info(f"Response confidence: {result['confidence']}")
    
    def test_follow_up_suggestions(self, api_client, assistant_rag):
        """Test follow-up suggestions generation after query"""
        # First query to establish context
        response = api_client.post(
            "/rag/query",
            json={
                "prompt": "What are the main product segments?",
                "project_id": assistant_rag,
                "assistant_mode": True
            },
            timeout=QUERY_TIMEOUT
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Check for follow-up suggestions
        follow_ups = result.get('follow_up_suggestions', [])
        suggestions = result.get('suggestions', [])
        
        # Either field may contain suggestions
        all_suggestions = follow_ups or suggestions
        
        if all_suggestions:
            logger.info(f"Follow-up suggestions ({len(all_suggestions)}):")
            for i, suggestion in enumerate(all_suggestions[:5]):
                logger.info(f"  {i+1}. {suggestion}")
        else:
            logger.info("No follow-up suggestions returned (may not be enabled)")
    
    def test_response_confidence(self, api_client, assistant_rag):
        """Test response confidence calculation"""
        # Query with clear answer in data
        high_conf_response = api_client.post(
            "/rag/query",
            json={
                "prompt": "List the column names in the data",
                "project_id": assistant_rag,
                "assistant_mode": True
            },
            timeout=QUERY_TIMEOUT
        )
        
        assert high_conf_response.status_code == 200
        high_result = high_conf_response.json()
        
        # Query that should have lower confidence
        low_conf_response = api_client.post(
            "/rag/query",
            json={
                "prompt": "What will be the revenue next year?",
                "project_id": assistant_rag,
                "assistant_mode": True
            },
            timeout=QUERY_TIMEOUT
        )
        
        assert low_conf_response.status_code == 200
        low_result = low_conf_response.json()
        
        # Log confidence scores
        high_conf = high_result.get('confidence', {})
        low_conf = low_result.get('confidence', {})
        
        logger.info(f"High confidence query result: {high_conf}")
        logger.info(f"Low confidence query result: {low_conf}")
        
        # Check for confidence structure
        if isinstance(high_conf, dict):
            if 'overall' in high_conf:
                logger.info(f"High confidence overall: {high_conf['overall']}")
            if 'data_coverage' in high_conf:
                logger.info(f"High confidence data coverage: {high_conf['data_coverage']}")
    
    def test_smart_query_routing(self, api_client, assistant_rag):
        """Test smart query routing (DSPy-based)"""
        # Simple factual query
        simple_response = api_client.post(
            "/rag/query",
            json={
                "prompt": "How many rows of data are there?",
                "project_id": assistant_rag,
                "use_routing": True
            },
            timeout=QUERY_TIMEOUT
        )
        
        assert simple_response.status_code == 200
        simple_result = simple_response.json()
        
        # Complex analytical query
        complex_response = api_client.post(
            "/rag/query",
            json={
                "prompt": "Analyze the trends across all segments and regions over time, comparing performance and identifying patterns",
                "project_id": assistant_rag,
                "use_routing": True
            },
            timeout=QUERY_TIMEOUT
        )
        
        assert complex_response.status_code == 200
        complex_result = complex_response.json()
        
        # Log routing decisions if available
        simple_routing = simple_result.get('routing', simple_result.get('strategy', 'unknown'))
        complex_routing = complex_result.get('routing', complex_result.get('strategy', 'unknown'))
        
        logger.info(f"Simple query routing: {simple_routing}")
        logger.info(f"Complex query routing: {complex_routing}")
    
    def test_query_with_clarification_needed(self, api_client, assistant_rag):
        """Test handling of ambiguous queries that may need clarification"""
        # Ambiguous query
        response = api_client.post(
            "/rag/query",
            json={
                "prompt": "What is the total?",  # Ambiguous - total of what?
                "project_id": assistant_rag,
                "assistant_mode": True
            },
            timeout=QUERY_TIMEOUT
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Check for clarification request or answer
        clarification = result.get('clarification', result.get('needs_clarification'))
        answer = result.get('answer', '')
        
        if clarification:
            logger.info(f"Clarification requested: {clarification}")
        else:
            # If no clarification, it should still provide some answer
            logger.info(f"No clarification - answer provided: {answer[:200]}...")


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.assistant
class TestDeepSearchMode:
    """
    Test deep search/analysis functionality.
    
    Deep search performs more thorough analysis across multiple sources.
    """
    
    @pytest.fixture(scope="function")
    def deep_search_rag(self, api_client, financial_sample):
        """Create RAG for deep search testing"""
        response = api_client.post("/projects", json={
            "name": f"Deep Search Test RAG_{uuid.uuid4().hex[:8]}",
            "description": "RAG for testing deep search analysis"
        })
        assert response.status_code == 200
        rag_id = response.json()["id"]
        
        # Import data
        response = api_client.upload_file(
            "/datasources/connect",
            financial_sample,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        assert response.status_code == 200
        
        time.sleep(RAG_INGESTION_WAIT)
        
        yield rag_id
        
        try:
            api_client.delete(f"/projects/{rag_id}")
        except:
            pass
    
    def test_deep_analysis_endpoint(self, api_client, deep_search_rag):
        """Test deep analysis query endpoint"""
        response = api_client.post(
            "/rag/query/deep-analysis",
            json={
                "prompt": "Perform a comprehensive analysis of sales performance across all segments",
                "project_id": deep_search_rag
            },
            timeout=QUERY_TIMEOUT
        )
        
        # May be 200 or 404 if endpoint not available
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Deep analysis response keys: {list(result.keys())}")
            
            answer = result.get('answer', '')
            logger.info(f"Deep analysis answer length: {len(answer)}")
        elif response.status_code == 404:
            logger.info("Deep analysis endpoint not available")
        else:
            logger.warning(f"Deep analysis returned: {response.status_code}")
    
    def test_deep_search_stats(self, api_client, deep_search_rag):
        """Test deep search statistics endpoint"""
        # First get data source IDs
        ds_response = api_client.get(f"/datasources?project_id={deep_search_rag}")
        
        if ds_response.status_code != 200:
            pytest.skip("Could not get data sources")
        
        data_sources = ds_response.json()
        if not data_sources:
            pytest.skip("No data sources in RAG")
        
        ds_ids = [ds.get('id') for ds in data_sources if ds.get('id')]
        ds_ids_str = ",".join(map(str, ds_ids))
        
        # Test deep analysis stats endpoint
        response = api_client.get(f"/rag/deep-analysis/stats?data_source_ids={ds_ids_str}")
        
        if response.status_code == 200:
            stats = response.json()
            logger.info(f"Deep search stats: {stats}")
        elif response.status_code == 404:
            logger.info("Deep search stats endpoint not available")
        else:
            logger.warning(f"Deep search stats returned: {response.status_code}")
    
    def test_standard_vs_deep_search(self, api_client, deep_search_rag):
        """Compare standard query vs deep search for the same question"""
        query = "What are the key insights from this data?"
        
        # Standard query
        standard_response = api_client.post(
            "/rag/query",
            json={
                "prompt": query,
                "project_id": deep_search_rag
            },
            timeout=QUERY_TIMEOUT
        )
        
        assert standard_response.status_code == 200
        standard_result = standard_response.json()
        standard_answer = standard_result.get('answer', '')
        
        # Deep search query (if available)
        deep_response = api_client.post(
            "/rag/query/deep-analysis",
            json={
                "prompt": query,
                "project_id": deep_search_rag,
                "use_deep_search": True
            },
            timeout=QUERY_TIMEOUT
        )
        
        if deep_response.status_code == 200:
            deep_result = deep_response.json()
            deep_answer = deep_result.get('answer', '')
            
            logger.info(f"Standard answer length: {len(standard_answer)}")
            logger.info(f"Deep search answer length: {len(deep_answer)}")
            
            # Deep search often produces more detailed results
            if len(deep_answer) > len(standard_answer):
                logger.info("Deep search produced more detailed response")
        else:
            logger.info(f"Deep search endpoint not available, standard answer length: {len(standard_answer)}")


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.assistant
class TestQuickStartPrompts:
    """Test quick-start prompt generation based on data profiles"""
    
    def test_quick_start_for_financial_data(self, api_client, create_test_rag, financial_sample):
        """Test quick-start prompts for financial data"""
        rag_id = create_test_rag("Quick Start Test")
        
        # Import data
        response = api_client.upload_file(
            "/datasources/connect",
            financial_sample,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        assert response.status_code == 200
        
        time.sleep(RAG_INGESTION_WAIT)
        
        # Get project/RAG details which may include quick-start prompts
        project_response = api_client.get(f"/projects/{rag_id}")
        
        if project_response.status_code == 200:
            project = project_response.json()
            quick_starts = project.get('quick_start_prompts', [])
            suggestions = project.get('suggested_queries', [])
            
            all_prompts = quick_starts or suggestions
            
            if all_prompts:
                logger.info(f"Quick-start prompts ({len(all_prompts)}):")
                for prompt in all_prompts[:5]:
                    logger.info(f"  - {prompt}")
            else:
                logger.info("No quick-start prompts in project response")
        
        # Alternative: Query with assistant mode to get suggestions
        query_response = api_client.post(
            "/rag/query",
            json={
                "prompt": "What can I ask about this data?",
                "project_id": rag_id,
                "assistant_mode": True
            },
            timeout=QUERY_TIMEOUT
        )
        
        if query_response.status_code == 200:
            result = query_response.json()
            suggestions = result.get('suggestions', result.get('follow_up_suggestions', []))
            
            if suggestions:
                logger.info(f"Query-based suggestions ({len(suggestions)}):")
                for s in suggestions[:5]:
                    logger.info(f"  - {s}")
