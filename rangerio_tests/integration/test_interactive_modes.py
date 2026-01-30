"""
Interactive Mode Testing

Extends interactive validation to include mode testing:
1. Mode selector in HTML report
2. Mode-specific validation questions
3. Side-by-side mode comparison
"""
import pytest
import time
from pathlib import Path
from rangerio_tests.utils.mode_config import get_all_modes


@pytest.mark.interactive
def test_interactive_mode_comparison(api_client, sample_csv_small, interactive_validator):
    """
    Interactive test comparing the same queries across all modes.
    Generates HTML report with side-by-side mode comparisons for human validation.
    """
    # Create RAG
    rag_name = f"Interactive Mode Test {int(time.time())}"
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
    
    # Test queries for mode comparison
    comparison_queries = [
        "How many records are in this dataset?",
        "What is the date range of this data?",
        "Analyze this dataset",
    ]
    
    print(f"\n{'='*70}")
    print(f"INTERACTIVE MODE COMPARISON")
    print(f"Generating HTML report with side-by-side mode comparisons")
    print(f"{'='*70}\n")
    
    for query in comparison_queries:
        mode_results = {}
        
        # Run query across all modes
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
                mode_results[mode_name] = {
                    'mode_config': mode_config,
                    'response_time_ms': elapsed_ms,
                    'answer': result.get('answer', ''),
                    'confidence': result.get('confidence'),
                    'hallucination_check': result.get('hallucination_check'),
                    'clarification': result.get('clarification'),
                    'sources': result.get('sources', []),
                }
        
        # Display for interactive validation using existing method
        # but add mode metadata
        for mode_name, result in mode_results.items():
            mode_config = result['mode_config']
            
            # Add to HTML report with mode information
            source_texts = [s.get('document', s.get('text', '')) for s in result['sources'] if s]
            
            interactive_validator.display_rag_answer(
                question=f"[{mode_config.name} Mode] {query}",
                answer=result['answer'],
                contexts=source_texts,
                metadata={
                    'mode': mode_name,
                    'mode_name': mode_config.name,
                    'assistant_mode': mode_config.assistant_mode,
                    'deep_search_mode': mode_config.deep_search_mode,
                    'response_time_ms': result['response_time_ms'],
                    'confidence': result.get('confidence'),
                    'hallucination_check': result.get('hallucination_check'),
                }
            )
    
    # Generate HTML report
    report_file = interactive_validator.generate_html_report()
    
    print(f"\n{'='*70}")
    print(f"✅ INTERACTIVE MODE COMPARISON REPORT GENERATED")
    print(f"{'='*70}")
    print(f"\n📂 File Location:")
    print(f"   {report_file}")
    print(f"\n🌐 Clickable Link:")
    print(f"   file://{report_file}")
    print(f"\n📊 Report Contains:")
    print(f"   • {len(comparison_queries)} queries")
    print(f"   • {len(get_all_modes())} modes per query")
    print(f"   • Side-by-side comparison")
    print(f"   • Mode metadata (confidence, hallucination checks)")
    print(f"\n💡 Instructions:")
    print(f"   1. Open the HTML report in your browser")
    print(f"   2. Compare answers across modes")
    print(f"   3. Rate which mode performed best for each query")
    print(f"   4. Add notes explaining your choice")
    print(f"   5. Export results when complete")
    print(f"{'='*70}\n")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")
    
    assert report_file.exists(), "HTML report should be generated"


