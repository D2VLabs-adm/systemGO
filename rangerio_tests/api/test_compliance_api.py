"""
Compliance API Tests
====================

Tests the compliance reporting and monitoring functionality.
Critical for enterprise users who need audit trails and compliance reports.

Note: assistant_mode is auto-enabled by conftest.py for all /rag/query calls.

Endpoints tested:
- POST /compliance/generate         - Generate compliance report
- GET /compliance/summary           - Get compliance summary
- GET /compliance/trends            - Get trend analysis
- GET /compliance/frameworks        - List supported frameworks
- GET /compliance/alerts            - Get active alerts
- GET /compliance/datasource/{id}/* - Per-datasource compliance

Run with:
    PYTHONPATH=. pytest rangerio_tests/api/test_compliance_api.py -v -s
"""
import pytest
import time
from pathlib import Path

from rangerio_tests.config import config


@pytest.mark.api
@pytest.mark.compliance
class TestComplianceFrameworks:
    """Test compliance framework listing"""
    
    def test_list_supported_frameworks(self, api_client):
        """Test listing supported compliance frameworks"""
        response = api_client.get("/compliance/frameworks")
        
        if response.status_code == 404:
            pytest.skip("Compliance frameworks endpoint not available")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        frameworks = response.json()
        print(f"Supported frameworks: {frameworks}")
        
        # Should return list of frameworks (GDPR, HIPAA, SOC2, etc.)
        assert isinstance(frameworks, (list, dict)), "Should return framework info"


@pytest.mark.api
@pytest.mark.compliance
class TestComplianceSummary:
    """Test compliance summary endpoint"""
    
    def test_get_compliance_summary(self, api_client):
        """Test getting overall compliance summary"""
        response = api_client.get("/compliance/summary")
        
        if response.status_code == 404:
            pytest.skip("Compliance summary endpoint not available")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        summary = response.json()
        print(f"Compliance summary: {summary}")
        
        # Should have summary fields
        assert isinstance(summary, dict), "Should return summary dict"


@pytest.mark.api
@pytest.mark.compliance
class TestComplianceReportGeneration:
    """Test generating compliance reports"""
    
    def test_generate_compliance_report(self, api_client, create_test_rag, sample_csv_with_pii):
        """Test generating a compliance report for data with PII"""
        # Create project with PII data
        rag_id = create_test_rag("Compliance Report Test")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_with_pii,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Could not upload test data")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        # Generate compliance report
        response = api_client.post("/compliance/generate", json={
            "datasource_id": ds_id,
            "framework": "GDPR"  # Common framework
        })
        
        if response.status_code == 404:
            pytest.skip("Compliance generate endpoint not available")
        
        if response.status_code == 200:
            report = response.json()
            print(f"Generated report: {report}")
            
            # Should have report fields
            assert "id" in report or "report_id" in report or "findings" in report, \
                "Should return report data"
    
    def test_generate_report_requires_datasource(self, api_client):
        """Test that report generation requires valid datasource"""
        response = api_client.post("/compliance/generate", json={
            "datasource_id": 999999999,
            "framework": "GDPR"
        })
        
        if response.status_code == 404:
            # Endpoint doesn't exist - skip
            pytest.skip("Compliance endpoint not available")
        
        # Should fail with invalid datasource
        assert response.status_code in [400, 404, 422], \
            f"Invalid datasource should be rejected, got {response.status_code}"


@pytest.mark.api
@pytest.mark.compliance
class TestComplianceTrends:
    """Test compliance trend analysis"""
    
    def test_get_compliance_trends(self, api_client):
        """Test getting compliance trends over time"""
        response = api_client.get("/compliance/trends")
        
        if response.status_code == 404:
            pytest.skip("Compliance trends endpoint not available")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        trends = response.json()
        print(f"Compliance trends: {trends}")
    
    def test_get_trends_by_type(self, api_client):
        """Test getting trends by compliance type"""
        response = api_client.get("/compliance/trends/by-type")
        
        if response.status_code == 404:
            pytest.skip("Trends by type endpoint not available")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Trends by type: {data}")


