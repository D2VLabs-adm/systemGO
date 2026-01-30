"""
Interactive RAG validation tests - requires human review
Run with: pytest -m interactive

These tests display RAG answers for human validation to:
1. Catch hallucinations
2. Verify accuracy of charts/visualizations
3. Build golden dataset of validated answers
"""
import pytest
import json
import time
from pathlib import Path


@pytest.mark.interactive
@pytest.mark.slow
def test_interactive_rag_factual_answers(api_client, interactive_validator, sample_csv_small):
    """
    Interactive validation of factual RAG answers
    Human reviews each answer for accuracy and hallucinations
    """
    # Create a RAG project
    rag_response = api_client.post("/projects", json={"name": (f"Interactive Test RAG {int(time.time())}"), "description": "Interactive testing"})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    # Upload sample data
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={"project_id": rag_id, "source_type": "file"}
    )
    assert upload_resp.status_code == 200
    datasource_id = upload_resp.json()["id"]
    
    # Test questions that require factual answers
    test_questions = [
        {
            "question": "How many rows are in the dataset?",
            "expected_type": "numeric",
            "category": "dataset_info"
        },
        {
            "question": "What are the column names in this dataset?",
            "expected_type": "list",
            "category": "dataset_info"
        },
        {
            "question": "What is the average age of customers?",
            "expected_type": "numeric",
            "category": "aggregation"
        },
        {
            "question": "Which region has the highest sales?",
            "expected_type": "categorical",
            "category": "comparison"
        },
        {
            "question": "Summarize the key insights from this data",
            "expected_type": "narrative",
            "category": "summary"
        }
    ]
    
    results = []
    for test_case in test_questions:
        # Get RAG answer
        query_resp = api_client.post(
            "/rag/query",
            json={
                "prompt": test_case["question"],
                "project_id": rag_id
            }
        )
        assert query_resp.status_code == 200
        result = query_resp.json()
        answer = result.get("answer", "")
        contexts = result.get("sources", [])
        
        # Display for human validation
        validation = interactive_validator.display_rag_answer(
            question=test_case["question"],
            answer=answer,
            contexts=contexts,
            metadata={
                "expected_type": test_case["expected_type"],
                "category": test_case["category"],
                "datasource_id": datasource_id
            }
        )
        
        results.append({
            "question": test_case["question"],
            "answer": answer,
            "contexts": contexts,
            "validation": validation,
            "category": test_case["category"]
        })
    
    # Save validated results for golden dataset
    interactive_validator.save_validated_data(
        results,
        filename="rag_factual_answers_validated.json"
    )
    
    # Assert that at least 80% passed human validation
    passed = sum(1 for r in results if r["validation"]["is_accurate"])
    assert passed >= len(results) * 0.8, f"Only {passed}/{len(results)} answers validated as accurate"
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")


@pytest.mark.interactive
@pytest.mark.slow
def test_interactive_chart_validation(api_client, interactive_validator, sample_csv_small):
    """
    Interactive validation of PandasAI-generated charts
    Human reviews each chart for accuracy and proper visualization
    """
    # Create RAG and upload data
    rag_response = api_client.post("/projects", json={"name": (f"Chart Test RAG {int(time.time())}")})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={"project_id": rag_id, "source_type": "file"}
    )
    assert upload_resp.status_code == 200
    datasource_id = upload_resp.json()["id"]
    
    # Test chart generation requests
    chart_requests = [
        {
            "prompt": "Create a bar chart showing sales by region",
            "expected_chart_type": "bar"
        },
        {
            "prompt": "Show a pie chart of product category distribution",
            "expected_chart_type": "pie"
        },
        {
            "prompt": "Plot a line chart of sales over time",
            "expected_chart_type": "line"
        }
    ]
    
    results = []
    for request in chart_requests:
        # Request chart via PandasAI
        chart_resp = api_client.post(
            "/pandasai/chart",
            json={
                "datasource_id": datasource_id,
                "prompt": request["prompt"]
            }
        )
        
        if chart_resp.status_code == 200:
            chart_data = chart_resp.json()
            chart_path = chart_data.get("chart_path")
            
            # Display chart for human validation
            validation = interactive_validator.display_chart(
                chart_path=chart_path,
                prompt=request["prompt"],
                metadata={"expected_type": request["expected_chart_type"]}
            )
            
            results.append({
                "prompt": request["prompt"],
                "chart_path": chart_path,
                "validation": validation
            })
        else:
            print(f"Chart generation failed for: {request['prompt']}")
    
    # Save validated charts
    interactive_validator.save_validated_data(
        results,
        filename="chart_validation_results.json"
    )
    
    # Assert at least 2/3 charts validated correctly
    passed = sum(1 for r in results if r["validation"]["is_accurate"])
    assert passed >= len(results) * 0.67, f"Only {passed}/{len(results)} charts validated as accurate"
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")