@pytest.mark.interactive
def test_interactive_assistant_features(api_client, sample_csv_small, interactive_validator):
    """
    Interactive test focused on Assistant mode features.
    Validates clarification, confidence scoring, and constraints with human feedback.
    """
    # Create RAG
    rag_name = f"Interactive Assistant Test {int(time.time())}"
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
    
    assistant_mode = get_all_modes()['assistant']
    
    # Queries testing different Assistant features
    test_cases = [
        {
            "query": "analyze this data",
            "feature": "clarification",
            "expected": "Should trigger clarification request"
        },
        {
            "query": "Summarize in 20 words",
            "feature": "constraint_parsing",
            "expected": "Should detect and enforce word limit"
        },
        {
            "query": "What is the date range?",
            "feature": "hallucination_detection",
            "expected": "Should detect potential hallucination"
        },
    ]
    
    print(f"\n{'='*70}")
    print(f"INTERACTIVE ASSISTANT FEATURES TEST")
    print(f"{'='*70}\n")
    
    for test_case in test_cases:
        query = test_case["query"]
        feature = test_case["feature"]
        expected = test_case["expected"]
        
        resp = api_client.post("/rag/query", json={
            "prompt": query,
            "project_id": rag_id,
            **assistant_mode.to_api_params()
        })
        
        if resp.status_code == 200:
            result = resp.json()
            
            # Display with feature-specific metadata
            source_texts = [s.get('document', s.get('text', '')) for s in result.get('sources', []) if s]
            
            interactive_validator.display_rag_answer(
                question=f"[Assistant - {feature}] {query}",
                answer=result.get('answer', ''),
                contexts=source_texts,
                metadata={
                    'mode': 'assistant',
                    'feature_tested': feature,
                    'expected_behavior': expected,
                    'confidence': result.get('confidence'),
                    'hallucination_check': result.get('hallucination_check'),
                    'clarification': result.get('clarification'),
                    'constraints': result.get('constraints'),
                    'disambiguation': result.get('disambiguation'),
                }
            )
    
    # Generate report
    report_file = interactive_validator.generate_html_report()
    
    print(f"\n{'='*70}")
    print(f"✅ ASSISTANT FEATURES REPORT GENERATED")
    print(f"{'='*70}")
    print(f"\nfile://{report_file}")
    print(f"\nValidate:")
    print(f"  • Was clarification helpful for ambiguous queries?")
    print(f"  • Were constraints properly enforced?")
    print(f"  • Was hallucination detection accurate?")
    print(f"  • Were confidence scores reasonable?")
    print(f"{'='*70}\n")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")


@pytest.mark.interactive
def test_interactive_deep_search_features(api_client, sample_csv_small, interactive_validator):
    """
    Interactive test focused on Deep Search mode features.
    Validates compound queries, query validation, and thorough analysis.
    """
    # Create RAG
    rag_name = f"Interactive Deep Search Test {int(time.time())}"
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
    
    deep_search_mode = get_all_modes()['deep']
    
    # Queries testing Deep Search features
    test_cases = [
        {
            "query": "What is the average age AND maximum salary?",
            "feature": "compound_query",
            "expected": "Should decompose into sub-queries and aggregate"
        },
        {
            "query": "Give me a comprehensive overview",
            "feature": "hierarchical_rag",
            "expected": "Should use hierarchical retrieval"
        },
    ]
    
    print(f"\n{'='*70}")
    print(f"INTERACTIVE DEEP SEARCH FEATURES TEST")
    print(f"{'='*70}\n")
    
    for test_case in test_cases:
        query = test_case["query"]
        feature = test_case["feature"]
        expected = test_case["expected"]
        
        resp = api_client.post("/rag/query", json={
            "prompt": query,
            "project_id": rag_id,
            **deep_search_mode.to_api_params()
        })
        
        if resp.status_code == 200:
            result = resp.json()
            
            source_texts = [s.get('document', s.get('text', '')) for s in result.get('sources', []) if s]
            
            interactive_validator.display_rag_answer(
                question=f"[Deep Search - {feature}] {query}",
                answer=result.get('answer', ''),
                contexts=source_texts,
                metadata={
                    'mode': 'deep_search',
                    'feature_tested': feature,
                    'expected_behavior': expected,
                    'strategy': result.get('metadata', {}).get('strategy'),
                    'compound_info': result.get('metadata', {}).get('compound_query'),
                    'validation': result.get('validation'),
                }
            )
    
    # Generate report
    report_file = interactive_validator.generate_html_report()
    
    print(f"\n{'='*70}")
    print(f"✅ DEEP SEARCH FEATURES REPORT GENERATED")
    print(f"{'='*70}")
    print(f"\nfile://{report_file}")
    print(f"\nValidate:")
    print(f"  • Were compound queries properly decomposed?")
    print(f"  • Was the analysis thorough and accurate?")
    print(f"  • Did query validation improve suggestion quality?")
    print(f"{'='*70}\n")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")








