"""
Sales Data Analysis Use Case - Realistic Testing

Tests RangerIO with 5-year sales data and complex business intelligence queries.
Validates data cleanup, multi-year comparisons, and export quality.

Use Case: Sales executive needs to analyze regional performance,
          profitability trends, and team effectiveness.
"""
import pytest
import pandas as pd
import time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.interactive
def test_sales_regional_profit_decline_analysis(
    api_client,
    sales_dataset,
    interactive_validator
):
    """
    Complex Query 1: Regional profit margin decline with product breakdown
    
    "Which regions showed declining profit margins in Q4 2022 compared to Q4 2021, 
    and what were the top 3 product categories contributing to this decline?"
    
    Tests:
    - Multi-year comparison (Q4 2021 vs Q4 2022)
    - Regional aggregation
    - Profitability calculation
    - Product category analysis
    - Cross-tab reasoning
    """
    logger.info("\n" + "="*80)
    logger.info("SALES USE CASE TEST 1: Regional Profit Margin Decline Analysis")
    logger.info("="*80)
    
    # Step 1: Create RAG project
    project_name = f"Sales Analysis {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]
    logger.info(f"✓ Created project: {project_name} (ID: {project_id})")
    
    # Step 2: Upload sales dataset
    upload_response = api_client.upload_file(
        "/datasources/connect",
        sales_dataset,
        data={"project_id": project_id, "source_type": "file"}
    )
    assert upload_response.status_code == 200
    upload_result = upload_response.json()
    # Get datasource info from the response
    table_name = upload_result.get("table_name", "")
    datasource_id = project_id  # Use project_id as datasource identifier for queries
    logger.info(f"✓ Uploaded sales data (Table: {table_name}, Rows: {upload_result.get('row_count', 0)})")
    
    # Wait for ingestion to complete (Excel files take longer)
    logger.info("⏳ Waiting for ingestion to complete...")
    time.sleep(15)
    
    # Step 3: Execute complex query
    question = """
    Which regions showed declining profit margins in Q4 2022 compared to Q4 2021, 
    and what were the top 3 product categories contributing to this decline?
    
    Please provide:
    1. List of regions with margin decline
    2. The percentage point decline for each region
    3. Top 3 product categories in those regions that contributed most to the decline
    """
    
    logger.info(f"\n📊 QUERY: {question[:100]}...")
    
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
    contexts = result.get("sources", [])  # RangerIO uses "sources" not "contexts"
    
    # Capture assistant mode information
    clarification = result.get("clarification", {})
    validation = result.get("validation", {})
    confidence = result.get("confidence", {})
    hallucination_check = result.get("hallucination_check", {})
    
    logger.info(f"\n✓ Received answer ({len(answer)} chars)")
    logger.info(f"✓ Retrieved {len(contexts)} source chunks")
    if clarification:
        logger.info(f"✓ Clarification: {clarification.get('verdict', 'none')}")
    if confidence:
        logger.info(f"✓ Confidence: {confidence.get('score', 0):.2f} ({confidence.get('verdict', 'unknown')})")
    if hallucination_check:
        logger.info(f"✓ Hallucination check: {'DETECTED' if hallucination_check.get('is_hallucination') else 'CLEAN'}")
    
    # Step 4: Interactive validation with refinement tracking
    validation = interactive_validator.display_query_with_refinement_feedback(
        question=question,
        answer=answer,
        contexts=contexts,
        metadata={
            'query_type': 'multi_year_comparison',
            'complexity': 'high',
            'datasource_id': datasource_id,
            'project_id': project_id,
            'test_name': 'regional_profit_decline',
            'assistant_mode': True,
            'clarification': clarification,
            'validation_info': validation,
            'confidence': confidence,
            'hallucination_check': hallucination_check,
            'answer_length': len(answer),
            'expected_elements': [
                'Region names (North, South, East, West, Central)',
                'Q4 2021 vs Q4 2022 comparison',
                'Profit margin percentages',
                'Product categories ranked by impact',
                'Quantitative decline values'
            ],
            'potential_issues': [
                'Hallucinated regions not in data',
                'Incorrect date filtering (wrong quarters)',
                'Made-up profit margin numbers',
                'Product categories not actually in decline',
                'Missing year-over-year comparison',
                'Too verbose (should be concise)',
                'Too brief (missing details)'
            ]
        }
    )
    
    # Basic assertions (before human review)
    assert len(answer) > 50, "Answer too short"
    assert len(contexts) > 0, "No context retrieved"
    
    logger.info("✓ Test 1 completed - awaiting human validation")


