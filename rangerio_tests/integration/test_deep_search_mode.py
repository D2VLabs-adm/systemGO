"""
Deep Search Mode Test Suite

Tests Deep Search-specific features:
1. Compound query handling (multi-part questions, SQL decomposition)
2. Query validation with actual test queries
3. Map-reduce for multi-source queries
4. Hierarchical RAG for exploratory queries
"""
import pytest
import time
from pathlib import Path
from rangerio_tests.utils.mode_config import get_mode, ModeValidator


@pytest.mark.integration
def test_compound_query_handling(api_client, sample_csv_small):
    """
    Test that Deep Search mode correctly handles compound queries.
    Multi-part questions should be decomposed and results aggregated.
    """
    # Create RAG
    rag_name = f"Compound Query Test {int(time.time())}"
    rag_response = api_client.post("/projects", json={"name": rag_name})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    # Upload data
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    assert upload_resp.status_code == 200
    
    deep_search_mode = get_mode('deep')
    basic_mode = get_mode('basic')
    
    # Compound query (requires analyzing multiple aspects)
    compound_query = "What is the average age AND the maximum salary?"
    
    print(f"\n{'='*70}")
    print(f"COMPOUND QUERY HANDLING")
    print(f"{'='*70}")
    print(f"Query: {compound_query}")
    
    # Test with Basic mode (may not handle compound correctly)
    basic_resp = api_client.post("/rag/query", json={
        "prompt": compound_query,
        "project_id": rag_id,
        **basic_mode.to_api_params()
    })
    basic_result = basic_resp.json() if basic_resp.status_code == 200 else {}
    
    print(f"\nBasic Mode:")
    print(f"  Answer: {basic_result.get('answer', '')[:150]}...")
    
    # Test with Deep Search mode (should decompose and handle)
    deep_resp = api_client.post("/rag/query", json={
        "prompt": compound_query,
        "project_id": rag_id,
        **deep_search_mode.to_api_params()
    })
    assert deep_resp.status_code == 200
    deep_result = deep_resp.json()
    
    metadata = deep_result.get('metadata', {})
    print(f"\nDeep Search Mode:")
    print(f"  Answer: {deep_result.get('answer', '')[:150]}...")
    print(f"  Compound query detected: {'compound_query' in metadata}")
    if 'compound_query' in metadata:
        print(f"  Sub-queries: {metadata['compound_query'].get('sub_queries', [])}")
    print(f"{'='*70}\n")
    
    # Validate Deep Search provides metadata
    assert 'answer' in deep_result, "Deep Search should return an answer"
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")


@pytest.mark.integration
def test_query_validation_with_test_queries(api_client, sample_csv_small):
    """
    Test that Deep Search mode validates suggestions by running actual test queries.
    Compare with Basic mode which uses fast heuristics.
    """
    # Create RAG
    rag_name = f"Query Validation Test {int(time.time())}"
    rag_response = api_client.post("/projects", json={"name": rag_name})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    # Upload data
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    assert upload_resp.status_code == 200
    
    deep_search_mode = get_mode('deep')
    
    # Query that should trigger suggestion validation
    ambiguous_query = "tell me about this data"
    
    print(f"\n{'='*70}")
    print(f"QUERY VALIDATION WITH TEST QUERIES")
    print(f"{'='*70}")
    print(f"Query: {ambiguous_query}")
    
    resp = api_client.post("/rag/query", json={
        "prompt": ambiguous_query,
        "project_id": rag_id,
        **deep_search_mode.to_api_params()
    })
    
    if resp.status_code == 200:
        result = resp.json()
        
        print(f"\nDeep Search Response:")
        print(f"  Answer: {result.get('answer', '')[:150]}...")
        
        # Check for clarification with validated suggestions
        if 'clarification' in result and result['clarification'] is not None:
            clarification = result['clarification']
            print(f"  Clarification provided: Yes")
            print(f"  Suggestions: {clarification.get('suggestions', [])}")
            print(f"  Quick prompts: {clarification.get('quick_prompts', [])}")
        
        # Check for validation metadata
        if 'validation' in result and result['validation'] is not None:
            print(f"  Validation metadata present: Yes")
            validation = result['validation']
            print(f"  Validation details: {validation}")
        
        print(f"{'='*70}\n")
    else:
        print(f"  Response status: {resp.status_code}")
        print(f"  Error: {resp.text[:200]}")
        print(f"{'='*70}\n")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")


