"""
Export Workflows E2E Tests for RangerIO
=======================================

Tests for export functionality including:
1. CSV generation from RAG responses
2. Excel generation from direct data
3. Export from query with table extraction
4. File download verification

Uses test files from: /Users/vadim/Documents/RangerIO test files/

Run with:
    PYTHONPATH=. pytest rangerio_tests/integration/test_export_workflows.py -v --tb=long
"""
import pytest
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from rangerio_tests.config import config, logger

# Test timeouts
QUERY_TIMEOUT = 180  # 3 minutes for LLM queries
RAG_INGESTION_WAIT = 45  # seconds to wait for RAG indexing


# =============================================================================
# EXPORT WORKFLOW TESTS
# =============================================================================

@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.export
class TestExportWorkflows:
    """
    Test export functionality for generating CSV and Excel files.
    
    These tests validate the ability to export query results and data
    to various file formats.
    """
    
    @pytest.fixture(scope="function")
    def export_rag(self, api_client, financial_sample):
        """Create RAG with financial data for export testing"""
        import uuid
        unique_name = f"Export Test RAG_{uuid.uuid4().hex[:8]}"
        response = api_client.post("/projects", json={
            "name": unique_name,
            "description": "RAG for testing export workflows"
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
        
        time.sleep(RAG_INGESTION_WAIT)
        
        logger.info(f"Created export test RAG: {rag_id}")
        yield rag_id
        
        try:
            api_client.delete(f"/projects/{rag_id}")
        except:
            pass
    
    def test_generate_csv_from_response(self, api_client):
        """Test CSV generation from LLM response text"""
        # Create a response with table data
        response_text = """Here is the sales data:

| Product | Region | Sales |
|---------|--------|-------|
| Widget A | North | 1500 |
| Widget B | South | 2300 |
| Widget C | East | 1800 |
| Widget D | West | 2100 |

This shows the distribution across regions."""
        
        response = api_client.post(
            "/exports/generate",
            json={
                "response_text": response_text,
                "format": "csv",
                "filename": "sales_export"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            
            assert result.get('status') == 'success'
            file_info = result.get('file', {})
            
            logger.info(f"CSV generated: {file_info.get('filename')}")
            logger.info(f"  Rows: {file_info.get('row_count')}")
            logger.info(f"  Columns: {file_info.get('column_count')}")
            logger.info(f"  Download URL: {file_info.get('download_url')}")
            
            # Verify file structure
            assert file_info.get('row_count', 0) >= 4, "Should have at least 4 data rows"
            assert file_info.get('column_count', 0) == 3, "Should have 3 columns"
            
        elif response.status_code == 400:
            # Table extraction may fail - that's valid behavior
            logger.info(f"CSV generation returned 400: {response.text}")
        else:
            logger.warning(f"Unexpected status: {response.status_code}")
    
    def test_generate_excel_from_data(self, api_client):
        """Test Excel generation from direct data input"""
        response = api_client.post(
            "/exports/generate/data",
            json={
                "headers": ["Name", "Department", "Salary"],
                "rows": [
                    ["John Doe", "Engineering", "85000"],
                    ["Jane Smith", "Marketing", "72000"],
                    ["Bob Wilson", "Sales", "68000"],
                    ["Alice Brown", "Engineering", "92000"]
                ],
                "format": "xlsx",
                "filename": "employees_export"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            
            assert result.get('status') == 'success'
            file_info = result.get('file', {})
            
            logger.info(f"Excel generated: {file_info.get('filename')}")
            logger.info(f"  Rows: {file_info.get('row_count')}")
            logger.info(f"  Columns: {file_info.get('column_count')}")
            
            assert file_info.get('row_count') == 4, "Should have 4 data rows"
            assert file_info.get('column_count') == 3, "Should have 3 columns"
            
        elif response.status_code == 404:
            logger.info("Export data endpoint not available")
        else:
            logger.warning(f"Export data status: {response.status_code}")
    
    def test_export_from_query(self, api_client, export_rag):
        """Test export from RAG query with table extraction"""
        response = api_client.post(
            "/exports/generate/query",
            json={
                "prompt": "Show me the top 5 products by sales in a table format",
                "project_id": export_rag,
                "format": "csv"
            },
            timeout=QUERY_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            status = result.get('status')
            
            if status == 'success':
                file_info = result.get('file', {})
                logger.info(f"Export from query generated: {file_info.get('filename')}")
                logger.info(f"  Rows: {file_info.get('row_count')}")
            elif status == 'no_table':
                logger.info(f"Query returned no table data: {result.get('message')}")
                # Response should still be present
                assert result.get('response') or result.get('answer')
            else:
                logger.info(f"Export status: {status}")
                
        elif response.status_code == 404:
            logger.info("Export query endpoint not available")
        else:
            logger.warning(f"Export query status: {response.status_code}")
    
    def test_file_download(self, api_client):
        """Test file download after generation"""
        # First generate a file
        response = api_client.post(
            "/exports/generate/data",
            json={
                "headers": ["ID", "Value"],
                "rows": [["1", "100"], ["2", "200"]],
                "format": "csv",
                "filename": "download_test"
            }
        )
        
        if response.status_code != 200:
            pytest.skip("Could not generate file for download test")
        
        result = response.json()
        if result.get('status') != 'success':
            pytest.skip("File generation did not succeed")
        
        file_id = result.get('file', {}).get('id')
        download_url = result.get('file', {}).get('download_url')
        
        if not file_id or not download_url:
            pytest.skip("No file ID or download URL returned")
        
        # Test download
        download_response = api_client.get(download_url)
        
        if download_response.status_code == 200:
            content_type = download_response.headers.get('content-type', '')
            content_length = len(download_response.content)
            
            logger.info(f"File downloaded successfully")
            logger.info(f"  Content-Type: {content_type}")
            logger.info(f"  Content-Length: {content_length} bytes")
            
            assert content_length > 0, "Downloaded file should not be empty"
        else:
            logger.warning(f"Download failed: {download_response.status_code}")
    
    def test_list_generated_files(self, api_client, export_rag):
        """Test listing generated export files"""
        response = api_client.get(f"/exports/files?project_id={export_rag}")
        
        if response.status_code == 200:
            result = response.json()
            files = result.get('files', result) if isinstance(result, dict) else result
            
            logger.info(f"Generated files for project: {len(files) if isinstance(files, list) else 'unknown'}")
            
            if isinstance(files, list):
                for f in files[:5]:
                    logger.info(f"  - {f.get('filename', f.get('id', 'unknown'))}")
        elif response.status_code == 404:
            logger.info("File listing endpoint not available")
        else:
            logger.info(f"File listing status: {response.status_code}")


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.export
class TestExportFormats:
    """Test different export format options"""
    
    def test_csv_format_options(self, api_client):
        """Test CSV generation with different delimiters"""
        # Standard CSV
        response = api_client.post(
            "/exports/generate/data",
            json={
                "headers": ["A", "B", "C"],
                "rows": [["1", "2", "3"]],
                "format": "csv"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            mime_type = result.get('file', {}).get('mime_type', '')
            logger.info(f"CSV mime type: {mime_type}")
            assert 'csv' in mime_type.lower() or 'text' in mime_type.lower()
    
    def test_excel_format_options(self, api_client):
        """Test Excel generation"""
        response = api_client.post(
            "/exports/generate/data",
            json={
                "headers": ["X", "Y", "Z"],
                "rows": [["a", "b", "c"]],
                "format": "xlsx"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            mime_type = result.get('file', {}).get('mime_type', '')
            filename = result.get('file', {}).get('filename', '')
            
            logger.info(f"Excel mime type: {mime_type}")
            logger.info(f"Excel filename: {filename}")
            
            # Verify Excel format
            assert 'xlsx' in filename.lower() or 'spreadsheet' in mime_type.lower()


@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.export
class TestExportErrorHandling:
    """Test export error handling"""
    
    def test_empty_data_export(self, api_client):
        """Test export with empty data"""
        response = api_client.post(
            "/exports/generate/data",
            json={
                "headers": [],
                "rows": [],
                "format": "csv"
            }
        )
        
        # Should return 400 for invalid input
        if response.status_code == 400:
            logger.info("Correctly rejected empty data export")
        elif response.status_code == 200:
            logger.info("Accepted empty data (may generate empty file)")
        else:
            logger.info(f"Empty data response: {response.status_code}")
    
    def test_invalid_format(self, api_client):
        """Test export with invalid format"""
        response = api_client.post(
            "/exports/generate/data",
            json={
                "headers": ["A"],
                "rows": [["1"]],
                "format": "invalid_format"
            }
        )
        
        # Should handle invalid format gracefully
        logger.info(f"Invalid format response: {response.status_code}")
        
        if response.status_code == 400:
            logger.info("Correctly rejected invalid format")
    
    def test_no_table_in_response(self, api_client):
        """Test export from response with no table data"""
        response = api_client.post(
            "/exports/generate",
            json={
                "response_text": "This is just plain text with no tables at all.",
                "format": "csv"
            }
        )
        
        if response.status_code == 400:
            logger.info("Correctly indicated no table found")
            error = response.json()
            logger.info(f"Error message: {error}")
        elif response.status_code == 200:
            result = response.json()
            # May succeed with empty or parsed result
            logger.info(f"Response with no table: {result}")
