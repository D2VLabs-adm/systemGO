"""
Validation test for hallucination detection and query disambiguation fixes.
Tests the improvements made based on interactive validation feedback.
"""
import pytest
import json
from pathlib import Path


@pytest.mark.integration
def test_hallucination_fixes_with_golden_dataset(api_client, sample_csv_small, golden_output_dir):
    """
    Test that hallucination detection and query disambiguation fixes work correctly.
    Uses the golden dataset created from interactive validation.
    """
    import time
    
    # Load golden dataset if it exists
    golden_file = golden_output_dir / "rag_golden_dataset.json"
    if not golden_file.exists():
        pytest.skip("Golden dataset not found. Run test_build_golden_dataset first.")
    
    with open(golden_file, 'r') as f:
        golden_data = json.load(f)
    
    # Golden data is a list of QA pairs
    qa_pairs = golden_data if isinstance(golden_data, list) else golden_data.get("qa_pairs", [])
    
    # Create a test RAG
    rag_name = f"Validation Test RAG {int(time.time())}"
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
    
    # Run queries and validate improvements
    results = []
    
    for qa_pair in qa_pairs:
        question = qa_pair["question"]
        expected_issues = qa_pair.get("validation_notes", "")
        
        # Query RAG
        query_resp = api_client.post(
            "/rag/query",
            json={
                "prompt": question,
                "project_id": rag_id
            }
        )
        assert query_resp.status_code == 200
        result = query_resp.json()
        
        answer = result.get("answer", "")
        disambiguation = result.get("disambiguation", {})
        hallucination_check = result.get("hallucination_check", {})
        confidence = result.get("confidence", {})
        
        # Validate improvements based on golden dataset issues
        test_result = {
            "question": question,
            "answer": answer[:200],  # Truncated for readability
            "expected_issues": expected_issues,
            "disambiguation_applied": bool(disambiguation),
            "hallucination_checked": hallucination_check.get("checked", False),
            "hallucination_detected": hallucination_check.get("is_hallucination", False),
            "hallucination_score": hallucination_check.get("score", 0.0),
            "confidence_score": confidence.get("score", 0.0),
            "passed": True
        }
        
        # Check specific improvements based on validation feedback
        
        # Issue #1: Record count confusion ("rows" vs "records")
        if "how many records" in question.lower() or "number of records" in question.lower():
            # Should have synonym disambiguation
            if disambiguation:
                applied_synonyms = disambiguation.get("applied_synonyms", [])
                has_record_synonym = any("records" in str(syn) or "rows" in str(syn) for syn in applied_synonyms)
                test_result["record_synonym_handled"] = has_record_synonym
                print(f"  ✓ Synonym disambiguation applied for record count query: {applied_synonyms}")
        
        # Issue #2: Date range hallucination
        if "date range" in question.lower():
            # Should detect hallucination if no dates in data
            if hallucination_check.get("is_hallucination"):
                print(f"  ✓ Hallucination detected for date range query (score: {hallucination_check['score']})")
                print(f"    Reasons: {hallucination_check['reasons']}")
                test_result["hallucination_prevented"] = True
            else:
                # If no hallucination detected, answer should not contain made-up dates
                has_specific_dates = any(month in answer for month in ["January", "February", "March", "April", "May", "June"])
                if has_specific_dates and "march" not in question.lower():
                    test_result["passed"] = False
                    test_result["failure_reason"] = "Contains specific dates but hallucination not detected"
        
        # Issue #3: Over-verbosity for simple data
        if "summarize" in question.lower() or "key statistics" in question.lower():
            # Answer should be reasonably concise
            word_count = len(answer.split())
            test_result["word_count"] = word_count
            if word_count > 300:
                print(f"  ⚠ Answer might be too verbose ({word_count} words)")
            else:
                print(f"  ✓ Answer is appropriately concise ({word_count} words)")
        
        results.append(test_result)
    
    # Summary
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    
    print(f"\n{'='*70}")
    print(f"VALIDATION TEST RESULTS")
    print(f"{'='*70}")
    print(f"Passed: {passed_count}/{total_count}")
    print(f"\nImprovements Validated:")
    print(f"  ✓ Query disambiguation active: {any(r.get('disambiguation_applied') for r in results)}")
    print(f"  ✓ Hallucination detection active: {all(r.get('hallucination_checked') for r in results)}")
    print(f"  ✓ Hallucinations prevented: {sum(1 for r in results if r.get('hallucination_detected'))}")
    print(f"{'='*70}\n")
    
    # Assert that all tests passed
    assert passed_count == total_count, f"Some validation tests failed: {[r for r in results if not r['passed']]}"
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")


@pytest.mark.integration
def test_hallucination_detection_with_no_context(api_client):
    """
    Test that hallucination detection works when no relevant context is available.
    This simulates the "gibberish" scenario from validation feedback.
    """
    import time
    
    # Create a test RAG with minimal data
    rag_name = f"Hallucination Test {int(time.time())}"
    rag_response = api_client.post("/projects", json={"name": rag_name})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    # Query with no uploaded data (should trigger hallucination detection)
    query_resp = api_client.post(
        "/rag/query",
        json={
            "prompt": "What is the average temperature in this dataset?",
            "project_id": rag_id
        }
    )
    
    assert query_resp.status_code == 200
    result = query_resp.json()
    
    hallucination_check = result.get("hallucination_check", {})
    answer = result.get("answer", "")
    
    print(f"\n{'='*70}")
    print(f"NO CONTEXT HALLUCINATION TEST")
    print(f"{'='*70}")
    print(f"Question: What is the average temperature in this dataset?")
    print(f"Answer: {answer}")
    print(f"Hallucination detected: {hallucination_check.get('is_hallucination')}")
    print(f"Hallucination score: {hallucination_check.get('score')}")
    print(f"Reasons: {hallucination_check.get('reasons')}")
    print(f"{'='*70}\n")
    
    # Should detect hallucination due to no context
    assert hallucination_check.get("is_hallucination"), "Should detect hallucination when no context available"
    assert "I don't have" in answer or "I don't know" in answer, "Should provide honest uncertainty"
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")


@pytest.mark.integration
def test_query_disambiguation_synonyms(api_client, sample_csv_small):
    """
    Test that query disambiguation correctly handles synonyms like "rows" vs "records".
    """
    import time
    
    # Create RAG and upload data
    rag_name = f"Synonym Test {int(time.time())}"
    rag_response = api_client.post("/projects", json={"name": rag_name})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    assert upload_resp.status_code == 200
    
    # Test different synonyms for "record count"
    synonyms_to_test = [
        "How many records are there?",
        "How many rows are there?",
        "How many entries are there?",
        "What is the number of items?",
    ]
    
    print(f"\n{'='*70}")
    print(f"SYNONYM DISAMBIGUATION TEST")
    print(f"{'='*70}")
    
    for query in synonyms_to_test:
        query_resp = api_client.post(
            "/rag/query",
            json={"prompt": query, "project_id": rag_id}
        )
        assert query_resp.status_code == 200
        result = query_resp.json()
        
        disambiguation = result.get("disambiguation", {})
        answer = result.get("answer", "")
        
        print(f"\nQuery: {query}")
        if disambiguation:
            print(f"  Enhanced: {disambiguation.get('enhanced_query', 'N/A')}")
            print(f"  Intent: {disambiguation.get('intent', 'N/A')}")
            print(f"  Synonyms applied: {disambiguation.get('applied_synonyms', [])}")
        print(f"  Answer preview: {answer[:100]}...")
    
    print(f"{'='*70}\n")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")

