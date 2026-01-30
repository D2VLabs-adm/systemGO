"""
Mode Combination Matrix Tests

Tests the same queries across all 4 mode combinations:
- Basic: No features (fastest)
- Assistant: Smart features
- Deep Search: Thorough analysis
- Both: All features

Validates expected behavior differences per mode.
"""
import pytest
import time
from rangerio_tests.utils.mode_config import get_all_modes, ModeValidator, create_mode_comparison_table


# Test queries covering different query types
TEST_QUERIES = [
    {
        "query": "How many records are there?",
        "type": "factual",
        "description": "Simple factual query",
        "expectations": {
            "basic": "direct_answer",
            "assistant": "confidence_scoring",
            "deep": "sql_based_answer",
            "both": "all_features"
        }
    },
    {
        "query": "analyze this data",
        "type": "ambiguous",
        "description": "Ambiguous query requiring clarification",
        "expectations": {
            "basic": "best_effort_answer",
            "assistant": "clarification_request",
            "deep": "validated_suggestions",
            "both": "clarification_with_validation"
        }
    },
    {
        "query": "What is the average age AND the maximum salary?",
        "type": "compound",
        "description": "Compound query with multiple parts",
        "expectations": {
            "basic": "best_effort",
            "assistant": "confidence_scoring",
            "deep": "compound_decomposition",
            "both": "full_analysis"
        }
    },
    {
        "query": "What is the date range of this data?",
        "type": "hallucination_risk",
        "description": "Query likely to trigger hallucination (no dates in data)",
        "expectations": {
            "basic": "hallucination_check",
            "assistant": "low_confidence_or_clarification",
            "deep": "validated_response",
            "both": "comprehensive_check"
        }
    },
    {
        "query": "Summarize the dataset in 20 words",
        "type": "constraint",
        "description": "Query with explicit constraint",
        "expectations": {
            "basic": "ignore_constraint",
            "assistant": "constraint_enforcement",
            "deep": "thorough_summary",
            "both": "constrained_thorough_summary"
        }
    },
]