@pytest.mark.integration
@pytest.mark.interactive
def test_sales_team_performance_segmentation(
    api_client,
    sales_dataset,
    interactive_validator
):
    """
    Complex Query 2: Sales team performance analysis with deal size comparison
    
    "For sales teams that exceeded their targets by more than 20% in 2023, 
    what was their average deal size and how does it compare to teams that missed targets?"
    
    Tests:
    - Performance segmentation (>20% vs missed)
    - Aggregation across teams
    - Comparative analysis
    - Average deal size calculation
    - Multi-tab data (Sales Team Performance tab)
    """
    logger.info("\n" + "="*80)
    logger.info("SALES USE CASE TEST 2: Sales Team Performance Segmentation")
    logger.info("="*80)
    
    # Step 1: Create RAG project
    project_name = f"Team Performance {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]
    logger.info(f"✓ Created project: {project_name} (ID: {project_id})")
    
    # Step 2: Upload sales dataset
    upload_response = api_client.upload_file(
        "/datasources/connect",
        sales_dataset,
        data={"project_id": project_id, "source_type": "file"}
    )
    assert upload_response.status_code == 200
    upload_result = upload_response.json()
    # Get datasource info from the response
    table_name = upload_result.get("table_name", "")
    datasource_id = project_id  # Use project_id as datasource identifier for queries
    logger.info(f"✓ Uploaded sales data (Table: {table_name}, Rows: {upload_result.get('row_count', 0)})")
    
    # Wait for ingestion to complete (Excel files take longer)
    logger.info("⏳ Waiting for ingestion to complete...")
    time.sleep(15)
    
    # Step 3: Execute complex query
    question = """
    For sales teams that exceeded their targets by more than 20% in 2023, 
    what was their average deal size and how does it compare to teams that missed targets?
    
    Please provide:
    1. Number of teams that exceeded targets by >20%
    2. Their average deal size (revenue per deal)
    3. Number of teams that missed targets
    4. The average deal size for teams that missed
    5. The percentage difference between the two groups
    """
    
    logger.info(f"\n📊 QUERY: {question[:100]}...")
    
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
    contexts = result.get("sources", [])  # RangerIO uses "sources" not "contexts"
    
    logger.info(f"\n✓ Received answer ({len(answer)} chars)")
    logger.info(f"✓ Retrieved {len(contexts)} source chunks")
    
    # Step 4: Interactive validation with refinement tracking
    validation = interactive_validator.display_query_with_refinement_feedback(
        question=question,
        answer=answer,
        contexts=contexts,
        metadata={
            'query_type': 'performance_segmentation',
            'complexity': 'high',
            'datasource_id': datasource_id,
            'project_id': project_id,
            'test_name': 'team_performance',
            'expected_elements': [
                'Count of high-performing teams (>20% target)',
                'Count of teams that missed targets',
                'Average deal size for each group',
                'Comparative analysis (percentage difference)',
                'Data from Sales Team Performance tab'
            ],
            'potential_issues': [
                'Incorrect target achievement threshold (not >20%)',
                'Wrong year (not 2023)',
                'Deal size calculation error',
                'Missing comparison between groups',
                'Hallucinated team names or counts'
            ]
        }
    )
    
    # Basic assertions
    assert len(answer) > 50, "Answer too short"
    assert len(contexts) > 0, "No context retrieved"
    
    logger.info("✓ Test 2 completed - awaiting human validation")


