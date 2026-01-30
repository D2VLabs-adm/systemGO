"""
Comprehensive Sales Analysis - 10 Varied Test Queries

Tests different query types, complexities, and expected answer formats.
Provides diverse evaluation of RangerIO's capabilities.
"""
import pytest
import pandas as pd
import time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.interactive
def test_query_01_simple_factual(
    api_client,
    sales_dataset,
    interactive_validator
):
    """
    Query 1: Simple Factual - SHORT ANSWER EXPECTED
    
    "What regions are included in the sales data?"
    
    Expected: Brief list (1-2 sentences)
    Tests: Basic data understanding, conciseness
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Simple Factual Query (Expected: SHORT)")
    logger.info("="*80)
    
    # Setup
    project_name = f"Sales Comprehensive {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]
    
    upload_response = api_client.upload_file(
        "/datasources/connect",
        sales_dataset,
        data={"project_id": project_id, "source_type": "file"}
    )
    assert upload_response.status_code == 200
    
    logger.info("⏳ Waiting for ingestion...")
    time.sleep(15)
    
    # Query
    question = "What regions are included in the sales data?"
    
    logger.info(f"\n📊 QUERY: {question}")
    
    rag_response = api_client.post(
        "/rag/query",
        json={
            "project_id": project_id,
            "prompt": question,
            "assistant_mode": True,
            "deep_search_mode": False
        }
    )
    
    assert rag_response.status_code == 200
    result = rag_response.json()
    
    answer = result.get("answer", "")
    contexts = result.get("sources", [])
    clarification = result.get("clarification", {})
    confidence = result.get("confidence", {})
    
    logger.info(f"\n✓ Answer length: {len(answer)} chars")
    logger.info(f"✓ Confidence: {confidence.get('score', 0):.2f}")
    
    validation = interactive_validator.display_query_with_refinement_feedback(
        question=question,
        answer=answer,
        contexts=contexts,
        metadata={
            'query_type': 'simple_factual',
            'complexity': 'low',
            'expected_answer_length': 'short (50-150 chars)',
            'expected_format': 'Brief list or sentence',
            'test_name': 'q01_simple_factual',
            'assistant_mode': True,
            'clarification': clarification,
            'confidence': confidence,
            'answer_length': len(answer),
            'expected_elements': [
                'List of 5 regions: North, South, East, West, Central',
                'Concise (1-2 sentences max)'
            ],
            'potential_issues': [
                'Too verbose (should be very brief)',
                'Made up extra regions',
                'Missing one or more regions',
                'Unnecessary explanation'
            ]
        }
    )
    
    assert len(contexts) > 0, "No context retrieved"
    logger.info("✓ Test 1 completed")


@pytest.mark.integration
@pytest.mark.interactive
def test_query_02_aggregation(
    api_client,
    sales_dataset,
    interactive_validator
):
    """
    Query 2: Aggregation - MEDIUM LENGTH EXPECTED
    
    "What is the total revenue and average profit margin by region in 2023?"
    
    Expected: Table or structured list (3-5 sentences)
    Tests: Aggregation, numerical accuracy, year filtering
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Aggregation Query (Expected: MEDIUM)")
    logger.info("="*80)
    
    # Setup (reuse existing project to save time)
    project_name = f"Sales Comprehensive {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]
    
    upload_response = api_client.upload_file(
        "/datasources/connect",
        sales_dataset,
        data={"project_id": project_id, "source_type": "file"}
    )
    assert upload_response.status_code == 200
    
    logger.info("⏳ Waiting for ingestion...")
    time.sleep(15)
    
    question = "What is the total revenue and average profit margin by region in 2023?"
    
    logger.info(f"\n📊 QUERY: {question}")
    
    rag_response = api_client.post(
        "/rag/query",
        json={
            "project_id": project_id,
            "prompt": question,
            "assistant_mode": True,
            "deep_search_mode": False
        }
    )
    
    assert rag_response.status_code == 200
    result = rag_response.json()
    
    answer = result.get("answer", "")
    contexts = result.get("sources", [])
    confidence = result.get("confidence", {})
    
    logger.info(f"\n✓ Answer length: {len(answer)} chars")
    
    validation = interactive_validator.display_query_with_refinement_feedback(
        question=question,
        answer=answer,
        contexts=contexts,
        metadata={
            'query_type': 'aggregation',
            'complexity': 'medium',
            'expected_answer_length': 'medium (200-500 chars)',
            'expected_format': 'Table or structured list with numbers',
            'test_name': 'q02_aggregation',
            'answer_length': len(answer),
            'confidence': confidence,
            'expected_elements': [
                'Total revenue for each region (5 regions)',
                'Average profit margin % for each region',
                'Only 2023 data (filtered by year)',
                'Numerical values (not just text)'
            ],
            'potential_issues': [
                'Includes data from other years (not just 2023)',
                'Missing regions',
                'Hallucinated numbers',
                'Too verbose with unnecessary explanations',
                'No actual numbers provided'
            ]
        }
    )
    
    assert len(contexts) > 0
    logger.info("✓ Test 2 completed")


