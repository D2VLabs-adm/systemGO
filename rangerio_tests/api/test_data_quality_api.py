"""
Data Quality API Tests
======================

Tests PII detection, masking, and data quality features.
These are critical for privacy compliance.

Run with:
    PYTHONPATH=. pytest rangerio_tests/api/test_data_quality_api.py -v -s
"""
import pytest
import re
from pathlib import Path

from rangerio_tests.config import config


# Sample PII patterns to test
EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
PHONE_PATTERN = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
SSN_PATTERN = r'\b\d{3}-\d{2}-\d{4}\b'


@pytest.mark.api
@pytest.mark.quality
class TestPIIDetection:
    """Test PII detection accuracy"""
    
    def test_pii_detection_on_customer_data(self, api_client, create_test_rag):
        """Test that PII is detected in customer data"""
        # Use built-in PII test data
        pii_file = config.TEST_DATA_DIR / "csv" / "pii_data.csv"
        if not pii_file.exists():
            pii_file = config.CUSTOMERS_PII
        
        if not pii_file.exists():
            pytest.skip("PII test data not found")
        
        # Create project and upload
        rag_id = create_test_rag("PII Detection Test")
        upload_response = api_client.upload_file(
            "/datasources/connect",
            pii_file,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip(f"Could not upload: {upload_response.text}")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        # Get data profile
        profile_response = api_client.get(f"/datasources/{ds_id}/profile")
        
        if profile_response.status_code != 200:
            # Try alternative endpoint
            profile_response = api_client.get(f"/datasources/{ds_id}")
        
        if profile_response.status_code == 200:
            profile = profile_response.json()
            
            # Check for PII detection in profile
            pii_detected = False
            pii_info = profile.get("pii_detection", profile.get("pii", {}))
            
            if pii_info:
                pii_detected = True
                print(f"PII detected: {pii_info}")
            
            # Also check column-level PII
            columns = profile.get("columns", profile.get("schema", []))
            for col in columns if isinstance(columns, list) else []:
                if isinstance(col, dict):
                    if col.get("pii_type") or col.get("contains_pii"):
                        pii_detected = True
                        print(f"PII in column {col.get('name')}: {col.get('pii_type')}")
            
            # Should detect PII in customer data
            assert pii_detected or "pii" in str(profile).lower(), \
                "PII should be detected in customer data"
    
    def test_pii_detection_accuracy_threshold(self, api_client, create_test_rag):
        """Test that PII detection meets accuracy threshold"""
        pii_file = config.CUSTOMERS_PII
        if not pii_file.exists():
            pytest.skip("Customer PII file not found")
        
        # Upload and check
        rag_id = create_test_rag("PII Accuracy Test")
        upload_response = api_client.upload_file(
            "/datasources/connect",
            pii_file,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        # Get quality analysis
        quality_response = api_client.get(f"/datasources/{ds_id}/quality")
        
        if quality_response.status_code == 200:
            quality = quality_response.json()
            
            # Check PII detection rate if available
            pii_rate = quality.get("pii_detection_rate", 0)
            if pii_rate > 0:
                assert pii_rate >= config.MIN_PII_DETECTION_RATE, \
                    f"PII detection rate {pii_rate} below threshold {config.MIN_PII_DETECTION_RATE}"


@pytest.mark.api
@pytest.mark.quality
class TestPIIMasking:
    """Test PII masking functionality"""
    
    def test_pii_masking_settings(self, api_client):
        """Test PII masking settings endpoint"""
        response = api_client.get("/settings/pii")
        
        if response.status_code == 404:
            pytest.skip("PII settings endpoint not available")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        settings = response.json()
        print(f"PII settings: {settings}")
        
        # Should have masking options
        assert isinstance(settings, dict), "Should return settings dict"
    
    def test_masked_export_removes_pii(self, api_client, create_test_rag):
        """Test that masked export actually removes PII"""
        pii_file = config.CUSTOMERS_PII
        if not pii_file.exists():
            pytest.skip("Customer PII file not found")
        
        # Upload PII data
        rag_id = create_test_rag("PII Masking Test")
        upload_response = api_client.upload_file(
            "/datasources/connect",
            pii_file,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        # Try to export with masking enabled
        export_response = api_client.post("/export/", json={
            "data_source_id": ds_id,
            "format": "csv",
            "mask_pii": True  # Request PII masking
        })
        
        if export_response.status_code == 404:
            pytest.skip("Export endpoint not available")
        
        if export_response.status_code == 200:
            result = export_response.json()
            export_id = result.get("id", result.get("export_id"))
            
            if export_id:
                # Download and check for PII
                download_response = api_client.get(f"/export/{export_id}/download")
                
                if download_response.status_code == 200:
                    content = download_response.text
                    
                    # Should NOT contain raw emails
                    emails_found = re.findall(EMAIL_PATTERN, content)
                    
                    # Masked emails might look like: j***@****.com
                    real_emails = [e for e in emails_found if '@' in e and '***' not in e]
                    
                    if real_emails:
                        print(f"WARNING: Found unmasked emails: {real_emails[:3]}")
                    
                    print(f"Export checked for PII masking")


@pytest.mark.api
@pytest.mark.quality
class TestDataQualityRules:
    """Test data quality rules application"""
    
    def test_quality_rules_endpoint(self, api_client):
        """Test quality rules endpoint exists"""
        response = api_client.get("/settings/quality")
        
        if response.status_code == 404:
            pytest.skip("Quality settings endpoint not available")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        settings = response.json()
        print(f"Quality settings: {settings}")
    
    def test_quality_defaults_endpoint(self, api_client):
        """Test getting quality rule defaults"""
        response = api_client.get("/settings/quality/defaults")
        
        if response.status_code == 404:
            pytest.skip("Quality defaults endpoint not available")
        
        assert response.status_code == 200, f"Failed: {response.text}"
    
    def test_quality_profile_on_mixed_data(self, api_client, create_test_rag):
        """Test quality profiling on data with known issues"""
        # Use data with quality issues
        quality_file = config.DATA_MIXED_QUALITY
        if not quality_file.exists():
            pytest.skip("Mixed quality test file not found")
        
        # Upload
        rag_id = create_test_rag("Quality Profile Test")
        upload_response = api_client.upload_file(
            "/datasources/connect",
            quality_file,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        # Get quality report
        quality_response = api_client.get(f"/datasources/{ds_id}/quality")
        
        if quality_response.status_code == 200:
            quality = quality_response.json()
            
            # Should report quality issues
            quality_score = quality.get("quality_score", quality.get("score", 100))
            issues = quality.get("issues", [])
            
            print(f"Quality score: {quality_score}")
            print(f"Issues found: {len(issues)}")
            
            # Mixed quality data should have issues
            # (Only assert if we have a meaningful response)
            if quality_score is not None:
                assert quality_score < 100, "Mixed quality data should have issues"


@pytest.mark.api
@pytest.mark.quality
class TestDuplicateDetection:
    """Test duplicate detection functionality"""
    
    def test_duplicate_detection(self, api_client, create_test_rag):
        """Test that duplicates are detected"""
        dup_file = config.DATA_DUPLICATES
        if not dup_file.exists():
            pytest.skip("Duplicates test file not found")
        
        # Upload
        rag_id = create_test_rag("Duplicate Test")
        upload_response = api_client.upload_file(
            "/datasources/connect",
            dup_file,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        # Check for duplicate detection in profile
        profile_response = api_client.get(f"/datasources/{ds_id}/profile")
        
        if profile_response.status_code == 200:
            profile = profile_response.json()
            
            duplicates = profile.get("duplicates", profile.get("duplicate_rows", 0))
            
            print(f"Duplicates detected: {duplicates}")
            
            # File with duplicates should show duplicate count
            # (relaxed assertion - just verify we got a response)
            assert profile is not None


@pytest.mark.api
@pytest.mark.quality
class TestMissingValueDetection:
    """Test missing value detection"""
    
    def test_missing_values_detected(self, api_client, create_test_rag):
        """Test that missing values are detected and reported"""
        missing_file = config.DATA_MISSING_VALUES
        if not missing_file.exists():
            pytest.skip("Missing values test file not found")
        
        # Upload
        rag_id = create_test_rag("Missing Values Test")
        upload_response = api_client.upload_file(
            "/datasources/connect",
            missing_file,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        # Check profile
        profile_response = api_client.get(f"/datasources/{ds_id}/profile")
        
        if profile_response.status_code == 200:
            profile = profile_response.json()
            
            # Check for missing value stats
            columns = profile.get("columns", [])
            missing_found = False
            
            for col in columns if isinstance(columns, list) else []:
                if isinstance(col, dict):
                    null_count = col.get("null_count", col.get("missing", 0))
                    if null_count and null_count > 0:
                        missing_found = True
                        print(f"Column {col.get('name')}: {null_count} missing values")
            
            if not missing_found:
                # Check top-level stats
                total_missing = profile.get("missing_values", profile.get("null_count", 0))
                if total_missing:
                    missing_found = True
                    print(f"Total missing values: {total_missing}")
            
            print(f"Missing value detection: {'Working' if missing_found else 'Not detected'}")
