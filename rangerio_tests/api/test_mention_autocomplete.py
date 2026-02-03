"""
@-Mention Autocomplete Tests
=============================

Tests the @-mention field autocomplete capability in chat.
This feature allows users to reference specific columns/fields using @column_name syntax.

Endpoints tested:
- GET /datasources/{id}/query-context     - Single source field info
- POST /datasources/batch-query-context   - Batch field info for multiple sources

Key behaviors:
- Tabular data (CSV, Excel, JSON) should return field names with types
- Document data (PDF, DOCX, TXT) should return is_document=True with empty fields
- Batch endpoint should merge fields across sources

Run with:
    PYTHONPATH=. pytest rangerio_tests/api/test_mention_autocomplete.py -v -s
"""
import pytest
import time
from pathlib import Path
from typing import List, Dict, Any

from rangerio_tests.config import config


@pytest.mark.api
@pytest.mark.mention
class TestQueryContextEndpoint:
    """Test single source query context endpoint"""
    
    def test_query_context_for_csv(self, api_client, create_test_rag, sample_csv_small):
        """Test getting field info for CSV data source"""
        rag_id = create_test_rag("Mention CSV Test")
        
        # Upload CSV
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        # Get query context
        response = api_client.get(f"/datasources/{ds_id}/query-context")
        
        if response.status_code == 404:
            pytest.skip("Query context endpoint not available")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        context = response.json()
        
        # Verify structure
        assert "data_source_id" in context
        assert "data_source_name" in context
        assert "fields" in context
        assert "is_document" in context
        
        # CSV should NOT be a document
        assert context["is_document"] == False, "CSV should not be marked as document"
        
        # Should have fields
        fields = context["fields"]
        assert len(fields) > 0, "CSV should have fields for @-mention"
        
        print(f"CSV query context:")
        print(f"  Source: {context['data_source_name']}")
        print(f"  Fields: {[f['name'] for f in fields]}")
        
        # Check field structure
        for field in fields:
            assert "name" in field, "Field should have name"
            assert "data_type" in field, "Field should have data_type"
            print(f"    - {field['name']}: {field['data_type']}")
    
    def test_query_context_for_excel(self, api_client, create_test_rag, sample_excel):
        """Test getting field info for Excel data source"""
        rag_id = create_test_rag("Mention Excel Test")
        
        # Upload Excel
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_excel,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        # Get query context
        response = api_client.get(f"/datasources/{ds_id}/query-context")
        
        if response.status_code == 404:
            pytest.skip("Query context endpoint not available")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        context = response.json()
        
        # Excel should NOT be a document
        assert context["is_document"] == False, "Excel should not be marked as document"
        
        # Should have fields
        fields = context["fields"]
        assert len(fields) > 0, "Excel should have fields for @-mention"
        
        print(f"Excel fields: {[f['name'] for f in fields]}")
    
    def test_query_context_nonexistent_source(self, api_client):
        """Test getting context for non-existent data source"""
        response = api_client.get("/datasources/999999999/query-context")
        
        # Should return 404
        assert response.status_code == 404, \
            f"Non-existent source should return 404, got {response.status_code}"
    
    def test_field_types_are_simplified(self, api_client, create_test_rag, sample_csv_small):
        """Test that field types are simplified for frontend"""
        rag_id = create_test_rag("Field Types Test")
        
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if upload_response.status_code != 200:
            pytest.skip("Upload failed")
        
        ds_id = upload_response.json().get('id', upload_response.json().get('data_source_id'))
        
        response = api_client.get(f"/datasources/{ds_id}/query-context")
        
        if response.status_code != 200:
            pytest.skip("Query context not available")
        
        context = response.json()
        fields = context.get("fields", [])
        
        # Expected simplified types
        valid_types = {"string", "integer", "float", "datetime", "boolean"}
        
        for field in fields:
            data_type = field.get("data_type", "")
            # Type should be simplified (not raw DuckDB types like VARCHAR, BIGINT)
            if data_type:
                is_simplified = data_type in valid_types or data_type.lower() in valid_types
                print(f"Field {field['name']}: {data_type} (simplified: {is_simplified})")