@pytest.mark.integration
@pytest.mark.interactive
def test_sales_reseller_profitability_correlation(
    api_client,
    sales_dataset,
    interactive_validator
):
    """
    Complex Query 3: Reseller discount vs profit margin correlation
    
    "Analyze the correlation between reseller discount rates and profit margins. 
    Which resellers are getting the best deals but generating the lowest margins?"
    
    Tests:
    - Correlation analysis
    - Profitability insights
    - Business recommendations
    - Multi-metric analysis (discount % and margin %)
    - Identifying outliers (high discount, low margin)
    """
    logger.info("\n" + "="*80)
    logger.info("SALES USE CASE TEST 3: Reseller Profitability Correlation")
    logger.info("="*80)
    
    # Step 1: Create RAG project
    project_name = f"Reseller Analysis {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]
    logger.info(f"✓ Created project: {project_name} (ID: {project_id})")
    
    # Step 2: Upload sales dataset
    upload_response = api_client.upload_file(
        "/datasources/connect",
        sales_dataset,
        data={"project_id": project_id, "source_type": "file"}
    )
    assert upload_response.status_code == 200
    upload_result = upload_response.json()
    # Get datasource info from the response
    table_name = upload_result.get("table_name", "")
    datasource_id = project_id  # Use project_id as datasource identifier for queries
    logger.info(f"✓ Uploaded sales data (Table: {table_name}, Rows: {upload_result.get('row_count', 0)})")
    
    # Wait for ingestion to complete (Excel files take longer)
    logger.info("⏳ Waiting for ingestion to complete...")
    time.sleep(15)
    
    # Step 3: Execute complex query
    question = """
    Analyze the correlation between reseller discount rates and profit margins. 
    Which resellers are getting the best deals (highest discounts) but generating 
    the lowest profit margins for us?
    
    Please provide:
    1. Overall correlation between discount % and profit margin %
    2. List of top 5 resellers by average discount received
    3. Their corresponding average profit margins
    4. Which resellers have high discounts (>15%) but low margins (<10%)
    5. Business recommendation based on this analysis
    """
    
    logger.info(f"\n📊 QUERY: {question[:100]}...")
    
    rag_response = api_client.post(
        "/rag/query",
        json={
            "project_id": project_id,
            "prompt": question,
            "assistant_mode": True,
            "deep_search_mode": True  # Complex analysis benefits from deep search
        }
    )
    
    assert rag_response.status_code == 200
    result = rag_response.json()
    
    answer = result.get("answer", "")
    contexts = result.get("sources", [])  # RangerIO uses "sources" not "contexts"
    
    logger.info(f"\n✓ Received answer ({len(answer)} chars)")
    logger.info(f"✓ Retrieved {len(contexts)} source chunks")
    
    # Step 4: Interactive validation with refinement tracking
    validation = interactive_validator.display_query_with_refinement_feedback(
        question=question,
        answer=answer,
        contexts=contexts,
        metadata={
            'query_type': 'correlation_analysis',
            'complexity': 'very_high',
            'datasource_id': datasource_id,
            'project_id': project_id,
            'test_name': 'reseller_profitability',
            'expected_elements': [
                'Correlation coefficient or qualitative assessment',
                'Top 5 resellers by discount rate',
                'Profit margins for those resellers',
                'Identification of problematic relationships (high discount, low margin)',
                'Actionable business recommendation'
            ],
            'potential_issues': [
                'No correlation analysis (just lists data)',
                'Incorrect discount/margin calculations',
                'Hallucinated reseller names',
                'Missing business insight/recommendation',
                'Overly generic response without data specifics'
            ]
        }
    )
    
    # Basic assertions
    assert len(answer) > 50, "Answer too short"
    assert len(contexts) > 0, "No context retrieved"
    
    logger.info("✓ Test 3 completed - awaiting human validation")


