"""
Auditor Use Case - Multi-File Information Extraction

Tests RangerIO with mixed file types (Excel, PDF, DOCX, TXT) and complex
cross-document reasoning queries that require information synthesis.

Use Case: Auditor needs to cross-reference financial statements, board minutes,
          audit findings, and email correspondence to identify discrepancies
          and validate governance compliance.
"""
import pytest
import pandas as pd
import time
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.interactive
def test_auditor_capex_discrepancy_detection(
    api_client,
    auditor_files,
    interactive_validator
):
    """
    Complex Query 1: Cross-document discrepancy detection
    
    "Based on the financial statements and board meeting minutes, what capital 
    expenditures were discussed in Q3 2023 but don't appear in the Cash Flow statement?"
    
    Tests:
    - Cross-document reasoning (Excel + TXT/PDF)
    - Discrepancy detection
    - Numerical comparison
    - Context from multiple sources
    """
    logger.info("\n" + "="*80)
    logger.info("AUDITOR USE CASE TEST 1: CapEx Discrepancy Detection")
    logger.info("="*80)
    
    # Step 1: Create RAG project
    project_name = f"Auditor CapEx {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]
    logger.info(f"✓ Created project: {project_name} (ID: {project_id})")
    
    # Step 2: Upload all auditor files
    uploaded_sources = []
    for file_type, file_path in auditor_files.items():
        logger.info(f"Uploading {file_type}: {file_path.name}")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            file_path,
            data={"project_id": project_id, "source_type": "file"}
        )
        
        if upload_response.status_code == 200:
            upload_result = upload_response.json()
            table_name = upload_result.get("table_name", "")
            datasource_id = project_id  # Use project_id for queries
            uploaded_sources.append({
                'type': file_type,
                'path': file_path,
                'datasource_id': datasource_id,
                'table_name': table_name
            })
            logger.info(f"  ✓ Uploaded (Table: {table_name})")
        else:
            logger.warning(f"  ✗ Upload failed: {upload_response.status_code}")
    
    assert len(uploaded_sources) >= 2, "Need at least 2 files for cross-document testing"
    
    # Wait for ingestion to complete (multiple files)
    logger.info(f"⏳ Waiting for ingestion to complete ({len(uploaded_sources)} files)...")
    time.sleep(15)
    
    # Step 3: Execute cross-document query
    question = """
    Based on the financial statements and board meeting minutes, what capital 
    expenditures were discussed in Q3 2023 but don't appear in the Cash Flow statement?
    
    Please provide:
    1. List of capital expenditures mentioned in board minutes
    2. Capital expenditures shown in the Cash Flow statement
    3. Any discrepancies (items in minutes but not in cash flow)
    4. Dollar amounts for each discrepancy
    5. Possible explanations for the discrepancy
    """
    
    logger.info(f"\n📊 CROSS-DOCUMENT QUERY: {question[:100]}...")
    
    rag_response = api_client.post(
        "/rag/query",
        json={
            "project_id": project_id,
            "prompt": question,
            "assistant_mode": True,
            "deep_search_mode": True  # Multi-document needs thorough search
        }
    )
    
    assert rag_response.status_code == 200
    result = rag_response.json()
    
    answer = result.get("answer", "")
    contexts = result.get("sources", [])  # RangerIO uses "sources" not "contexts"
    
    logger.info(f"\n✓ Received answer ({len(answer)} chars)")
    logger.info(f"✓ Retrieved {len(contexts)} source chunks")
    
    # Analyze source coverage
    source_coverage = _analyze_source_coverage(contexts, uploaded_sources)
    logger.info(f"✓ Source coverage: {source_coverage}")
    
    # Step 4: Interactive validation with multi-source tracking
    validation = interactive_validator.display_multisource_query_validation(
        question=question,
        answer=answer,
        contexts=contexts,
        source_coverage=source_coverage,
        metadata={
            'query_type': 'cross_document_discrepancy',
            'complexity': 'very_high',
            'required_sources': ['excel', 'pdf'],  # Financial statements + board minutes
            'uploaded_sources': uploaded_sources,
            'project_id': project_id,
            'test_name': 'capex_discrepancy',
            'expected_elements': [
                'List of capex from board minutes ($750K approved)',
                'Capex from cash flow statement ($450K + $180K = $630K)',
                'Identification of $180K equipment purchases',
                'Explanation that $180K wasn\'t in cash flow projections',
                'Reference to both documents with specific amounts'
            ],
            'potential_issues': [
                'Only references one document (not cross-checking)',
                'Hallucinated dollar amounts',
                'Missing the $180K discrepancy',
                'Incorrect total calculations',
                'No explanation for why discrepancy exists',
                'Doesn\'t cite specific document sections'
            ]
        }
    )
    
    # Basic assertions
    assert len(answer) > 100, "Answer too short for complex cross-document query"
    assert len(contexts) > 0, "No context retrieved"
    assert source_coverage['unique_sources'] >= 2, "Query should reference multiple sources"
    
    logger.info("✓ Test 1 completed - awaiting human validation")