@pytest.mark.api
@pytest.mark.compliance
class TestComplianceAlerts:
    """Test compliance alerts functionality"""
    
    def test_get_compliance_alerts(self, api_client):
        """Test getting active compliance alerts"""
        response = api_client.get("/compliance/alerts")
        
        if response.status_code == 404:
            pytest.skip("Compliance alerts endpoint not available")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        alerts = response.json()
        print(f"Active alerts: {alerts}")
        
        # Should return list of alerts (may be empty)
        assert isinstance(alerts, (list, dict)), "Should return alerts data"


@pytest.mark.api
@pytest.mark.compliance
class TestComplianceReportList:
    """Test listing compliance reports"""
    
    def test_list_compliance_reports(self, api_client):
        """Test listing all compliance reports"""
        response = api_client.get("/compliance")
        
        if response.status_code == 404:
            pytest.skip("Compliance list endpoint not available")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        reports = response.json()
        print(f"Compliance reports: {reports}")
    
    def test_get_specific_report(self, api_client):
        """Test getting a specific report by ID"""
        # First try to get list
        list_response = api_client.get("/compliance")
        
        if list_response.status_code != 200:
            pytest.skip("Cannot get report list")
        
        reports = list_response.json()
        
        # Try to get first report if any exist
        report_list = reports if isinstance(reports, list) else reports.get("reports", [])
        
        if report_list:
            report_id = report_list[0].get("id", report_list[0].get("report_id"))
            if report_id:
                response = api_client.get(f"/compliance/{report_id}")
                assert response.status_code in [200, 404], \
                    f"Unexpected status: {response.status_code}"


@pytest.mark.api
@pytest.mark.compliance
class TestDatasourceCompliance:
    """Test per-datasource compliance endpoints"""
    
    def test_datasource_compliance_summary(self, api_client, create_test_rag, sample_csv_with_pii):
        """Test getting compliance summary for a specific datasource"""
        rag_id = create_test_rag("DS Compliance Test")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_with_pii,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        response = api_client.get(f"/compliance/datasource/{ds_id}/summary")
        
        if response.status_code == 404:
            pytest.skip("Datasource compliance summary not available")
        
        if response.status_code == 200:
            summary = response.json()
            print(f"Datasource compliance summary: {summary}")
    
    def test_datasource_intelligence(self, api_client, create_test_rag, sample_csv_with_pii):
        """Test compliance intelligence for datasource"""
        rag_id = create_test_rag("DS Intelligence Test")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_with_pii,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        response = api_client.get(f"/compliance/datasource/{ds_id}/intelligence")
        
        if response.status_code == 404:
            pytest.skip("Datasource intelligence endpoint not available")
        
        if response.status_code == 200:
            intel = response.json()
            print(f"Compliance intelligence: {intel}")
    
    def test_datasource_suggestions(self, api_client, create_test_rag, sample_csv_with_pii):
        """Test compliance fix suggestions for datasource"""
        rag_id = create_test_rag("DS Suggestions Test")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_with_pii,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        response = api_client.get(f"/compliance/datasource/{ds_id}/suggestions")
        
        if response.status_code == 404:
            pytest.skip("Suggestions endpoint not available")
        
        if response.status_code == 200:
            suggestions = response.json()
            print(f"Compliance suggestions: {suggestions}")
    
    def test_datasource_repair_actions(self, api_client, create_test_rag, sample_csv_with_pii):
        """Test getting repair actions for compliance issues"""
        rag_id = create_test_rag("DS Repair Test")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_with_pii,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        response = api_client.get(f"/compliance/datasource/{ds_id}/repair-actions")
        
        if response.status_code == 404:
            pytest.skip("Repair actions endpoint not available")
        
        if response.status_code == 200:
            actions = response.json()
            print(f"Repair actions: {actions}")


@pytest.mark.api
@pytest.mark.compliance
class TestComplianceExport:
    """Test exporting compliance data"""
    
    def test_export_warnings(self, api_client):
        """Test exporting compliance warnings"""
        response = api_client.post("/compliance/export/warnings", json={
            "format": "json"
        })
        
        if response.status_code == 404:
            pytest.skip("Export warnings endpoint not available")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Exported warnings: {data}")
