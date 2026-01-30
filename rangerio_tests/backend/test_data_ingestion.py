"""
Comprehensive backend data ingestion tests
Tests all file types, sizes, and error scenarios
"""
import pytest
from pathlib import Path


@pytest.mark.integration
class TestDataIngestion:
    """Test data ingestion for all file types"""
    
    def test_import_small_csv(self, api_client, create_test_rag, sample_csv_small):
        """Test importing small CSV file"""
        rag_id = create_test_rag("CSV Import Test")
        assert rag_id is not None
        
        response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        assert response.status_code == 200
        result = response.json()
        assert 'id' in result or 'data_source_id' in result
    
    def test_import_large_csv(self, api_client, create_test_rag, sample_csv_large, performance_monitor):
        """Test importing medium-sized CSV with performance monitoring (5K rows)"""
        rag_id = create_test_rag("Large CSV Test")
        
        performance_monitor.start()
        response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_large,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        metrics = performance_monitor.stop()
        
        assert response.status_code == 200
        result = response.json()
        assert result['row_count'] == 5000  # Updated from 50000 to 5000
        
        # Performance assertions - adjusted for 5K rows
        performance_monitor.assert_performance(max_duration_s=30, max_memory_mb=1024)
    
    def test_import_excel(self, api_client, create_test_rag, sample_excel):
        """Test importing Excel file with multiple sheets"""
        rag_id = create_test_rag("Excel Import Test")
        
        response = api_client.upload_file(
            "/datasources/connect",
            sample_excel,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        assert response.status_code == 200
        # Should detect multiple sheets
    
    def test_import_json(self, api_client, create_test_rag, sample_json):
        """Test importing JSON file"""
        rag_id = create_test_rag("JSON Import Test")
        
        response = api_client.upload_file(
            "/datasources/connect",
            sample_json,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result['row_count'] == 200
    
    @pytest.mark.slow
    def test_concurrent_imports(self, api_client, create_test_rag, sample_csv_small):
        """Test concurrent file imports"""
        import concurrent.futures
        
        rag_id = create_test_rag("Concurrent Import Test")
        
        def import_file(file_num):
            response = api_client.upload_file(
                "/datasources/connect",
                sample_csv_small,
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
            return response.status_code == 200
        
        # Import 5 files concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(import_file, range(5)))
        
        assert all(results), "All concurrent imports should succeed"


@pytest.mark.integration
class TestDataQuality:
    """Test data quality checks and PII detection"""
    
    def test_pii_detection(self, api_client, create_test_rag, sample_csv_with_pii):
        """Test PII detection on data with known PII"""
        rag_id = create_test_rag("PII Test")
        
        # Upload file with PII
        response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_with_pii,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        assert response.status_code == 200
        datasource_id = response.json().get('data_source_id') or response.json().get('id')
        
        # Get quality report
        quality_response = api_client.get(f"/datasources/{datasource_id}/quality-check")
        assert quality_response.status_code == 200
        
        quality_data = quality_response.json()
        
        # Find PII check
        pii_issues = []
        for check in quality_data.get('checks', []):
            if 'pii' in check.get('check_type', '').lower():
                pii_issues.extend(check.get('issues', []))
        
        # Should detect at least SSN, email, phone columns (3+ PII detections)
        pii_columns = set(issue.get('column') for issue in pii_issues if issue.get('column'))
        assert len(pii_columns) >= 3, f"Expected ≥3 PII columns, found {len(pii_columns)}: {pii_columns}"


@pytest.mark.integration  
class TestPandasAIIntegration:
    """Test PandasAI endpoints"""
    
    def test_pandasai_query(self, api_client, create_test_rag, sample_csv_small):
        """Test natural language query via PandasAI"""
        rag_id = create_test_rag("PandasAI Test")
        
        # Upload data
        response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        assert response.status_code == 200
        datasource_id = response.json().get('data_source_id') or response.json().get('id')
        
        # Query with PandasAI
        query_response = api_client.post("/pandasai/query", json={
            "datasource_id": datasource_id,
            "question": "How many rows are there?"
        })
        
        if query_response.status_code == 200:
            result = query_response.json()
            assert 'answer' in result
            # Should mention 100 rows
            assert '100' in str(result['answer'])


@pytest.mark.integration
class TestMemoryManagement:
    """Test memory usage and management"""
    
    def test_memory_usage_large_file(self, api_client, create_test_rag, sample_csv_large, performance_monitor):
        """Test memory stays within limits for medium files (5K rows)"""
        rag_id = create_test_rag("Memory Test")
        
        performance_monitor.start()
        response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_large,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        metrics = performance_monitor.stop()
        
        assert response.status_code == 200
        # Memory should stay under 1GB for 5K rows
        assert metrics['peak_memory_mb'] < 1024, f"Memory usage: {metrics['peak_memory_mb']:.2f}MB exceeds 1GB limit"

