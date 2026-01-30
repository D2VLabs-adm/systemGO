"""
Interactive Mode Accuracy Testing

Generates side-by-side comparison of all 4 modes for the same query,
allowing human evaluation of answer quality, clarity, and usefulness.
"""
import pytest
import time
from typing import Dict, List
from rangerio_tests.utils.mode_config import get_all_modes


@pytest.mark.integration
@pytest.mark.interactive
def test_interactive_mode_accuracy_comparison(api_client, sample_csv_small, interactive_validator):
    """
    Compare all 4 modes side-by-side for human accuracy rating.
    
    For each test query:
    1. Run query in all 4 modes (Basic, Assistant, Deep Search, Both)
    2. Display all 4 answers side-by-side in HTML
    3. User rates accuracy (1-5 stars) and adds notes
    4. Results saved to benchmark DB
    """
    # Create RAG
    rag_name = f"Accuracy Test {int(time.time())}"
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
    
    # Test queries covering different scenarios
    test_queries = [
        {
            "query": "How many records are in this dataset?",
            "type": "factual",
            "expected_answer": "~1000 records"
        },
        {
            "query": "What are the key characteristics of this dataset?",
            "type": "analytical",
            "expected_answer": "Summary of columns, data types, patterns"
        },
        {
            "query": "analyze this data",
            "type": "ambiguous",
            "expected_answer": "Should request clarification in Assistant/Both modes"
        },
        {
            "query": "What is the average value and maximum value?",
            "type": "compound",
            "expected_answer": "Two separate calculations"
        },
        {
            "query": "What is the date range of this data?",
            "type": "hallucination_risk",
            "expected_answer": "Should say 'I don't know' if no dates present"
        }
    ]
    
    print(f"\n{'='*80}")
    print(f"INTERACTIVE MODE ACCURACY COMPARISON")
    print(f"Please rate the quality of each mode's answer (1-5 stars)")
    print(f"{'='*80}\n")
    
    for query_info in test_queries:
        query = query_info["query"]
        query_type = query_info["type"]
        
        print(f"\n{'─'*80}")
        print(f"Query: {query}")
        print(f"Type: {query_type}")
        print(f"Expected: {query_info['expected_answer']}")
        print(f"{'─'*80}\n")
        
        # Run query in all 4 modes (WITH 10-SECOND DELAY BETWEEN QUERIES)
        mode_results = {}
        
        for mode_name, mode_config in get_all_modes().items():
            # Throttle: 10-second delay between queries to prevent memory spikes
            if mode_results:  # Skip delay for first query
                print(f"  ⏳ Throttling: 10-second delay before next mode...")
                time.sleep(10)
            
            start_time = time.time()
            
            resp = api_client.post("/rag/query", json={
                "prompt": query,
                "project_id": rag_id,
                **mode_config.to_api_params()
            })
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            if resp.status_code == 200:
                result = resp.json()
                
                mode_results[mode_name] = {
                    'mode_config': mode_config,
                    'response_time_ms': elapsed_ms,
                    'answer': result.get('answer', ''),
                    'confidence': result.get('confidence', {}),
                    'clarification': result.get('clarification'),
                    'validation': result.get('validation'),
                    'metadata': result.get('metadata', {}),
                    'hallucination_check': result.get('hallucination_check', {}),
                    'sources': len(result.get('sources', []))
                }
                
                # Print to terminal for monitoring
                print(f"{mode_config.name} Mode ({elapsed_ms}ms):")
                print(f"  Answer: {result.get('answer', '')[:100]}...")
                print(f"  Confidence: {result.get('confidence', {}).get('score', 'N/A')}")
                if result.get('clarification'):
                    print(f"  Clarification: {result['clarification'].get('needed', False)}")
                if result.get('validation'):
                    print(f"  Validation: {result['validation'].get('status', 'N/A')}")
                print()
        
        # Add to interactive validator for HTML display
        interactive_validator.display_mode_comparison(
            query=query,
            query_type=query_type,
            expected_answer=query_info['expected_answer'],
            mode_results=mode_results
        )
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")
    
    # Generate HTML report
    report_path = interactive_validator.generate_html_report()
    print(f"\n{'='*80}")
    print(f"✅ Interactive Accuracy Testing Complete!")
    print(f"📊 HTML Report: file://{report_path}")
    print(f"{'='*80}\n")
    print(f"Please open the HTML report to rate answer accuracy.")
    print(f"After rating, export results and place JSON in the test directory.")
    print(f"\n")
    
    return report_path