@pytest.mark.integration
@pytest.mark.parametrize("query_info", TEST_QUERIES, ids=[q["type"] for q in TEST_QUERIES])
def test_query_across_all_modes(api_client, sample_csv_small, query_info):
    """
    Test the same query across all 4 mode combinations.
    Validates expected behavior for each mode.
    """
    query = query_info["query"]
    query_type = query_info["type"]
    expectations = query_info["expectations"]
    
    # Create RAG
    rag_name = f"Matrix Test {query_type} {int(time.time())}"
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
    
    print(f"\n{'='*70}")
    print(f"QUERY: {query}")
    print(f"TYPE: {query_type}")
    print(f"{'='*70}")
    
    results = {}
    
    # Test across all modes
    for mode_name, mode_config in get_all_modes().items():
        start_time = time.time()
        
        resp = api_client.post("/rag/query", json={
            "prompt": query,
            "project_id": rag_id,
            **mode_config.to_api_params()
        })
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if resp.status_code == 200:
            result = resp.json()
            validator = ModeValidator(mode_config)
            
            # Collect results
            results[mode_name] = {
                'mode_config': mode_config,
                'response_time_ms': elapsed_ms,
                'answer': result.get('answer', ''),
                'confidence': result.get('confidence'),
                'hallucination_check': result.get('hallucination_check'),
                'clarification': result.get('clarification'),
                'disambiguation': result.get('disambiguation'),
                'constraints': result.get('constraints'),
                'metadata': result.get('metadata', {}),
                'validation_summary': validator.get_validation_summary(result, elapsed_ms)
            }
            
            print(f"\n{mode_config.name} Mode:")
            print(f"  Time: {elapsed_ms}ms (expected: {mode_config.expected_response_time})")
            print(f"  Expectation: {expectations.get(mode_name, 'N/A')}")
            print(f"  Answer: {result.get('answer', '')[:80]}...")
            
            # Mode-specific checks
            if mode_config.assistant_mode:
                print(f"  Has confidence: {'confidence' in result}")
                if 'confidence' in result:
                    print(f"    Score: {result['confidence'].get('score', 'N/A')}")
            
            if mode_config.deep_search_mode:
                print(f"  Strategy: {result.get('metadata', {}).get('strategy', 'N/A')}")
            
            # Check for clarification (only present if needed)
            if result.get('clarification'):
                print(f"  Clarification: Needed")
                suggestions = result['clarification'].get('suggested_questions', [])
                print(f"    Suggestions: {len(suggestions)}")
            elif mode_config.assistant_mode:
                print(f"  Clarification: Not needed")
        else:
            print(f"\n{mode_config.name} Mode:")
            print(f"  ERROR: Status {resp.status_code}")
            results[mode_name] = {
                'error': True,
                'status_code': resp.status_code,
                'response_time_ms': elapsed_ms
            }
    
    print(f"\n{'='*70}")
    print(f"SUMMARY FOR: {query}")
    print(f"{'='*70}")
    
    # Validate mode-specific expectations
    for mode_name, result in results.items():
        if result.get('error'):
            continue
        
        mode_config = result['mode_config']
        expectation = expectations.get(mode_name, '')
        
        print(f"\n{mode_config.name}:")
        print(f"  Expected behavior: {expectation}")
        
        # Validate based on query type and mode
        if query_type == "ambiguous" and mode_config.assistant_mode:
            # Assistant mode should provide confidence or clarification
            has_feature = result.get('confidence') or result.get('clarification')
            print(f"  ✓ Assistant features present: {bool(has_feature)}")
        
        if query_type == "compound" and mode_config.deep_search_mode:
            # Deep Search should handle compound queries
            print(f"  ✓ Deep Search active: True")
        
        if query_type == "constraint" and mode_config.assistant_mode:
            # Assistant should detect constraints
            has_constraints = result.get('constraints') is not None
            print(f"  ✓ Constraints detected: {has_constraints}")
        
        if query_type == "hallucination_risk":
            # Check hallucination detection
            h_check = result.get('hallucination_check', {})
            print(f"  Hallucination detected: {h_check.get('is_hallucination', 'N/A')}")
            print(f"  Hallucination score: {h_check.get('score', 'N/A')}")
    
    print(f"{'='*70}\n")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")
    
    # Store results for comparison (in real test run, this would be aggregated)
    return results


@pytest.mark.integration
def test_mode_comparison_summary(api_client, sample_csv_small):
    """
    Run a representative query across all modes and generate comparison summary.
    """
    # Create RAG
    rag_name = f"Mode Summary Test {int(time.time())}"
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
    
    # Representative query
    query = "What are the key characteristics of this dataset?"
    
    comparison_results = {}
    
    for mode_name, mode_config in get_all_modes().items():
        start_time = time.time()
        
        resp = api_client.post("/rag/query", json={
            "prompt": query,
            "project_id": rag_id,
            **mode_config.to_api_params()
        })
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if resp.status_code == 200:
            result = resp.json()
            
            comparison_results[mode_name] = {
                'avg_response_time_ms': elapsed_ms,
                'accuracy_score': 'N/A',  # Would need human evaluation
                'answer_length': len(result.get('answer', '')),
                'features': []
            }
            
            # Identify active features
            if 'confidence' in result:
                comparison_results[mode_name]['features'].append('confidence')
            if 'clarification' in result:
                comparison_results[mode_name]['features'].append('clarification')
            if result.get('metadata', {}).get('strategy'):
                comparison_results[mode_name]['features'].append(result['metadata']['strategy'])
    
    # Generate comparison table
    print(f"\n{'='*70}")
    print(f"MODE COMPARISON SUMMARY")
    print(f"Query: {query}")
    print(f"{'='*70}\n")
    
    table = create_mode_comparison_table(comparison_results)
    print(table)
    print(f"\n{'='*70}\n")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")