@pytest.mark.integration
@pytest.mark.interactive
def test_query_03_trend_analysis(
    api_client,
    sales_dataset,
    interactive_validator
):
    """
    Query 3: Trend Analysis - MEDIUM-LONG LENGTH EXPECTED
    
    "How has revenue trended across quarters from 2019 to 2023? 
    Which years showed growth vs decline?"
    
    Expected: Summary with trend description (5-8 sentences)
    Tests: Time-series analysis, growth calculation, multi-year comparison
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Trend Analysis (Expected: MEDIUM-LONG)")
    logger.info("="*80)
    
    project_name = f"Sales Comprehensive {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    project_id = project_response.json()["id"]
    
    upload_response = api_client.upload_file(
        "/datasources/connect",
        sales_dataset,
        data={"project_id": project_id, "source_type": "file"}
    )
    
    logger.info("⏳ Waiting for ingestion...")
    time.sleep(15)
    
    question = "How has revenue trended across quarters from 2019 to 2023? Which years showed growth vs decline?"
    
    logger.info(f"\n📊 QUERY: {question}")
    
    rag_response = api_client.post(
        "/rag/query",
        json={
            "project_id": project_id,
            "prompt": question,
            "assistant_mode": True,
            "deep_search_mode": False
        }
    )
    
    result = rag_response.json()
    answer = result.get("answer", "")
    contexts = result.get("sources", [])
    confidence = result.get("confidence", {})
    
    validation = interactive_validator.display_query_with_refinement_feedback(
        question=question,
        answer=answer,
        contexts=contexts,
        metadata={
            'query_type': 'trend_analysis',
            'complexity': 'high',
            'expected_answer_length': 'medium-long (400-800 chars)',
            'expected_format': 'Narrative with trend insights',
            'test_name': 'q03_trend_analysis',
            'answer_length': len(answer),
            'confidence': confidence,
            'expected_elements': [
                'Quarterly revenue trends',
                'Year-over-year comparison (2019-2023)',
                'Identification of growth years',
                'Identification of decline years',
                'Some numerical support for trends'
            ],
            'potential_issues': [
                'Only shows one or two years (not full 2019-2023)',
                'No actual trend (just lists numbers)',
                'Hallucinated growth/decline patterns',
                'Too much raw data without interpretation',
                'Too brief for complex trend analysis'
            ]
        }
    )
    
    logger.info("✓ Test 3 completed")


@pytest.mark.integration
@pytest.mark.interactive
def test_query_04_top_performers(
    api_client,
    sales_dataset,
    interactive_validator
):
    """
    Query 4: Ranking/Top-N - SHORT-MEDIUM LENGTH EXPECTED
    
    "Which are the top 3 best-selling products by revenue?"
    
    Expected: Ranked list with revenue figures (2-4 sentences)
    Tests: Sorting, top-N selection, concise formatting
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Top Performers (Expected: SHORT-MEDIUM)")
    logger.info("="*80)
    
    project_name = f"Sales Comprehensive {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    project_id = project_response.json()["id"]
    
    upload_response = api_client.upload_file(
        "/datasources/connect",
        sales_dataset,
        data={"project_id": project_id, "source_type": "file"}
    )
    
    logger.info("⏳ Waiting for ingestion...")
    time.sleep(15)
    
    question = "Which are the top 3 best-selling products by revenue?"
    
    logger.info(f"\n📊 QUERY: {question}")
    
    rag_response = api_client.post(
        "/rag/query",
        json={
            "project_id": project_id,
            "prompt": question,
            "assistant_mode": True,
            "deep_search_mode": False
        }
    )
    
    result = rag_response.json()
    answer = result.get("answer", "")
    contexts = result.get("sources", [])
    confidence = result.get("confidence", {})
    
    validation = interactive_validator.display_query_with_refinement_feedback(
        question=question,
        answer=answer,
        contexts=contexts,
        metadata={
            'query_type': 'ranking_top_n',
            'complexity': 'low',
            'expected_answer_length': 'short-medium (150-300 chars)',
            'expected_format': 'Ranked list (1, 2, 3) with revenue',
            'test_name': 'q04_top_performers',
            'answer_length': len(answer),
            'confidence': confidence,
            'expected_elements': [
                'Exactly 3 products listed',
                'Ranked in order (1st, 2nd, 3rd)',
                'Revenue figures for each',
                'Concise (no unnecessary details)'
            ],
            'potential_issues': [
                'More than 3 products listed',
                'Not ranked in order',
                'No revenue figures provided',
                'Made up product names',
                'Too verbose for simple ranking'
            ]
        }
    )
    
    logger.info("✓ Test 4 completed")