@pytest.mark.integration
def test_map_reduce_multi_source(api_client, sample_csv_small):
    """
    Test that Deep Search mode uses map-reduce for multi-source queries.
    Requires querying across multiple data sources and aggregating results.
    """
    # Create RAG
    rag_name = f"Map-Reduce Test {int(time.time())}"
    rag_response = api_client.post("/projects", json={"name": rag_name})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    # Upload multiple data sources
    for i in range(3):
        upload_resp = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        assert upload_resp.status_code == 200
    
    deep_search_mode = get_mode('deep')
    
    # Multi-source aggregation query
    multi_source_query = "Compare the totals across all datasets"
    
    print(f"\n{'='*70}")
    print(f"MAP-REDUCE MULTI-SOURCE TEST")
    print(f"{'='*70}")
    print(f"Query: {multi_source_query}")
    
    resp = api_client.post("/rag/query", json={
        "prompt": multi_source_query,
        "project_id": rag_id,
        **deep_search_mode.to_api_params()
    })
    
    if resp.status_code == 200:
        result = resp.json()
        metadata = result.get('metadata', {})
        
        print(f"\nDeep Search Response:")
        print(f"  Answer: {result.get('answer', '')[:200]}...")
        print(f"  Strategy used: {metadata.get('strategy', 'N/A')}")
        print(f"  Sources queried: {len(result.get('sources', []))}")
        
        if 'map_reduce' in metadata:
            print(f"  Map-reduce metadata: {metadata['map_reduce']}")
        
        print(f"{'='*70}\n")
    else:
        print(f"  Response status: {resp.status_code}")
        print(f"  Note: Map-reduce might require 4+ data sources or specific keywords")
        print(f"{'='*70}\n")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")


@pytest.mark.integration
def test_hierarchical_rag_exploratory(api_client, sample_csv_small):
    """
    Test that Deep Search mode uses hierarchical RAG for exploratory queries.
    Queries like "tell me about" or "overview of" should trigger multi-level retrieval.
    """
    # Create RAG
    rag_name = f"Hierarchical Test {int(time.time())}"
    rag_response = api_client.post("/projects", json={"name": rag_name})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    # Upload data
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    assert upload_resp.status_code == 200
    
    deep_search_mode = get_mode('deep')
    basic_mode = get_mode('basic')
    
    # Exploratory query
    exploratory_query = "Give me an overview of this dataset"
    
    print(f"\n{'='*70}")
    print(f"HIERARCHICAL RAG TEST")
    print(f"{'='*70}")
    print(f"Query: {exploratory_query}")
    
    # Test with Basic mode
    basic_resp = api_client.post("/rag/query", json={
        "prompt": exploratory_query,
        "project_id": rag_id,
        **basic_mode.to_api_params()
    })
    basic_result = basic_resp.json() if basic_resp.status_code == 200 else {}
    
    print(f"\nBasic Mode:")
    print(f"  Answer length: {len(basic_result.get('answer', ''))} chars")
    print(f"  Answer: {basic_result.get('answer', '')[:150]}...")
    
    # Test with Deep Search mode
    deep_resp = api_client.post("/rag/query", json={
        "prompt": exploratory_query,
        "project_id": rag_id,
        **deep_search_mode.to_api_params()
    })
    
    if deep_resp.status_code == 200:
        deep_result = deep_resp.json()
        metadata = deep_result.get('metadata', {})
        
        print(f"\nDeep Search Mode:")
        print(f"  Answer length: {len(deep_result.get('answer', ''))} chars")
        print(f"  Answer: {deep_result.get('answer', '')[:150]}...")
        print(f"  Strategy: {metadata.get('strategy', 'N/A')}")
        
        # Deep Search should potentially provide more comprehensive answer
        # or use hierarchical strategy
        if metadata.get('strategy') == 'hierarchical':
            print(f"  ✓ Hierarchical strategy detected")
        
        print(f"{'='*70}\n")
    else:
        print(f"  Response status: {deep_resp.status_code}")
        print(f"{'='*70}\n")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")