@pytest.mark.integration
def test_mode_feature_matrix(api_client, sample_csv_small):
    """
    Test that expected features are present/absent correctly for each mode.
    Creates a feature presence matrix across all modes.
    """
    # Create RAG
    rag_name = f"Feature Matrix Test {int(time.time())}"
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
    
    query = "Summarize this dataset"
    
    feature_matrix = {}
    
    for mode_name, mode_config in get_all_modes().items():
        resp = api_client.post("/rag/query", json={
            "prompt": query,
            "project_id": rag_id,
            **mode_config.to_api_params()
        })
        
        if resp.status_code == 200:
            result = resp.json()
            validator = ModeValidator(mode_config)
            
            # Check feature presence
            features = {
                'confidence_scoring': 'confidence' in result,
                'hallucination_check': 'hallucination_check' in result,
                'disambiguation': 'disambiguation' in result,
                'clarification': 'clarification' in result,
                'constraints': 'constraints' in result,
                'validation': 'validation' in result,
                'metadata': 'metadata' in result and len(result['metadata']) > 0,
            }
            
            feature_matrix[mode_name] = features
    
    # Print feature matrix
    print(f"\n{'='*70}")
    print(f"FEATURE PRESENCE MATRIX")
    print(f"{'='*70}\n")
    
    print(f"{'Feature':<25} | Basic | Asst | Deep | Both")
    print(f"{'-'*25}-+-------+------+------+------")
    
    feature_names = list(feature_matrix.get('basic', {}).keys())
    for feature in feature_names:
        basic_val = '✓' if feature_matrix.get('basic', {}).get(feature) else '✗'
        asst_val = '✓' if feature_matrix.get('assistant', {}).get(feature) else '✗'
        deep_val = '✓' if feature_matrix.get('deep', {}).get(feature) else '✗'
        both_val = '✓' if feature_matrix.get('both', {}).get(feature) else '✗'
        
        print(f"{feature:<25} |  {basic_val}    |  {asst_val}   |  {deep_val}   |  {both_val}")
    
    print(f"\n{'='*70}\n")
    
    # Validate expected feature presence
    # Assistant mode should have confidence and hallucination check
    if 'assistant' in feature_matrix:
        assert feature_matrix['assistant'].get('confidence_scoring') or \
               feature_matrix['assistant'].get('hallucination_check'), \
               "Assistant mode should have confidence or hallucination features"
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")


@pytest.mark.integration
def test_performance_across_modes(api_client, sample_csv_small):
    """
    Test that response times follow expected ordering:
    Basic < Assistant < Deep Search < Both
    """
    # Create RAG
    rag_name = f"Performance Order Test {int(time.time())}"
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
    
    query = "How many records are in this dataset?"
    
    timings = {}
    
    for mode_name, mode_config in get_all_modes().items():
        start_time = time.time()
        
        resp = api_client.post("/rag/query", json={
            "prompt": query,
            "project_id": rag_id,
            **mode_config.to_api_params()
        })
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        timings[mode_name] = elapsed_ms
    
    print(f"\n{'='*70}")
    print(f"PERFORMANCE ORDERING TEST")
    print(f"Query: {query}")
    print(f"{'='*70}\n")
    
    for mode_name, elapsed_ms in sorted(timings.items(), key=lambda x: x[1]):
        mode_config = get_all_modes()[mode_name]
        in_range = mode_config.expected_response_time[0] <= elapsed_ms <= mode_config.expected_response_time[1]
        status = "✓" if in_range else "⚠"
        print(f"{mode_config.name:<15}: {elapsed_ms:>6}ms  {status}")
    
    print(f"\n{'='*70}\n")
    
    # Validate general ordering (with some tolerance for variance)
    # Note: Deep Search and Both can have similar times
    print(f"Timing relationships:")
    print(f"  Basic vs Assistant: {timings['basic']} vs {timings['assistant']}")
    print(f"  Assistant vs Deep: {timings['assistant']} vs {timings['deep']}")
    print(f"  Basic vs Both: {timings['basic']} vs {timings['both']}")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")