@pytest.mark.integration
@pytest.mark.interactive
def test_query_05_comparison(
    api_client,
    sales_dataset,
    interactive_validator
):
    """
    Query 5: Comparison - MEDIUM LENGTH EXPECTED
    
    "Compare the performance of North vs South regions in terms of 
    revenue, profit, and number of transactions."
    
    Expected: Side-by-side comparison (4-6 sentences)
    Tests: Multi-metric comparison, structured output
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Comparison Query (Expected: MEDIUM)")
    logger.info("="*80)
    
    project_name = f"Sales Comprehensive {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    project_id = project_response.json()["id"]
    
    upload_response = api_client.upload_file(
        "/datasources/connect",
        sales_dataset,
        data={"project_id": project_id, "source_type": "file"}
    )
    
    logger.info("⏳ Waiting for ingestion...")
    time.sleep(15)
    
    question = "Compare the performance of North vs South regions in terms of revenue, profit, and number of transactions."
    
    logger.info(f"\n📊 QUERY: {question}")
    
    rag_response = api_client.post(
        "/rag/query",
        json={
            "project_id": project_id,
            "prompt": question,
            "assistant_mode": True,
            "deep_search_mode": False
        }
    )
    
    result = rag_response.json()
    answer = result.get("answer", "")
    contexts = result.get("sources", [])
    confidence = result.get("confidence", {})
    
    validation = interactive_validator.display_query_with_refinement_feedback(
        question=question,
        answer=answer,
        contexts=contexts,
        metadata={
            'query_type': 'comparison',
            'complexity': 'medium',
            'expected_answer_length': 'medium (300-600 chars)',
            'expected_format': 'Structured comparison (North vs South for each metric)',
            'test_name': 'q05_comparison',
            'answer_length': len(answer),
            'confidence': confidence,
            'expected_elements': [
                'Revenue for North',
                'Revenue for South',
                'Profit for both regions',
                'Transaction count for both',
                'Clear comparison (which is higher/lower)'
            ],
            'potential_issues': [
                'Only provides one region data',
                'Missing one of the three metrics',
                'No actual comparison (just lists numbers)',
                'Includes other regions not asked for',
                'Hallucinated numbers'
            ]
        }
    )
    
    logger.info("✓ Test 5 completed")


@pytest.mark.integration
@pytest.mark.interactive
def test_query_06_filtering(
    api_client,
    sales_dataset,
    interactive_validator
):
    """
    Query 6: Multi-Criteria Filtering - MEDIUM LENGTH EXPECTED
    
    "Show transactions where profit margin is greater than 30% 
    and revenue exceeds $50,000."
    
    Expected: Filtered results summary (3-5 sentences)
    Tests: Complex filtering, threshold comparisons
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 6: Multi-Criteria Filtering (Expected: MEDIUM)")
    logger.info("="*80)
    
    project_name = f"Sales Comprehensive {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    project_id = project_response.json()["id"]
    
    upload_response = api_client.upload_file(
        "/datasources/connect",
        sales_dataset,
        data={"project_id": project_id, "source_type": "file"}
    )
    
    logger.info("⏳ Waiting for ingestion...")
    time.sleep(15)
    
    question = "Show transactions where profit margin is greater than 30% and revenue exceeds $50,000."
    
    logger.info(f"\n📊 QUERY: {question}")
    
    rag_response = api_client.post(
        "/rag/query",
        json={
            "project_id": project_id,
            "prompt": question,
            "assistant_mode": True,
            "deep_search_mode": False
        }
    )
    
    result = rag_response.json()
    answer = result.get("answer", "")
    contexts = result.get("sources", [])
    confidence = result.get("confidence", {})
    
    validation = interactive_validator.display_query_with_refinement_feedback(
        question=question,
        answer=answer,
        contexts=contexts,
        metadata={
            'query_type': 'multi_criteria_filter',
            'complexity': 'medium',
            'expected_answer_length': 'medium (250-500 chars)',
            'expected_format': 'Count + examples of filtered transactions',
            'test_name': 'q06_filtering',
            'answer_length': len(answer),
            'confidence': confidence,
            'expected_elements': [
                'Count of transactions meeting criteria',
                'Both filters applied (margin >30% AND revenue >$50K)',
                'Examples or summary of results',
                'Specific numbers'
            ],
            'potential_issues': [
                'Only one filter applied (not both)',
                'Wrong threshold values',
                'Just shows all data without filtering',
                'Hallucinated transaction counts',
                'Too verbose listing individual transactions'
            ]
        }
    )
    
    logger.info("✓ Test 6 completed")