@pytest.mark.interactive
def test_interactive_prompt_comparison(api_client, interactive_validator, sample_csv_small):
    """
    Interactive comparison of different prompts for same question
    Helps identify which prompts produce better results
    """
    # Create RAG
    rag_response = api_client.post("/projects", json={"name": (f"Prompt Compare RAG {int(time.time())}")})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={"project_id": rag_id, "source_type": "file"}
    )
    assert upload_resp.status_code == 200
    
    # Test same question with different prompt formulations
    question_base = "What are the key patterns in the sales data?"
    
    prompt_variations = [
        {
            "prompt": question_base,
            "style": "direct"
        },
        {
            "prompt": f"As a data analyst, {question_base.lower()}",
            "style": "role_based"
        },
        {
            "prompt": f"{question_base} Please provide specific numbers and trends.",
            "style": "detailed_request"
        },
        {
            "prompt": f"Analyze the sales data and identify: 1) Top trends, 2) Anomalies, 3) Recommendations",
            "style": "structured"
        }
    ]
    
    answers = []
    for variation in prompt_variations:
        resp = api_client.post(
            "/rag/query",
            json={
                "prompt": variation["prompt"],
                "project_id": rag_id,
                "model_name": "qwen3-4b-q4-k-m"
            }
        )
        assert resp.status_code == 200
        answers.append({
            "prompt": variation["prompt"],
            "style": variation["style"],
            "answer": resp.json()["response"]
        })
    
    # Display side-by-side comparison
    validation = interactive_validator.display_prompt_comparison(
        question=question_base,
        answers=answers
    )
    
    # Save results
    interactive_validator.save_validated_data(
        {"question": question_base, "answers": answers, "validation": validation},
        filename="prompt_comparison_results.json"
    )
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")


@pytest.mark.interactive
@pytest.mark.slow
def test_interactive_hallucination_detection(api_client, interactive_validator, sample_csv_small):
    """
    Interactive test specifically for detecting hallucinations
    Uses edge case questions that LLMs might fabricate answers for
    """
    # Create RAG
    rag_response = api_client.post("/projects", json={"name": (f"Hallucination Test RAG {int(time.time())}")})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={"project_id": rag_id, "source_type": "file"}
    )
    assert upload_resp.status_code == 200
    datasource_id = upload_resp.json()["id"]
    
    # Questions designed to trigger potential hallucinations
    edge_questions = [
        {
            "question": "What is the correlation between customer satisfaction and product returns?",
            "note": "May not have satisfaction data"
        },
        {
            "question": "Which customers are likely to churn next month?",
            "note": "Predictive question without ML model"
        },
        {
            "question": "What was the exact ROI of the Q4 marketing campaign?",
            "note": "May not have campaign tracking data"
        },
        {
            "question": "Compare our sales to industry competitors",
            "note": "External data not in dataset"
        }
    ]
    
    results = []
    for test in edge_questions:
        resp = api_client.post(
            "/rag/query",
            json={
                "prompt": test["question"],
                "project_id": rag_id,
                "model_name": "qwen3-4b-q4-k-m"
            }
        )
        assert resp.status_code == 200
        result = resp.json()
        answer = result.get("answer", "")
        contexts = result.get("sources", [])
        
        # Special validation focusing on hallucination detection
        validation = interactive_validator.display_rag_answer(
            question=test["question"],
            answer=answer,
            contexts=contexts,
            metadata={
                "hallucination_risk": "high",
                "note": test["note"]
            }
        )
        
        results.append({
            "question": test["question"],
            "answer": answer,
            "contexts": contexts,
            "validation": validation,
            "hallucination_risk": "high"
        })
    
    # Save hallucination test results
    interactive_validator.save_validated_data(
        results,
        filename="hallucination_detection_results.json"
    )
    
    # Check for proper "I don't know" responses vs fabrications
    proper_uncertainty = sum(
        1 for r in results 
        if any(phrase in r["answer"].lower() for phrase in [
            "don't have", "not available", "cannot determine", 
            "insufficient data", "not enough information"
        ])
    )
    
    print(f"\nHallucination Test Results:")
    print(f"  Questions with proper uncertainty: {proper_uncertainty}/{len(results)}")
    print(f"  Human-validated accurate: {sum(1 for r in results if r['validation']['is_accurate'])}/{len(results)}")
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")


@pytest.mark.interactive
def test_build_golden_dataset(api_client, interactive_validator, sample_csv_small, golden_output_dir):
    """
    Build golden dataset of validated Q&A pairs for future automated testing
    This is a special test that creates reference data
    """
    # Create RAG
    import time
    rag_name = f"Golden Dataset RAG {int(time.time())}"
    rag_response = api_client.post("/projects", json={"name": rag_name})
    assert rag_response.status_code == 200
    rag_id = rag_response.json()["id"]
    
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={"project_id": rag_id, "source_type": "file"}
    )
    assert upload_resp.status_code == 200
    
    # Core questions that should always work
    golden_questions = [
        "What columns are in this dataset?",
        "How many records are there?",
        "What is the date range of this data?",
        "Summarize the key statistics",
        "List the unique values in the category column"
    ]
    
    golden_dataset = []
    for question in golden_questions:
        resp = api_client.post(
            "/rag/query",
            json={
                "prompt": question,
                "project_id": rag_id,
                "model_name": "qwen3-4b-q4-k-m"
            }
        )
        assert resp.status_code == 200
        result = resp.json()
        answer = result.get("answer", "")
        contexts = result.get("sources", [])
        
        validation = interactive_validator.display_rag_answer(
            question=question,
            answer=answer,
            contexts=contexts,
            metadata={"dataset_type": "golden"}
        )
        
        if validation["is_accurate"]:
            golden_dataset.append({
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "validation_date": validation["timestamp"],
                "model": "qwen3-4b-q4-k-m"
            })
    
    # Save golden dataset
    golden_file = golden_output_dir / "rag_golden_dataset.json"
    with open(golden_file, 'w') as f:
        json.dump(golden_dataset, f, indent=2)
    
    print(f"\n✓ Golden dataset created: {len(golden_dataset)} validated Q&A pairs")
    print(f"  Saved to: {golden_file}")
    
    # Generate HTML report for human review
    report_file = interactive_validator.generate_html_report()
    assert report_file.exists(), "HTML report should be generated"
    
    assert len(golden_dataset) >= 3, "Need at least 3 validated Q&A pairs for golden dataset"
    
    # Cleanup
    api_client.delete(f"/projects/{rag_id}")