@pytest.mark.integration
@pytest.mark.interactive
def test_auditor_approval_authority_validation(
    api_client,
    auditor_files,
    interactive_validator
):
    """
    Complex Query 2: Governance validation across documents
    
    "Who approved the transactions flagged as 'requiring review'? Cross-reference 
    with board meeting attendees to validate appropriate authority."
    
    Tests:
    - Multi-source entity extraction (names from different docs)
    - Governance/compliance validation
    - Cross-referencing people across documents
    - Authority verification
    """
    logger.info("\n" + "="*80)
    logger.info("AUDITOR USE CASE TEST 2: Approval Authority Validation")
    logger.info("="*80)
    
    # Step 1: Create RAG project
    project_name = f"Auditor Authority {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]
    logger.info(f"✓ Created project: {project_name} (ID: {project_id})")
    
    # Step 2: Upload all auditor files
    uploaded_sources = []
    for file_type, file_path in auditor_files.items():
        logger.info(f"Uploading {file_type}: {file_path.name}")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            file_path,
            data={"project_id": project_id, "source_type": "file"}
        )
        
        if upload_response.status_code == 200:
            upload_result = upload_response.json()
            table_name = upload_result.get("table_name", "")
            datasource_id = project_id  # Use project_id for queries
            uploaded_sources.append({
                'type': file_type,
                'path': file_path,
                'datasource_id': datasource_id,
                'table_name': table_name
            })
            logger.info(f"  ✓ Uploaded (Table: {table_name})")
        else:
            logger.warning(f"  ✗ Upload failed: {upload_response.status_code}")
    
    assert len(uploaded_sources) >= 2, "Need at least 2 files for cross-document testing"
    
    # Wait for ingestion to complete (multiple files)
    logger.info(f"⏳ Waiting for ingestion to complete ({len(uploaded_sources)} files)...")
    time.sleep(15)
    
    # Step 3: Execute governance validation query
    question = """
    Who approved the transactions flagged as 'requiring review' in the audit findings? 
    Cross-reference with the board meeting attendees list to validate whether the 
    approvers had appropriate authority (were they board members or executives?).
    
    Please provide:
    1. List of transactions flagged as 'requiring review'
    2. Who approved each transaction
    3. List of board meeting attendees
    4. Whether each approver was present at the board meeting
    5. Whether the approval authority was appropriate (board policy requires approval for >$50K)
    """
    
    logger.info(f"\n📊 GOVERNANCE QUERY: {question[:100]}...")
    
    rag_response = api_client.post(
        "/rag/query",
        json={
            "project_id": project_id,
            "prompt": question,
            "assistant_mode": True,
            "deep_search_mode": True
        }
    )
    
    assert rag_response.status_code == 200
    result = rag_response.json()
    
    answer = result.get("answer", "")
    contexts = result.get("sources", [])  # RangerIO uses "sources" not "contexts"
    
    logger.info(f"\n✓ Received answer ({len(answer)} chars)")
    logger.info(f"✓ Retrieved {len(contexts)} source chunks")
    
    # Analyze source coverage
    source_coverage = _analyze_source_coverage(contexts, uploaded_sources)
    logger.info(f"✓ Source coverage: {source_coverage}")
    
    # Step 4: Interactive validation
    validation = interactive_validator.display_multisource_query_validation(
        question=question,
        answer=answer,
        contexts=contexts,
        source_coverage=source_coverage,
        metadata={
            'query_type': 'governance_validation',
            'complexity': 'very_high',
            'required_sources': ['docx', 'pdf', 'txt'],  # Audit findings + board minutes + emails
            'uploaded_sources': uploaded_sources,
            'project_id': project_id,
            'test_name': 'approval_authority',
            'expected_elements': [
                'Three flagged transactions ($95K, $45K, $40K)',
                'Approver: John Smith (CEO) for all three',
                'Board attendees list from minutes',
                'Policy threshold: >$50K requires board approval',
                'Analysis of whether approval was appropriate',
                'Reference to CEO discretionary authority'
            ],
            'potential_issues': [
                'Only lists transactions without cross-referencing approvers',
                'Doesn\'t check if approvers were at board meeting',
                'Misses the policy requirement (>$50K)',
                'Hallucinated approver names',
                'No governance analysis (just lists facts)',
                'Doesn\'t cite specific documents for each claim'
            ]
        }
    )
    
    # Basic assertions
    assert len(answer) > 100, "Answer too short"
    assert len(contexts) > 0, "No context retrieved"
    assert source_coverage['unique_sources'] >= 2, "Should reference multiple sources"
    
    logger.info("✓ Test 2 completed - awaiting human validation")