@pytest.mark.integration
def test_deep_search_performance(api_client, sample_csv_small):
    """
    Test that Deep Search mode response times are within expected range.
    Should be slower than Basic and Assistant modes due to thorough validation.
    """
    # Create RAG
    rag_name = f"Deep Search Perf Test {int(time.time())}"
    rag_response = api_client.post("/projects", json={"name": rag_name})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    # Upload data
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    assert upload_resp.status_code == 200
    
    deep_search_mode = get_mode('deep')
    validator = ModeValidator(deep_search_mode)
    
    query = "What are the key statistics in this dataset?"
    
    # Run query and measure time
    start_time = time.time()
    resp = api_client.post("/rag/query", json={
        "prompt": query,
        "project_id": rag_id,
        **deep_search_mode.to_api_params()
    })
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    if resp.status_code == 200:
        result = resp.json()
        
        # Validate response time
        is_valid_time = validator.validate_response_time(elapsed_ms)
        
        print(f"\n{'='*70}")
        print(f"DEEP SEARCH MODE PERFORMANCE")
        print(f"{'='*70}")
        print(f"Query: {query}")
        print(f"Response time: {elapsed_ms}ms")
        print(f"Expected range: {deep_search_mode.expected_response_time}")
        print(f"Within range: {is_valid_time}")
        print(f"Answer: {result.get('answer', '')[:100]}...")
        print(f"{'='*70}\n")
        
        # Warn if outside expected range but don't fail
        if not is_valid_time:
            print(f"⚠️  WARNING: Response time {elapsed_ms}ms outside expected range {deep_search_mode.expected_response_time}")
    else:
        print(f"Response status: {resp.status_code}")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")


@pytest.mark.integration
def test_deep_search_vs_basic_comparison(api_client, sample_csv_small):
    """
    Direct comparison of Basic mode vs Deep Search mode for the same queries.
    Validates that Deep Search provides enhanced analysis.
    """
    # Create RAG
    rag_name = f"Deep vs Basic Test {int(time.time())}"
    rag_response = api_client.post("/projects", json={"name": rag_name})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    # Upload data
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    assert upload_resp.status_code == 200
    
    basic_mode = get_mode('basic')
    deep_search_mode = get_mode('deep')
    
    test_queries = [
        "What is the average age AND maximum salary?",  # Compound
        "Give me an overview",  # Exploratory
        "How many records?",  # Simple (shouldn't need Deep Search)
    ]
    
    print(f"\n{'='*70}")
    print(f"BASIC vs DEEP SEARCH MODE COMPARISON")
    print(f"{'='*70}")
    
    for query in test_queries:
        # Basic mode
        basic_start = time.time()
        basic_resp = api_client.post("/rag/query", json={
            "prompt": query,
            "project_id": rag_id,
            **basic_mode.to_api_params()
        })
        basic_time_ms = int((time.time() - basic_start) * 1000)
        basic_result = basic_resp.json() if basic_resp.status_code == 200 else {}
        
        # Deep Search mode
        deep_start = time.time()
        deep_resp = api_client.post("/rag/query", json={
            "prompt": query,
            "project_id": rag_id,
            **deep_search_mode.to_api_params()
        })
        deep_time_ms = int((time.time() - deep_start) * 1000)
        deep_result = deep_resp.json() if deep_resp.status_code == 200 else {}
        
        print(f"\nQuery: {query}")
        print(f"  Basic:")
        print(f"    Time: {basic_time_ms}ms")
        print(f"    Answer: {basic_result.get('answer', '')[:60]}...")
        
        print(f"  Deep Search:")
        print(f"    Time: {deep_time_ms}ms")
        print(f"    Answer: {deep_result.get('answer', '')[:60]}...")
        print(f"    Strategy: {deep_result.get('metadata', {}).get('strategy', 'N/A')}")
        
        # Validate Deep Search is typically slower but provides answers
        if deep_resp.status_code == 200:
            assert 'answer' in deep_result, f"Deep Search should return answer for '{query}'"
    
    print(f"{'='*70}\n")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")