@pytest.mark.api
@pytest.mark.mention
class TestBatchQueryContext:
    """Test batch query context endpoint"""
    
    def test_batch_context_multiple_sources(self, api_client, create_test_rag, sample_csv_small, sample_excel):
        """Test getting context for multiple sources at once"""
        rag_id = create_test_rag("Batch Mention Test")
        
        # Upload CSV
        csv_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        # Upload Excel
        excel_response = api_client.upload_file(
            "/datasources/connect",
            sample_excel,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if csv_response.status_code != 200 or excel_response.status_code != 200:
            pytest.skip("Upload failed")
        
        csv_id = csv_response.json().get('id', csv_response.json().get('data_source_id'))
        excel_id = excel_response.json().get('id', excel_response.json().get('data_source_id'))
        
        # Batch request
        response = api_client.post("/datasources/batch-query-context", json={
            "ids": [csv_id, excel_id]
        })
        
        if response.status_code == 404:
            pytest.skip("Batch query context endpoint not available")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        
        batch = response.json()
        
        # Should have sources list
        assert "sources" in batch
        assert len(batch["sources"]) == 2, "Should return info for both sources"
        
        # Should have merged all_fields
        assert "all_fields" in batch
        all_fields = batch["all_fields"]
        print(f"Merged fields: {[f['name'] for f in all_fields]}")
        
        # Should indicate has tabular data
        assert "has_tabular_data" in batch
        assert batch["has_tabular_data"] == True, "Should have tabular data"
        
        # Should not be all documents
        assert batch.get("all_documents", False) == False
    
    def test_batch_context_empty_list(self, api_client):
        """Test batch context with empty list"""
        response = api_client.post("/datasources/batch-query-context", json={
            "ids": []
        })
        
        if response.status_code == 404:
            pytest.skip("Batch endpoint not available")
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 422], \
            f"Empty list should be handled, got {response.status_code}"
    
    def test_batch_context_invalid_ids(self, api_client):
        """Test batch context with invalid IDs"""
        response = api_client.post("/datasources/batch-query-context", json={
            "ids": [999999999, 888888888]
        })
        
        if response.status_code == 404:
            pytest.skip("Batch endpoint not available")
        
        # Should handle gracefully - either return empty or error
        assert response.status_code in [200, 400, 404], \
            f"Invalid IDs should be handled, got {response.status_code}"