@pytest.mark.integration
@pytest.mark.interactive
def test_query_07_statistical_summary(
    api_client,
    sales_dataset,
    interactive_validator
):
    """
    Query 7: Statistical Summary - MEDIUM LENGTH EXPECTED
    
    "What are the mean, median, and standard deviation of profit margins?"
    
    Expected: Statistical measures (2-3 sentences)
    Tests: Statistical calculations, precision
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 7: Statistical Summary (Expected: MEDIUM)")
    logger.info("="*80)
    
    project_name = f"Sales Comprehensive {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    project_id = project_response.json()["id"]
    
    upload_response = api_client.upload_file(
        "/datasources/connect",
        sales_dataset,
        data={"project_id": project_id, "source_type": "file"}
    )
    
    logger.info("⏳ Waiting for ingestion...")
    time.sleep(15)
    
    question = "What are the mean, median, and standard deviation of profit margins?"
    
    logger.info(f"\n📊 QUERY: {question}")
    
    rag_response = api_client.post(
        "/rag/query",
        json={
            "project_id": project_id,
            "prompt": question,
            "assistant_mode": True,
            "deep_search_mode": False
        }
    )
    
    result = rag_response.json()
    answer = result.get("answer", "")
    contexts = result.get("sources", [])
    confidence = result.get("confidence", {})
    
    validation = interactive_validator.display_query_with_refinement_feedback(
        question=question,
        answer=answer,
        contexts=contexts,
        metadata={
            'query_type': 'statistical_summary',
            'complexity': 'medium',
            'expected_answer_length': 'short-medium (150-300 chars)',
            'expected_format': 'Direct answers: Mean=X, Median=Y, StdDev=Z',
            'test_name': 'q07_statistical',
            'answer_length': len(answer),
            'confidence': confidence,
            'expected_elements': [
                'Mean (average) profit margin %',
                'Median profit margin %',
                'Standard deviation',
                'Numerical precision (decimals)',
                'Concise (no long explanations)'
            ],
            'potential_issues': [
                'Missing one or more statistics',
                'Wrong calculations',
                'No numerical values provided',
                'Too much explanation of what these stats mean',
                'Rounded too much (should show precision)'
            ]
        }
    )
    
    logger.info("✓ Test 7 completed")


@pytest.mark.integration
@pytest.mark.interactive
def test_query_08_anomaly_detection(
    api_client,
    sales_dataset,
    interactive_validator
):
    """
    Query 8: Anomaly/Outlier Detection - MEDIUM-LONG LENGTH EXPECTED
    
    "Identify any unusual or outlier transactions with extremely high 
    discounts (>20%) combined with low profit margins (<5%)."
    
    Expected: Analysis with examples (5-7 sentences)
    Tests: Pattern detection, business insight
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 8: Anomaly Detection (Expected: MEDIUM-LONG)")
    logger.info("="*80)
    
    project_name = f"Sales Comprehensive {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    project_id = project_response.json()["id"]
    
    upload_response = api_client.upload_file(
        "/datasources/connect",
        sales_dataset,
        data={"project_id": project_id, "source_type": "file"}
    )
    
    logger.info("⏳ Waiting for ingestion...")
    time.sleep(15)
    
    question = "Identify any unusual or outlier transactions with extremely high discounts (>20%) combined with low profit margins (<5%)."
    
    logger.info(f"\n📊 QUERY: {question}")
    
    rag_response = api_client.post(
        "/rag/query",
        json={
            "project_id": project_id,
            "prompt": question,
            "assistant_mode": True,
            "deep_search_mode": True  # Complex analysis
        }
    )
    
    result = rag_response.json()
    answer = result.get("answer", "")
    contexts = result.get("sources", [])
    confidence = result.get("confidence", {})
    
    validation = interactive_validator.display_query_with_refinement_feedback(
        question=question,
        answer=answer,
        contexts=contexts,
        metadata={
            'query_type': 'anomaly_detection',
            'complexity': 'high',
            'expected_answer_length': 'medium-long (400-700 chars)',
            'expected_format': 'Analysis + examples of outliers',
            'test_name': 'q08_anomaly',
            'answer_length': len(answer),
            'confidence': confidence,
            'expected_elements': [
                'Count of outlier transactions',
                'Both criteria applied (discount >20% AND margin <5%)',
                'Examples or patterns',
                'Business insight (why this matters)',
                'Specific numbers'
            ],
            'potential_issues': [
                'Only one criterion applied',
                'No examples provided',
                'Just lists transactions without analysis',
                'Missing business context',
                'Too brief for complex analysis'
            ]
        }
    )
    
    logger.info("✓ Test 8 completed")


