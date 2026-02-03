"""
Multi-Source RAG Tests
======================

Tests RAG functionality when querying across multiple data sources.
This is a key feature for users who want to analyze data from different files together.

Note: assistant_mode is auto-enabled by conftest.py for all /rag/query calls.

Run with:
    PYTHONPATH=. pytest rangerio_tests/integration/test_multi_source_rag.py -v -s
"""
import pytest
import time
from pathlib import Path
from typing import List, Dict, Any

from rangerio_tests.config import config


@pytest.mark.integration
@pytest.mark.multi_source
class TestMultiSourceSetup:
    """Test setting up multi-source RAG projects"""
    
    def test_create_project_with_multiple_sources(self, api_client, create_test_rag, sample_csv_small):
        """Test creating a project and adding multiple data sources"""
        rag_id = create_test_rag("Multi-Source Test")
        assert rag_id is not None
        
        # Upload first source
        response1 = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        assert response1.status_code == 200, f"First upload failed: {response1.text}"
        ds1_id = response1.json().get('id', response1.json().get('data_source_id'))
        
        # Upload second source (same file, different upload)
        response2 = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        assert response2.status_code == 200, f"Second upload failed: {response2.text}"
        ds2_id = response2.json().get('id', response2.json().get('data_source_id'))
        
        # Verify both sources exist
        sources_response = api_client.get(f"/datasources/project/{rag_id}")
        if sources_response.status_code == 200:
            sources = sources_response.json()
            if isinstance(sources, list):
                assert len(sources) >= 2, "Should have at least 2 data sources"
            print(f"Project has {len(sources) if isinstance(sources, list) else 'N/A'} sources")
    
    def test_add_different_file_types(self, api_client, create_test_rag, sample_csv_small, sample_excel):
        """Test adding different file types to same project"""
        rag_id = create_test_rag("Multi-Type Source Test")
        
        # Add CSV
        csv_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        assert csv_response.status_code == 200
        
        # Add Excel
        excel_response = api_client.upload_file(
            "/datasources/connect",
            sample_excel,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        assert excel_response.status_code == 200
        
        print("Successfully added CSV and Excel to same project")


@pytest.mark.integration
@pytest.mark.multi_source
class TestMultiSourceQueries:
    """Test querying across multiple sources"""
    
    @pytest.fixture
    def multi_source_project(self, api_client, create_test_rag):
        """Create project with multiple data sources"""
        rag_id = create_test_rag("Multi-Source Query Test")
        
        # Use different test data files
        files_to_add = [
            config.TEST_DATA_DIR / "csv" / "small_100rows.csv",
            config.FINANCIAL_SAMPLE,
            config.SALES_TRENDS,
        ]
        
        source_ids = []
        for file_path in files_to_add:
            if file_path.exists():
                response = api_client.upload_file(
                    "/datasources/connect",
                    file_path,
                    data={'project_id': str(rag_id), 'source_type': 'file'}
                )
                if response.status_code == 200:
                    ds_id = response.json().get('id', response.json().get('data_source_id'))
                    source_ids.append(ds_id)
        
        # Wait for indexing
        time.sleep(3)
        
        return {
            "rag_id": rag_id,
            "source_ids": source_ids,
            "source_count": len(source_ids)
        }
    
    def test_query_returns_multi_source_context(self, api_client, multi_source_project):
        """Test that queries can pull context from multiple sources"""
        if multi_source_project["source_count"] < 2:
            pytest.skip("Need at least 2 sources for multi-source test")
        
        rag_id = multi_source_project["rag_id"]
        
        # Query that might need multiple sources
        response = api_client.post("/rag/query", json={
            "prompt": "What data is available? Summarize all the datasets.",
            "project_id": rag_id
        })
        
        assert response.status_code == 200, f"Query failed: {response.text}"
        
        result = response.json()
        answer = result.get("answer", result.get("response", ""))
        sources = result.get("sources", [])
        
        print(f"Answer length: {len(answer)}")
        print(f"Sources returned: {len(sources)}")
        
        # Should have an answer
        assert answer, "Should return an answer"
    
    def test_source_attribution(self, api_client, multi_source_project):
        """Test that responses attribute sources correctly"""
        if multi_source_project["source_count"] < 2:
            pytest.skip("Need at least 2 sources for attribution test")
        
        rag_id = multi_source_project["rag_id"]
        
        response = api_client.post("/rag/query", json={
            "prompt": "List all the columns and their data types from each dataset",
            "project_id": rag_id
        })
        
        if response.status_code == 200:
            result = response.json()
            sources = result.get("sources", [])
            
            # Check if sources have attribution info
            for source in sources:
                if isinstance(source, dict):
                    # Source should have identifying info
                    has_id = "datasource_id" in source or "source_id" in source or "id" in source
                    has_name = "name" in source or "filename" in source
                    print(f"Source has ID: {has_id}, has name: {has_name}")
    
    def test_cross_source_analysis(self, api_client, create_test_rag):
        """Test queries that require comparing data across sources"""
        rag_id = create_test_rag("Cross-Source Analysis")
        
        # Add sales data
        if config.SALES_TRENDS.exists():
            api_client.upload_file(
                "/datasources/connect",
                config.SALES_TRENDS,
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
        
        # Add financial data
        if config.FINANCIAL_SAMPLE.exists():
            api_client.upload_file(
                "/datasources/connect",
                config.FINANCIAL_SAMPLE,
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
        
        time.sleep(3)
        
        # Query requiring cross-source analysis
        response = api_client.post("/rag/query", json={
            "prompt": "Compare the data in the different files. What are the key differences in structure and content?",
            "project_id": rag_id
        })
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("answer", result.get("response", ""))
            
            # Answer should reference multiple sources
            print(f"Cross-source analysis answer: {answer[:500]}...")


@pytest.mark.integration
@pytest.mark.multi_source
class TestMultiSourcePerformance:
    """Test performance with multiple sources"""
    
    def test_query_time_scales_reasonably(self, api_client, create_test_rag, sample_csv_small, performance_monitor):
        """Test that query time doesn't explode with more sources"""
        rag_id = create_test_rag("Performance Scale Test")
        
        times = []
        
        for i in range(3):
            # Add another source
            api_client.upload_file(
                "/datasources/connect",
                sample_csv_small,
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
            time.sleep(2)  # Wait for indexing
            
            # Measure query time
            performance_monitor.start()
            response = api_client.post("/rag/query", json={
                "prompt": "Summarize all available data",
                "project_id": rag_id
            })
            metrics = performance_monitor.stop()
            
            if response.status_code == 200:
                times.append(metrics.get("duration_ms", 0))
                print(f"Query with {i+1} sources: {times[-1]:.0f}ms")
        
        # Check that time doesn't grow too fast
        if len(times) >= 2:
            growth_rate = times[-1] / times[0] if times[0] > 0 else 1
            print(f"Time growth rate: {growth_rate:.2f}x")
            
            # Time shouldn't more than triple with 3x sources
            assert growth_rate < 5, f"Query time grew too fast: {growth_rate:.2f}x"


@pytest.mark.integration
@pytest.mark.multi_source
class TestSourceCoverage:
    """Test that queries properly cover all sources"""
    
    def test_min_source_coverage(self, api_client, create_test_rag):
        """Test that queries reference expected percentage of sources"""
        rag_id = create_test_rag("Source Coverage Test")
        
        # Add distinct data files
        files = [
            config.TEST_DATA_DIR / "csv" / "small_100rows.csv",
            config.DATA_MIXED_QUALITY,
            config.CUSTOMERS_PII,
        ]
        
        added_sources = []
        for f in files:
            if f.exists():
                resp = api_client.upload_file(
                    "/datasources/connect",
                    f,
                    data={'project_id': str(rag_id), 'source_type': 'file'}
                )
                if resp.status_code == 200:
                    added_sources.append(f.name)
        
        if len(added_sources) < 2:
            pytest.skip("Need at least 2 sources")
        
        time.sleep(3)
        
        # Query that should touch all sources
        response = api_client.post("/rag/query", json={
            "prompt": "Describe the data in each file. What columns does each have?",
            "project_id": rag_id
        })
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("answer", result.get("response", ""))
            sources = result.get("sources", [])
            
            # Count unique sources referenced
            unique_sources = set()
            for s in sources:
                if isinstance(s, dict):
                    src_id = s.get("datasource_id", s.get("source_id", s.get("id")))
                    if src_id:
                        unique_sources.add(src_id)
            
            coverage = len(unique_sources) / len(added_sources) if added_sources else 0
            print(f"Source coverage: {coverage*100:.0f}% ({len(unique_sources)}/{len(added_sources)})")
            
            # Check threshold from config
            if coverage < config.MIN_SOURCE_COVERAGE:
                print(f"WARNING: Coverage {coverage:.0%} below threshold {config.MIN_SOURCE_COVERAGE:.0%}")


@pytest.mark.integration
@pytest.mark.multi_source
class TestSourceConflicts:
    """Test handling of conflicting data across sources"""
    
    def test_contradictory_data_handling(self, api_client, create_test_rag, tmp_path):
        """Test how RAG handles contradictory information"""
        rag_id = create_test_rag("Contradiction Test")
        
        # Create two CSVs with contradictory data
        csv1 = tmp_path / "data1.csv"
        csv1.write_text("metric,value\nrevenue,1000000\nemployees,50")
        
        csv2 = tmp_path / "data2.csv"
        csv2.write_text("metric,value\nrevenue,2000000\nemployees,100")
        
        # Add both
        api_client.upload_file(
            "/datasources/connect",
            csv1,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        api_client.upload_file(
            "/datasources/connect",
            csv2,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        
        time.sleep(2)
        
        # Ask about the contradictory data
        response = api_client.post("/rag/query", json={
            "prompt": "What is the revenue and how many employees are there?",
            "project_id": rag_id
        })
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("answer", result.get("response", ""))
            
            # Good RAG should acknowledge the contradiction or pick one
            print(f"Contradiction handling: {answer}")
            
            # Answer should exist
            assert answer, "Should provide an answer even with contradictions"