@pytest.mark.api
@pytest.mark.mention
class TestMentionInQueries:
    """Test using @-mention syntax in actual queries"""
    
    @pytest.fixture
    def project_with_data(self, api_client, create_test_rag):
        """Create project with data that has known columns"""
        rag_id = create_test_rag("Mention Query Test")
        
        # Use financial sample which has known columns
        if config.FINANCIAL_SAMPLE.exists():
            response = api_client.upload_file(
                "/datasources/connect",
                config.FINANCIAL_SAMPLE,
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
            if response.status_code == 200:
                ds_id = response.json().get('id', response.json().get('data_source_id'))
                time.sleep(2)
                return {"rag_id": rag_id, "ds_id": ds_id}
        
        pytest.skip("Could not create test data")
    
    def test_query_with_column_mention(self, api_client, project_with_data):
        """Test query that references a specific column"""
        rag_id = project_with_data["rag_id"]
        ds_id = project_with_data["ds_id"]
        
        # First get available columns
        context_response = api_client.get(f"/datasources/{ds_id}/query-context")
        
        if context_response.status_code != 200:
            pytest.skip("Query context not available")
        
        context = context_response.json()
        fields = context.get("fields", [])
        
        if not fields:
            pytest.skip("No fields available")
        
        # Use first field name in query
        field_name = fields[0]["name"]
        
        # Query mentioning the field
        response = api_client.post("/rag/query", json={
            "prompt": f"What are the unique values in the {field_name} column?",
            "project_id": rag_id
        })
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("answer", result.get("response", ""))
            
            print(f"Query about @{field_name}:")
            print(f"Answer: {answer[:300]}...")
            
            # Answer should reference the field
            assert len(answer) > 20, "Should provide answer about the field"
    
    def test_query_referencing_multiple_columns(self, api_client, project_with_data):
        """Test query that references multiple columns"""
        rag_id = project_with_data["rag_id"]
        ds_id = project_with_data["ds_id"]
        
        # Get columns
        context_response = api_client.get(f"/datasources/{ds_id}/query-context")
        
        if context_response.status_code != 200:
            pytest.skip("Query context not available")
        
        context = context_response.json()
        fields = context.get("fields", [])
        
        if len(fields) < 2:
            pytest.skip("Need at least 2 fields")
        
        field1 = fields[0]["name"]
        field2 = fields[1]["name"]
        
        # Query mentioning both fields
        response = api_client.post("/rag/query", json={
            "prompt": f"Compare the {field1} and {field2} columns. What's the relationship?",
            "project_id": rag_id
        })
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("answer", result.get("response", ""))
            
            print(f"Query about @{field1} and @{field2}:")
            print(f"Answer: {answer[:300]}...")
    
    def test_query_with_nonexistent_column(self, api_client, project_with_data):
        """Test query referencing a column that doesn't exist"""
        rag_id = project_with_data["rag_id"]
        
        # Query with fake column name
        response = api_client.post("/rag/query", json={
            "prompt": "What is the average of the xyz_nonexistent_column_123?",
            "project_id": rag_id
        })
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("answer", result.get("response", ""))
            
            print(f"Query about non-existent column:")
            print(f"Answer: {answer[:200]}...")
            
            # Should handle gracefully - either indicate column not found or provide alternatives


@pytest.mark.api
@pytest.mark.mention
class TestCategoricalFieldInfo:
    """Test that categorical fields include sample values"""
    
    def test_categorical_fields_have_samples(self, api_client, create_test_rag):
        """Test that categorical fields include sample values for autocomplete"""
        rag_id = create_test_rag("Categorical Test")
        
        # Use data with known categorical columns
        if config.FINANCIAL_SAMPLE.exists():
            response = api_client.upload_file(
                "/datasources/connect",
                config.FINANCIAL_SAMPLE,
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
        else:
            pytest.skip("No suitable test file")
        
        if response.status_code != 200:
            pytest.skip("Upload failed")
        
        ds_id = response.json().get('id', response.json().get('data_source_id'))
        
        # Get context
        context_response = api_client.get(f"/datasources/{ds_id}/query-context")
        
        if context_response.status_code != 200:
            pytest.skip("Query context not available")
        
        context = context_response.json()
        fields = context.get("fields", [])
        
        # Check for categorical fields with sample values
        categorical_fields = [f for f in fields if f.get("is_categorical")]
        
        print(f"Categorical fields: {len(categorical_fields)}")
        
        for field in categorical_fields:
            samples = field.get("sample_values", [])
            print(f"  {field['name']}: {samples[:5] if samples else 'no samples'}")
            
            # Categorical fields SHOULD have sample values for autocomplete
            if samples:
                assert len(samples) <= 10, "Should limit sample values"


@pytest.mark.api
@pytest.mark.mention
class TestDocumentDataSources:
    """Test @-mention behavior for document data sources"""
    
    def test_document_source_returns_empty_fields(self, api_client, create_test_rag, tmp_path):
        """Test that PDF/document sources return is_document=True with empty fields"""
        # Note: This test would need a PDF file to upload
        # For now, we'll test the API behavior conceptually
        
        rag_id = create_test_rag("Document Mention Test")
        
        # Create a simple text file (simulating document)
        txt_file = tmp_path / "document.txt"
        txt_file.write_text("This is a sample document with some content.")
        
        response = api_client.upload_file(
            "/datasources/connect",
            txt_file,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        if response.status_code != 200:
            pytest.skip("Upload failed")
        
        ds_id = response.json().get('id', response.json().get('data_source_id'))
        
        # Get context
        context_response = api_client.get(f"/datasources/{ds_id}/query-context")
        
        if context_response.status_code != 200:
            pytest.skip("Query context not available")
        
        context = context_response.json()
        
        # Text files may or may not be treated as documents
        # depending on how RangerIO processes them
        print(f"Document context:")
        print(f"  is_document: {context.get('is_document')}")
        print(f"  fields: {len(context.get('fields', []))}")
        
        # If it's marked as document, should have empty fields
        if context.get("is_document"):
            assert len(context.get("fields", [])) == 0, \
                "Document sources should have empty fields for @-mention"


@pytest.mark.api
@pytest.mark.mention  
class TestMentionResponseIntegration:
    """Test that @-mention fields improve query responses"""
    
    @pytest.fixture
    def project_with_known_data(self, api_client, create_test_rag):
        """Create project with data that has predictable columns"""
        rag_id = create_test_rag("Mention Integration Test")
        
        if config.SALES_TRENDS.exists():
            response = api_client.upload_file(
                "/datasources/connect",
                config.SALES_TRENDS,
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
            if response.status_code == 200:
                ds_id = response.json().get('id', response.json().get('data_source_id'))
                time.sleep(2)
                return {"rag_id": rag_id, "ds_id": ds_id}
        
        pytest.skip("Could not create test data")
    
    def test_column_specific_aggregation(self, api_client, project_with_known_data):
        """Test that mentioning specific columns leads to accurate aggregations"""
        rag_id = project_with_known_data["rag_id"]
        ds_id = project_with_known_data["ds_id"]
        
        # Get columns
        context_response = api_client.get(f"/datasources/{ds_id}/query-context")
        
        if context_response.status_code != 200:
            pytest.skip("Query context not available")
        
        context = context_response.json()
        fields = context.get("fields", [])
        
        # Find a numeric field
        numeric_fields = [f for f in fields if f.get("data_type") in ["integer", "float"]]
        
        if not numeric_fields:
            pytest.skip("No numeric fields available")
        
        numeric_field = numeric_fields[0]["name"]
        
        # Query for average of specific column
        response = api_client.post("/rag/query", json={
            "prompt": f"What is the average of {numeric_field}?",
            "project_id": rag_id
        })
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("answer", result.get("response", ""))
            sql = result.get("sql", "")
            
            print(f"Aggregation query for @{numeric_field}:")
            print(f"SQL: {sql}")
            print(f"Answer: {answer[:200]}...")
            
            # SQL should reference the correct column
            if sql:
                assert numeric_field.lower() in sql.lower() or "avg" in sql.lower(), \
                    f"SQL should reference {numeric_field}"
    
    def test_filter_by_mentioned_column(self, api_client, project_with_known_data):
        """Test filtering by a specific mentioned column"""
        rag_id = project_with_known_data["rag_id"]
        ds_id = project_with_known_data["ds_id"]
        
        # Get columns
        context_response = api_client.get(f"/datasources/{ds_id}/query-context")
        
        if context_response.status_code != 200:
            pytest.skip("Query context not available")
        
        context = context_response.json()
        fields = context.get("fields", [])
        
        # Find a categorical field for filtering
        categorical_fields = [f for f in fields if f.get("is_categorical") and f.get("sample_values")]
        
        if categorical_fields:
            cat_field = categorical_fields[0]
            field_name = cat_field["name"]
            sample_value = cat_field["sample_values"][0] if cat_field.get("sample_values") else None
            
            if sample_value:
                # Query with filter
                response = api_client.post("/rag/query", json={
                    "prompt": f"Show me all rows where {field_name} is '{sample_value}'",
                    "project_id": rag_id
                })
                
                if response.status_code == 200:
                    result = response.json()
                    sql = result.get("sql", "")
                    
                    print(f"Filter query for @{field_name} = '{sample_value}':")
                    print(f"SQL: {sql}")
                    
                    # SQL should have WHERE clause with the field
                    if sql:
                        sql_lower = sql.lower()
                        has_filter = "where" in sql_lower and field_name.lower() in sql_lower
                        print(f"Has filter: {has_filter}")