@pytest.mark.integration
@pytest.mark.interactive
def test_auditor_revenue_reconciliation(
    api_client,
    auditor_files,
    interactive_validator
):
    """
    Complex Query 3: Cross-document numerical reconciliation
    
    "Calculate total revenue from Income Statement and compare to revenue figures 
    mentioned in board minutes or email thread. Any discrepancies?"
    
    Tests:
    - Numerical extraction from multiple sources
    - Cross-validation of figures
    - Discrepancy detection with amounts
    - Reasoning about timing differences
    """
    logger.info("\n" + "="*80)
    logger.info("AUDITOR USE CASE TEST 3: Revenue Reconciliation")
    logger.info("="*80)
    
    # Step 1: Create RAG project
    project_name = f"Auditor Revenue {int(time.time())}"
    project_response = api_client.post("/projects", json={"name": project_name})
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]
    logger.info(f"✓ Created project: {project_name} (ID: {project_id})")
    
    # Step 2: Upload all auditor files
    uploaded_sources = []
    for file_type, file_path in auditor_files.items():
        logger.info(f"Uploading {file_type}: {file_path.name}")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            file_path,
            data={"project_id": project_id, "source_type": "file"}
        )
        
        if upload_response.status_code == 200:
            upload_result = upload_response.json()
            table_name = upload_result.get("table_name", "")
            datasource_id = project_id  # Use project_id for queries
            uploaded_sources.append({
                'type': file_type,
                'path': file_path,
                'datasource_id': datasource_id,
                'table_name': table_name
            })
            logger.info(f"  ✓ Uploaded (Table: {table_name})")
        else:
            logger.warning(f"  ✗ Upload failed: {upload_response.status_code}")
    
    assert len(uploaded_sources) >= 2, "Need at least 2 files for cross-document testing"
    
    # Wait for ingestion to complete (multiple files)
    logger.info(f"⏳ Waiting for ingestion to complete ({len(uploaded_sources)} files)...")
    time.sleep(15)
    
    # Step 3: Execute reconciliation query
    question = """
    Calculate the total revenue from the Income Statement for 2023 and compare it 
    to any revenue figures mentioned in the board meeting minutes or email threads.
    Are there any discrepancies? If so, what might explain them?
    
    Please provide:
    1. 2023 revenue from Income Statement
    2. Any revenue figures mentioned in board minutes
    3. Any revenue figures mentioned in email thread
    4. Calculation of any discrepancies
    5. Possible explanations (e.g., timing differences, Q3 vs full year, management vs GAAP reporting)
    """
    
    logger.info(f"\n📊 RECONCILIATION QUERY: {question[:100]}...")
    
    rag_response = api_client.post(
        "/rag/query",
        json={
            "project_id": project_id,
            "prompt": question,
            "assistant_mode": True,
            "deep_search_mode": True
        }
    )
    
    assert rag_response.status_code == 200
    result = rag_response.json()
    
    answer = result.get("answer", "")
    contexts = result.get("sources", [])  # RangerIO uses "sources" not "contexts"
    
    logger.info(f"\n✓ Received answer ({len(answer)} chars)")
    logger.info(f"✓ Retrieved {len(contexts)} source chunks")
    
    # Analyze source coverage
    source_coverage = _analyze_source_coverage(contexts, uploaded_sources)
    logger.info(f"✓ Source coverage: {source_coverage}")
    
    # Step 4: Interactive validation
    validation = interactive_validator.display_multisource_query_validation(
        question=question,
        answer=answer,
        contexts=contexts,
        source_coverage=source_coverage,
        metadata={
            'query_type': 'numerical_reconciliation',
            'complexity': 'high',
            'required_sources': ['excel', 'pdf', 'docx'],  # Income statement + board minutes + audit findings
            'uploaded_sources': uploaded_sources,
            'project_id': project_id,
            'test_name': 'revenue_reconciliation',
            'expected_elements': [
                'Full year 2023 revenue: $8,500,000 (from Income Statement)',
                'Q3 revenue: $2,150,000 (from board minutes)',
                'Audit finding notes $25K timing difference',
                'Calculation showing figures are consistent (Q3 is part of full year)',
                'Explanation of management vs GAAP reporting differences'
            ],
            'potential_issues': [
                'Compares Q3 to full year without noting they\'re different periods',
                'Hallucinated revenue numbers',
                'Misses the $25K timing difference in audit findings',
                'No explanation for discrepancies',
                'Incorrect arithmetic',
                'Doesn\'t reference all three documents'
            ]
        }
    )
    
    # Basic assertions
    assert len(answer) > 100, "Answer too short"
    assert len(contexts) > 0, "No context retrieved"
    assert source_coverage['unique_sources'] >= 2, "Should reference multiple sources"
    
    logger.info("✓ Test 3 completed - awaiting human validation")