@pytest.mark.integration
@pytest.mark.interactive
def test_sales_data_cleanup_and_export(
    api_client,
    sales_dataset,
    interactive_validator
):
    """
    Data Cleanup & Export Test
    
    Tests the Prepare Wizard workflow:
    1. Identify missing data (Profit, Profit Margin %)
    2. Fill missing Profit values with mean
    3. Calculate missing Profit Margin % from Revenue and Profit
    4. Export cleaned data to Excel (multi-tab)
    5. Validate export quality
    """
    logger.info("\n" + "="*80)
    logger.info("SALES USE CASE TEST 4: Data Cleanup and Export")
    logger.info("="*80)
    
    # Step 1: Create RAG project
    project_name = f"Sales Cleanup {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]
    logger.info(f"✓ Created project: {project_name} (ID: {project_id})")
    
    # Step 2: Upload sales dataset
    upload_response = api_client.upload_file(
        "/datasources/connect",
        sales_dataset,
        data={"project_id": project_id, "source_type": "file"}
    )
    assert upload_response.status_code == 200
    upload_result = upload_response.json()
    # Get datasource info from the response
    table_name = upload_result.get("table_name", "")
    datasource_id = project_id  # Use project_id as datasource identifier for queries
    logger.info(f"✓ Uploaded sales data (Table: {table_name}, Rows: {upload_result.get('row_count', 0)})")
    
    # Wait for ingestion to complete (Excel files take longer)
    logger.info("⏳ Waiting for ingestion to complete...")
    time.sleep(15)
    
    # Step 3: Chat-based data cleanup instructions
    cleanup_instructions = """
    Please clean the sales data:
    
    1. For any missing values in the 'Profit' column, fill them with the mean (average) profit
    2. For any missing 'Profit Margin %' values, calculate them as: (Profit / Revenue) * 100
    3. Show me a preview of the changes
    """
    
    logger.info(f"\n🧹 CLEANUP INSTRUCTIONS: {cleanup_instructions[:100]}...")
    
    # Use PandasAI clean-with-audit endpoint
    cleanup_response = api_client.post(
        "/pandasai/clean-with-audit",
        json={
            "datasource_id": datasource_id,
            "instructions": cleanup_instructions,
            "columns": ["Profit", "Profit Margin %"]
        }
    )
    
    if cleanup_response.status_code == 200:
        cleanup_result = cleanup_response.json()
        logger.info(f"✓ Cleanup completed")
        logger.info(f"  - Changes made: {cleanup_result.get('changes_count', 0)}")
        logger.info(f"  - Low confidence items: {cleanup_result.get('low_confidence_count', 0)}")
    else:
        logger.warning(f"Cleanup endpoint not available (status {cleanup_response.status_code})")
        cleanup_result = {}
    
    # Step 4: Export cleaned data
    logger.info("\n📦 Exporting cleaned data...")
    
    export_response = api_client.post(
        "/pandasai/export",
        json={
            "datasource_id": datasource_id,
            "format": "xlsx",
            "data_option": "with_changes"
        }
    )
    
    if export_response.status_code == 200:
        # Save exported file
        export_path = Path("/tmp") / f"sales_cleaned_{int(time.time())}.xlsx"
        export_path.write_bytes(export_response.content)
        logger.info(f"✓ Exported to: {export_path}")
        
        # Validate export quality
        try:
            exported_df = pd.read_excel(export_path, sheet_name='Sales Transactions')
            
            # Check that missing values were filled
            profit_nulls = exported_df['Profit'].isna().sum()
            margin_nulls = exported_df['Profit Margin %'].isna().sum() if 'Profit Margin %' in exported_df.columns else 0
            
            logger.info(f"  - Remaining Profit nulls: {profit_nulls}")
            logger.info(f"  - Remaining Margin % nulls: {margin_nulls}")
            
            export_validation = {
                'file_path': str(export_path),
                'file_size': export_path.stat().st_size,
                'row_count': len(exported_df),
                'remaining_nulls': {
                    'Profit': int(profit_nulls),
                    'Profit Margin %': int(margin_nulls)
                },
                'export_successful': True
            }
            
        except Exception as e:
            logger.error(f"Export validation failed: {e}")
            export_validation = {'export_successful': False, 'error': str(e)}
    else:
        logger.warning(f"Export endpoint not available (status {export_response.status_code})")
        export_validation = {'export_successful': False, 'endpoint_unavailable': True}
    
    # Step 5: Interactive validation of cleanup and export
    validation = interactive_validator.display_export_quality_with_issues(
        export_info=export_validation,
        cleanup_instructions=cleanup_instructions,
        cleanup_result=cleanup_result,
        metadata={
            'test_name': 'sales_data_cleanup',
            'datasource_id': datasource_id,
            'project_id': project_id,
            'expected_outcomes': [
                'Missing Profit values filled with mean',
                'Missing Profit Margin % calculated correctly',
                'Excel export includes all tabs',
                'Data integrity maintained',
                'File opens correctly in Excel'
            ],
            'issues_to_check': [
                'Profit values not actually mean (wrong calculation)',
                'Profit Margin % formula incorrect',
                'Export missing tabs',
                'Data corruption or formatting issues',
                'File size unreasonable (too large/small)'
            ]
        }
    )
    
    logger.info("✓ Test 4 completed - awaiting human validation")

