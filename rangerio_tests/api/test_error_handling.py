"""
Error Handling Tests
====================

Tests that the API handles errors gracefully and returns helpful messages.
Critical for user experience and debugging.

Run with:
    PYTHONPATH=. pytest rangerio_tests/api/test_error_handling.py -v -s
"""
import pytest
import tempfile
from pathlib import Path

from rangerio_tests.config import config


@pytest.mark.api
@pytest.mark.error_handling
class TestInvalidFileUploads:
    """Test handling of invalid file uploads"""
    
    def test_empty_file_upload(self, api_client, create_test_rag, tmp_path):
        """Test that empty files are handled gracefully"""
        # Create empty file
        empty_file = tmp_path / "empty.csv"
        empty_file.write_text("")
        
        rag_id = create_test_rag("Empty File Test")
        
        response = api_client.upload_file(
            "/datasources/connect",
            empty_file,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        # Should return error, not crash
        assert response.status_code in [400, 422], \
            f"Empty file should be rejected, got {response.status_code}"
        
        # Error message should be helpful
        if response.status_code in [400, 422]:
            error = response.json()
            assert "error" in error or "detail" in error, "Should provide error details"
            print(f"Empty file error: {error}")
    
    def test_malformed_csv_upload(self, api_client, create_test_rag, tmp_path):
        """Test that malformed CSV is handled gracefully"""
        # Create malformed CSV (unbalanced quotes)
        bad_csv = tmp_path / "malformed.csv"
        bad_csv.write_text('col1,col2,col3\n"unclosed,value,here\n1,2,3')
        
        rag_id = create_test_rag("Malformed CSV Test")
        
        response = api_client.upload_file(
            "/datasources/connect",
            bad_csv,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        # Should handle gracefully (might succeed with error correction or fail)
        assert response.status_code != 500, \
            f"Malformed CSV should not cause 500 error: {response.text}"
        
        print(f"Malformed CSV response: {response.status_code}")
    
    def test_wrong_extension_upload(self, api_client, create_test_rag, tmp_path):
        """Test uploading file with wrong extension"""
        # Create JSON content but name it .csv
        wrong_ext = tmp_path / "data.csv"
        wrong_ext.write_text('{"not": "csv", "data": [1,2,3]}')
        
        rag_id = create_test_rag("Wrong Extension Test")
        
        response = api_client.upload_file(
            "/datasources/connect",
            wrong_ext,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        # Should handle gracefully
        assert response.status_code != 500, \
            f"Wrong extension should not cause 500 error"
        
        print(f"Wrong extension response: {response.status_code}")
    
    def test_binary_file_as_csv(self, api_client, create_test_rag, tmp_path):
        """Test uploading binary file as CSV"""
        # Create binary content
        binary_file = tmp_path / "binary.csv"
        binary_file.write_bytes(b'\x00\x01\x02\x03\x04\x05\xff\xfe\xfd')
        
        rag_id = create_test_rag("Binary File Test")
        
        response = api_client.upload_file(
            "/datasources/connect",
            binary_file,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        # Should reject binary, not crash
        assert response.status_code in [400, 415, 422], \
            f"Binary file should be rejected, got {response.status_code}"
    
    def test_oversized_header_csv(self, api_client, create_test_rag, tmp_path):
        """Test CSV with extremely long header"""
        # Create CSV with very long column name
        long_header = "col_" + "x" * 10000  # 10K char column name
        oversized = tmp_path / "long_header.csv"
        oversized.write_text(f'{long_header},col2\n1,2\n3,4')
        
        rag_id = create_test_rag("Long Header Test")
        
        response = api_client.upload_file(
            "/datasources/connect",
            oversized,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        # Should handle gracefully
        assert response.status_code != 500, "Long header should not cause 500"


@pytest.mark.api
@pytest.mark.error_handling
class TestInvalidAPIRequests:
    """Test handling of invalid API requests"""
    
    def test_missing_required_field(self, api_client):
        """Test request missing required fields"""
        response = api_client.post("/projects", json={})  # Missing name
        
        assert response.status_code in [400, 422], \
            f"Missing field should return 400/422, got {response.status_code}"
        
        error = response.json()
        assert "detail" in error or "error" in error, "Should provide error details"
    
    def test_invalid_json_body(self, api_client):
        """Test request with invalid JSON"""
        response = api_client.post(
            "/projects",
            data="not valid json {",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [400, 422], \
            f"Invalid JSON should return 400/422, got {response.status_code}"
    
    def test_wrong_data_type(self, api_client):
        """Test request with wrong data types"""
        response = api_client.post("/projects", json={
            "name": 12345,  # Should be string
            "description": ["array", "not", "string"]
        })
        
        # Should either accept (type coercion) or return validation error
        assert response.status_code in [200, 400, 422], \
            f"Wrong type should be handled, got {response.status_code}"
    
    def test_nonexistent_endpoint(self, api_client):
        """Test request to non-existent endpoint"""
        response = api_client.get("/this/endpoint/does/not/exist")
        
        assert response.status_code == 404, \
            f"Non-existent endpoint should return 404, got {response.status_code}"
    
    def test_wrong_http_method(self, api_client):
        """Test using wrong HTTP method"""
        # Try DELETE on endpoint that doesn't support it
        response = api_client.delete("/health")
        
        assert response.status_code in [404, 405], \
            f"Wrong method should return 404/405, got {response.status_code}"


@pytest.mark.api
@pytest.mark.error_handling
class TestResourceNotFound:
    """Test handling of not found resources"""
    
    def test_project_not_found(self, api_client):
        """Test getting non-existent project"""
        response = api_client.get("/projects/999999999")
        
        assert response.status_code == 404, \
            f"Non-existent project should return 404, got {response.status_code}"
    
    def test_datasource_not_found(self, api_client):
        """Test getting non-existent datasource"""
        response = api_client.get("/datasources/999999999")
        
        assert response.status_code == 404, \
            f"Non-existent datasource should return 404, got {response.status_code}"
    
    def test_rag_query_invalid_project(self, api_client):
        """Test RAG query with invalid project"""
        response = api_client.post("/rag/query", json={
            "prompt": "test query",
            "project_id": 999999999
        })
        
        # Should return error, not empty result
        assert response.status_code in [400, 404], \
            f"Invalid project should be rejected, got {response.status_code}"


@pytest.mark.api
@pytest.mark.error_handling
class TestInputValidation:
    """Test input validation and sanitization"""
    
    def test_sql_injection_in_query(self, api_client, create_test_rag):
        """Test that SQL injection attempts are handled"""
        rag_id = create_test_rag("SQL Injection Test")
        
        # SQL injection attempt in prompt
        response = api_client.post("/rag/query", json={
            "prompt": "'; DROP TABLE projects; --",
            "project_id": rag_id
        })
        
        # Should not crash, should not execute SQL
        assert response.status_code in [200, 400], \
            f"SQL injection should be handled, got {response.status_code}"
    
    def test_script_injection_in_name(self, api_client):
        """Test that script injection in names is handled"""
        response = api_client.post("/projects", json={
            "name": "<script>alert('xss')</script>",
            "description": "Test"
        })
        
        # Should accept but sanitize, or reject
        if response.status_code == 200:
            data = response.json()
            name = data.get("name", "")
            # Name should be sanitized or escaped
            assert "<script>" not in name or "&lt;script&gt;" in name, \
                "Script tags should be sanitized"
    
    def test_path_traversal_in_filename(self, api_client, create_test_rag, tmp_path):
        """Test that path traversal is blocked"""
        # Create normal file but try path traversal in name
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\n1,2")
        
        rag_id = create_test_rag("Path Traversal Test")
        
        # Attempt path traversal
        with open(test_file, 'rb') as f:
            response = api_client.post(
                "/datasources/connect",
                files={'file': ("../../../etc/passwd", f)},
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
        
        # Should either reject or sanitize filename
        if response.status_code == 200:
            data = response.json()
            name = data.get("name", data.get("filename", ""))
            assert ".." not in name, "Path traversal should be blocked"


@pytest.mark.api
@pytest.mark.error_handling
class TestResourceLimits:
    """Test resource limit handling"""
    
    def test_very_long_query(self, api_client, create_test_rag):
        """Test handling of extremely long query"""
        rag_id = create_test_rag("Long Query Test")
        
        # 100KB query
        long_query = "What is " + "the answer to " * 5000 + "?"
        
        response = api_client.post("/rag/query", json={
            "prompt": long_query,
            "project_id": rag_id
        })
        
        # Should handle gracefully - either truncate or reject
        assert response.status_code in [200, 400, 413, 422], \
            f"Long query should be handled, got {response.status_code}"
    
    def test_many_concurrent_requests(self, api_client):
        """Test handling many concurrent requests"""
        import concurrent.futures
        
        def make_request(_):
            return api_client.get("/health").status_code
        
        # 20 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(make_request, range(20)))
        
        # All should succeed
        success_rate = sum(1 for r in results if r == 200) / len(results)
        
        assert success_rate >= 0.9, \
            f"At least 90% of concurrent requests should succeed, got {success_rate*100:.0f}%"


@pytest.mark.api
@pytest.mark.error_handling  
class TestGracefulDegradation:
    """Test graceful degradation when components fail"""
    
    def test_health_check_always_responds(self, api_client):
        """Test that health check always responds"""
        response = api_client.get("/health")
        
        # Health should always respond, even if unhealthy
        assert response.status_code in [200, 503], \
            f"Health should respond, got {response.status_code}"
    
    def test_rag_query_without_model(self, api_client, create_test_rag):
        """Test RAG query behavior when model might not be loaded"""
        rag_id = create_test_rag("No Model Test")
        
        response = api_client.post("/rag/query", json={
            "prompt": "test query",
            "project_id": rag_id
        })
        
        # Should return meaningful error if model not loaded, not crash
        if response.status_code != 200:
            error = response.json()
            # Error should explain the issue
            assert "detail" in error or "error" in error or "message" in error, \
                "Should provide helpful error message"
            print(f"Query without model: {error}")
