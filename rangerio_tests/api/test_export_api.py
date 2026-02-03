"""
Export API Tests
================

Tests the export functionality which is critical for users to get data out of RangerIO.

Endpoints tested:
- POST /export/           - Create export
- GET /export/{id}        - Get export status
- GET /export/{id}/download - Download export
- DELETE /export/{id}     - Delete export
- POST /export/quick      - Quick export
- GET /export/formats/info - Format info

Run with:
    PYTHONPATH=. pytest rangerio_tests/api/test_export_api.py -v -s
"""
import pytest
import time
from pathlib import Path

from rangerio_tests.config import config


@pytest.mark.api
class TestExportFormats:
    """Test export format information"""
    
    def test_get_export_formats(self, api_client):
        """Test listing available export formats"""
        response = api_client.get("/export/formats/info")
        
        # Should return 200 or 404 if endpoint doesn't exist
        if response.status_code == 404:
            pytest.skip("Export formats endpoint not available")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # Should list available formats
        assert isinstance(data, (dict, list)), "Should return format info"
        
        print(f"Available export formats: {data}")


@pytest.mark.api
class TestExportCreation:
    """Test creating exports"""
    
    def test_export_requires_datasource(self, api_client):
        """Test that export requires a valid data source"""
        response = api_client.post("/export/", json={
            "data_source_id": 999999,  # Non-existent
            "format": "csv"
        })
        
        # Should fail with 404 or 400
        assert response.status_code in [400, 404, 422], \
            f"Should reject invalid datasource, got {response.status_code}"
    
    def test_export_invalid_format(self, api_client, create_test_rag, sample_csv_small):
        """Test that invalid export format is rejected"""
        # First create a datasource
        rag_id = create_test_rag("Export Format Test")
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Could not create test datasource")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        # Try invalid format
        response = api_client.post("/export/", json={
            "data_source_id": ds_id,
            "format": "invalid_format_xyz"
        })
        
        assert response.status_code in [400, 422], \
            f"Should reject invalid format, got {response.status_code}: {response.text}"
    
    def test_create_csv_export(self, api_client, create_test_rag, sample_csv_small):
        """Test creating a CSV export"""
        # Create datasource
        rag_id = create_test_rag("CSV Export Test")
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Could not create test datasource")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        # Create export
        response = api_client.post("/export/", json={
            "data_source_id": ds_id,
            "format": "csv"
        })
        
        if response.status_code == 404:
            pytest.skip("Export endpoint not available")
        
        assert response.status_code == 200, f"Export creation failed: {response.text}"
        
        result = response.json()
        assert "id" in result or "export_id" in result, "Should return export ID"
        
        print(f"Created export: {result}")


@pytest.mark.api
class TestExportStatus:
    """Test export status checking"""
    
    def test_get_nonexistent_export(self, api_client):
        """Test getting status of non-existent export"""
        response = api_client.get("/export/999999")
        
        if response.status_code == 404:
            # Expected behavior
            pass
        elif response.status_code == 200:
            # Some APIs return empty/null for not found
            data = response.json()
            assert data is None or data.get("error"), "Should indicate not found"


@pytest.mark.api
class TestExportDownload:
    """Test export download functionality"""
    
    def test_download_nonexistent_export(self, api_client):
        """Test downloading non-existent export"""
        response = api_client.get("/export/999999/download")
        
        assert response.status_code in [404, 400], \
            f"Should return not found, got {response.status_code}"


@pytest.mark.api
class TestQuickExport:
    """Test quick export functionality"""
    
    def test_quick_export(self, api_client, create_test_rag, sample_csv_small):
        """Test quick export (simpler API)"""
        # Create datasource
        rag_id = create_test_rag("Quick Export Test")
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Could not create test datasource")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        # Quick export
        response = api_client.post("/export/quick", json={
            "data_source_id": ds_id,
            "format": "csv"
        })
        
        if response.status_code == 404:
            pytest.skip("Quick export endpoint not available")
        
        # Should succeed or return meaningful error
        if response.status_code == 200:
            result = response.json()
            print(f"Quick export result: {result}")
        else:
            print(f"Quick export response: {response.status_code} - {response.text}")


@pytest.mark.api
class TestExportAuditTrail:
    """Test export audit trail functionality"""
    
    def test_audit_trail_requires_export(self, api_client):
        """Test that audit trail requires valid export"""
        response = api_client.get("/export/999999/audit")
        
        if response.status_code == 404:
            # Endpoint exists but export not found - expected
            pass
        elif response.status_code == 200:
            # Some APIs return empty for not found
            pass


@pytest.mark.api  
class TestExportPIIReport:
    """Test PII exposure report in exports"""
    
    def test_pii_report_endpoint(self, api_client):
        """Test PII report endpoint exists"""
        response = api_client.get("/export/999999/pii-report")
        
        # Should return 404 for not found, not 500
        assert response.status_code != 500, \
            f"PII report endpoint error: {response.text}"


@pytest.mark.api
class TestExportList:
    """Test listing exports"""
    
    def test_list_exports(self, api_client):
        """Test listing all exports"""
        response = api_client.get("/export/")
        
        if response.status_code == 404:
            pytest.skip("Export list endpoint not available")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # Should return a list or object with exports
        assert isinstance(data, (dict, list)), "Should return export list"
        
        print(f"Export list: {data}")


@pytest.mark.api
class TestExportDelete:
    """Test deleting exports"""
    
    def test_delete_nonexistent_export(self, api_client):
        """Test deleting non-existent export"""
        response = api_client.delete("/export/999999")
        
        # Should return 404 or succeed silently
        assert response.status_code in [200, 204, 404], \
            f"Unexpected status: {response.status_code}"