@pytest.mark.integration
@pytest.mark.interactive
def test_query_09_business_recommendation(
    api_client,
    sales_dataset,
    interactive_validator
):
    """
    Query 9: Business Recommendation - LONG LENGTH EXPECTED
    
    "Based on the sales data, which product categories should we 
    focus on for Q1 2024 and why? Provide recommendations."
    
    Expected: Strategic analysis with recommendations (8-12 sentences)
    Tests: Insight generation, recommendation quality, reasoning
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 9: Business Recommendation (Expected: LONG)")
    logger.info("="*80)
    
    project_name = f"Sales Comprehensive {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    project_id = project_response.json()["id"]
    
    upload_response = api_client.upload_file(
        "/datasources/connect",
        sales_dataset,
        data={"project_id": project_id, "source_type": "file"}
    )
    
    logger.info("⏳ Waiting for ingestion...")
    time.sleep(15)
    
    question = "Based on the sales data, which product categories should we focus on for Q1 2024 and why? Provide recommendations."
    
    logger.info(f"\n📊 QUERY: {question}")
    
    rag_response = api_client.post(
        "/rag/query",
        json={
            "project_id": project_id,
            "prompt": question,
            "assistant_mode": True,
            "deep_search_mode": True
        }
    )
    
    result = rag_response.json()
    answer = result.get("answer", "")
    contexts = result.get("sources", [])
    confidence = result.get("confidence", {})
    
    validation = interactive_validator.display_query_with_refinement_feedback(
        question=question,
        answer=answer,
        contexts=contexts,
        metadata={
            'query_type': 'business_recommendation',
            'complexity': 'very_high',
            'expected_answer_length': 'long (600-1000 chars)',
            'expected_format': 'Strategic analysis with actionable recommendations',
            'test_name': 'q09_recommendation',
            'answer_length': len(answer),
            'confidence': confidence,
            'expected_elements': [
                'Recommended product categories (prioritized)',
                'Data-driven reasoning (revenue, profit, growth)',
                'Historical performance analysis',
                'Forward-looking insights',
                'Actionable recommendations',
                'Business justification'
            ],
            'potential_issues': [
                'No clear recommendations (just describes data)',
                'Recommendations not based on data',
                'Missing justification/reasoning',
                'Too brief for strategic analysis',
                'Too verbose without clear action items',
                'Generic advice not specific to the data'
            ]
        }
    )
    
    logger.info("✓ Test 9 completed")


@pytest.mark.integration
@pytest.mark.interactive
def test_query_10_data_quality_check(
    api_client,
    sales_dataset,
    interactive_validator
):
    """
    Query 10: Data Quality Assessment - SHORT-MEDIUM LENGTH EXPECTED
    
    "Are there any data quality issues in the sales data, such as 
    missing values or inconsistencies?"
    
    Expected: Summary of data quality (3-5 sentences)
    Tests: Data profiling, quality assessment
    """
    logger.info("\n" + "="*80)
    logger.info("TEST 10: Data Quality Check (Expected: SHORT-MEDIUM)")
    logger.info("="*80)
    
    project_name = f"Sales Comprehensive {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    project_id = project_response.json()["id"]
    
    upload_response = api_client.upload_file(
        "/datasources/connect",
        sales_dataset,
        data={"project_id": project_id, "source_type": "file"}
    )
    
    logger.info("⏳ Waiting for ingestion...")
    time.sleep(15)
    
    question = "Are there any data quality issues in the sales data, such as missing values or inconsistencies?"
    
    logger.info(f"\n📊 QUERY: {question}")
    
    rag_response = api_client.post(
        "/rag/query",
        json={
            "project_id": project_id,
            "prompt": question,
            "assistant_mode": True,
            "deep_search_mode": False
        }
    )
    
    result = rag_response.json()
    answer = result.get("answer", "")
    contexts = result.get("sources", [])
    confidence = result.get("confidence", {})
    
    validation = interactive_validator.display_query_with_refinement_feedback(
        question=question,
        answer=answer,
        contexts=contexts,
        metadata={
            'query_type': 'data_quality',
            'complexity': 'medium',
            'expected_answer_length': 'short-medium (200-400 chars)',
            'expected_format': 'Summary of quality issues found',
            'test_name': 'q10_data_quality',
            'answer_length': len(answer),
            'confidence': confidence,
            'expected_elements': [
                'Missing values identified (columns with nulls)',
                'Percentage or count of missing data',
                'Any inconsistencies noted',
                'Overall data quality assessment',
                'Specific columns mentioned'
            ],
            'potential_issues': [
                'Says "no issues" when there are 20% nulls in data',
                'Too vague (no specific columns mentioned)',
                'Hallucinated issues that don\'t exist',
                'Too technical/verbose',
                'Doesn\'t actually check for quality issues'
            ]
        }
    )
    
    logger.info("✓ Test 10 completed")