def _analyze_source_coverage(contexts: list, uploaded_sources: list) -> dict:
    """
    Analyze which source documents contributed to the RAG response
    
    Returns: {
        'unique_sources': int,
        'source_breakdown': {file_type: count},
        'coverage_pct': float
    }
    """
    # Extract source information from contexts (if available in metadata)
    source_types = set()
    source_breakdown = {}
    
    for context in contexts:
        # Try to infer source from context (this is a simplified approach)
        context_text = context if isinstance(context, str) else str(context)
        
        # Check for financial statement indicators
        if any(keyword in context_text.lower() for keyword in ['revenue', 'balance sheet', 'cash flow', 'income statement']):
            source_types.add('excel')
            source_breakdown['excel'] = source_breakdown.get('excel', 0) + 1
        
        # Check for board minutes indicators
        if any(keyword in context_text.lower() for keyword in ['board meeting', 'attendees', 'approved unanimously', 'meeting adjourned']):
            source_types.add('pdf')
            source_breakdown['pdf'] = source_breakdown.get('pdf', 0) + 1
        
        # Check for audit findings indicators
        if any(keyword in context_text.lower() for keyword in ['audit findings', 'management response', 'finding 1', 'recommendation']):
            source_types.add('docx')
            source_breakdown['docx'] = source_breakdown.get('docx', 0) + 1
        
        # Check for email indicators
        if any(keyword in context_text.lower() for keyword in ['from:', 'to:', 'subject:', 'email']):
            source_types.add('txt')
            source_breakdown['txt'] = source_breakdown.get('txt', 0) + 1
    
    return {
        'unique_sources': len(source_types),
        'source_breakdown': source_breakdown,
        'coverage_pct': (len(source_types) / len(uploaded_sources)) * 100 if uploaded_sources else 0,
        'total_contexts': len(contexts)
    }

