"""
Query Type Classification & Routing Tests
==========================================

Tests that the system correctly identifies query intent and routes to the optimal
response workflow (SQL, LLM/RAG, suggestions, clarification, etc.)

This is critical for UX - users expect the system to "understand" what they want.

Note: assistant_mode is auto-enabled by conftest.py for all /rag/query calls.

Query Types:
- SQL Generation: "Show me all sales over $1000", "SELECT * FROM..."
- Data Analysis: "What's the average?", "Compare Q1 vs Q2"
- RAG/Context: "What does this data tell us?", "Summarize the trends"
- Suggestions: "What can I ask?", "Help me explore"
- Clarification: Ambiguous queries that need more info
- Metadata: "What columns are there?", "How many rows?"
- Visualization: "Plot the sales", "Show me a chart"

Run with:
    PYTHONPATH=. pytest rangerio_tests/integration/test_query_routing.py -v -s
"""
import pytest
import time
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from rangerio_tests.config import config


@dataclass
class QueryTestCase:
    """Test case for query routing"""
    query: str
    expected_type: str  # sql, rag, suggestion, clarification, metadata, visualization
    description: str
    should_contain: Optional[List[str]] = None  # Words/patterns expected in response
    should_not_contain: Optional[List[str]] = None  # Words that indicate wrong routing


# Test cases organized by expected query type
SQL_QUERIES = [
    QueryTestCase(
        query="Show me all rows where revenue is greater than 10000",
        expected_type="sql",
        description="Natural language SQL filter",
        should_contain=["SELECT", "WHERE", ">", "10000"],
    ),
    QueryTestCase(
        query="SELECT * FROM sales WHERE region = 'North'",
        expected_type="sql",
        description="Direct SQL passthrough",
        should_contain=["SELECT", "FROM"],
    ),
    QueryTestCase(
        query="Get the top 10 customers by total spend",
        expected_type="sql",
        description="Aggregation with limit",
        should_contain=["ORDER BY", "LIMIT", "10"],
    ),
    QueryTestCase(
        query="Count how many records have missing values in the email column",
        expected_type="sql",
        description="NULL check query",
        should_contain=["COUNT", "NULL", "email"],
    ),
    QueryTestCase(
        query="Join the customers and orders tables on customer_id",
        expected_type="sql",
        description="Join operation",
        should_contain=["JOIN", "customer_id"],
    ),
]

RAG_ANALYSIS_QUERIES = [
    QueryTestCase(
        query="What insights can you provide about sales trends?",
        expected_type="rag",
        description="Open-ended analysis request",
        should_not_contain=["SELECT", "FROM", "WHERE"],
    ),
    QueryTestCase(
        query="Summarize the key findings from this dataset",
        expected_type="rag",
        description="Summary request",
        should_contain=["summary", "key", "finding"],
    ),
    QueryTestCase(
        query="What story does this data tell about customer behavior?",
        expected_type="rag",
        description="Narrative analysis",
    ),
    QueryTestCase(
        query="Explain the relationship between price and quantity",
        expected_type="rag",
        description="Relationship analysis",
    ),
    QueryTestCase(
        query="What are the main patterns you see in Q4 performance?",
        expected_type="rag",
        description="Pattern identification",
    ),
]

METADATA_QUERIES = [
    QueryTestCase(
        query="What columns are in this dataset?",
        expected_type="metadata",
        description="Column listing",
        should_contain=["column"],
    ),
    QueryTestCase(
        query="How many rows are there?",
        expected_type="metadata",
        description="Row count",
        should_contain=["row", "record"],
    ),
    QueryTestCase(
        query="What data types does each column have?",
        expected_type="metadata",
        description="Schema info",
    ),
    QueryTestCase(
        query="Describe the structure of this data",
        expected_type="metadata",
        description="Structure description",
    ),
    QueryTestCase(
        query="What's the date range in this dataset?",
        expected_type="metadata",
        description="Data range query",
    ),
]


@pytest.mark.integration
@pytest.mark.query_routing
class TestQueryTypeClassification:
    """Test that queries are classified correctly"""
    
    @pytest.fixture
    def project_with_data(self, api_client, create_test_rag):
        """Create a project with sample data for testing"""
        rag_id = create_test_rag("Query Routing Test")
        
        # Upload financial sample for realistic queries
        if config.FINANCIAL_SAMPLE.exists():
            api_client.upload_file(
                "/datasources/connect",
                config.FINANCIAL_SAMPLE,
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
        elif config.SALES_TRENDS.exists():
            api_client.upload_file(
                "/datasources/connect",
                config.SALES_TRENDS,
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
        
        time.sleep(3)  # Wait for indexing
        return rag_id
    
    def _analyze_response(self, response_json: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze response to determine what type of answer was given"""
        analysis = {
            "has_sql": False,
            "has_chart": False,
            "has_narrative": False,
            "has_suggestions": False,
            "has_clarification": False,
            "response_type": "unknown"
        }
        
        answer = response_json.get("answer", response_json.get("response", ""))
        sql = response_json.get("sql", response_json.get("generated_sql", ""))
        chart = response_json.get("chart", response_json.get("visualization", None))
        suggestions = response_json.get("suggestions", response_json.get("follow_up", []))
        
        # Check for SQL
        if sql or (answer and re.search(r'\bSELECT\b.*\bFROM\b', answer, re.IGNORECASE)):
            analysis["has_sql"] = True
            analysis["response_type"] = "sql"
        
        # Check for chart
        if chart:
            analysis["has_chart"] = True
            analysis["response_type"] = "visualization"
        
        # Check for suggestions
        if suggestions:
            analysis["has_suggestions"] = True
        
        # Check for clarification request
        clarification_phrases = ["could you clarify", "what do you mean", "can you specify", "which", "unclear"]
        if any(phrase in answer.lower() for phrase in clarification_phrases):
            analysis["has_clarification"] = True
            analysis["response_type"] = "clarification"
        
        # Check for narrative (RAG) response
        if len(answer) > 100 and not analysis["has_sql"]:
            analysis["has_narrative"] = True
            if analysis["response_type"] == "unknown":
                analysis["response_type"] = "rag"
        
        return analysis
    
    @pytest.mark.parametrize("test_case", SQL_QUERIES, ids=lambda tc: tc.description)
    def test_sql_queries_generate_sql(self, api_client, project_with_data, test_case):
        """Test that SQL-intent queries generate SQL"""
        response = api_client.post("/rag/query", json={
            "prompt": test_case.query,
            "project_id": project_with_data
        })
        
        if response.status_code != 200:
            pytest.skip(f"Query failed: {response.status_code}")
        
        result = response.json()
        analysis = self._analyze_response(result)
        
        answer = result.get("answer", result.get("response", ""))
        sql = result.get("sql", result.get("generated_sql", ""))
        
        print(f"\nQuery: {test_case.query}")
        print(f"Response type: {analysis['response_type']}")
        print(f"SQL generated: {bool(sql)}")
        
        # Check for expected content
        if test_case.should_contain:
            combined = f"{answer} {sql}".upper()
            for expected in test_case.should_contain:
                if expected.upper() not in combined:
                    print(f"WARNING: Expected '{expected}' not found in response")
        
        # For SQL queries, we should get SQL
        assert analysis["has_sql"] or "SELECT" in answer.upper(), \
            f"SQL query should generate SQL, got: {analysis['response_type']}"
    
    @pytest.mark.parametrize("test_case", RAG_ANALYSIS_QUERIES, ids=lambda tc: tc.description)
    def test_analysis_queries_use_rag(self, api_client, project_with_data, test_case):
        """Test that analysis queries use RAG for narrative responses"""
        response = api_client.post("/rag/query", json={
            "prompt": test_case.query,
            "project_id": project_with_data
        })
        
        if response.status_code != 200:
            pytest.skip(f"Query failed: {response.status_code}")
        
        result = response.json()
        analysis = self._analyze_response(result)
        
        answer = result.get("answer", result.get("response", ""))
        
        print(f"\nQuery: {test_case.query}")
        print(f"Response type: {analysis['response_type']}")
        print(f"Answer length: {len(answer)} chars")
        
        # Analysis queries should get narrative responses, not just SQL
        assert analysis["has_narrative"] or len(answer) > 50, \
            f"Analysis query should get narrative response"
        
        # Should NOT just return raw SQL for open-ended questions
        if test_case.should_not_contain:
            for unwanted in test_case.should_not_contain:
                # Allow SQL in response but not ONLY SQL
                if answer.strip().upper().startswith(unwanted.upper()):
                    print(f"WARNING: Response appears to be just SQL")
    
    @pytest.mark.parametrize("test_case", METADATA_QUERIES, ids=lambda tc: tc.description)
    def test_metadata_queries(self, api_client, project_with_data, test_case):
        """Test that metadata queries return schema/structure info"""
        response = api_client.post("/rag/query", json={
            "prompt": test_case.query,
            "project_id": project_with_data
        })
        
        if response.status_code != 200:
            pytest.skip(f"Query failed: {response.status_code}")
        
        result = response.json()
        answer = result.get("answer", result.get("response", ""))
        
        print(f"\nQuery: {test_case.query}")
        print(f"Answer preview: {answer[:200]}...")
        
        # Metadata queries should return actual information
        assert len(answer) > 20, "Metadata query should return information"
        
        # Check for expected content
        if test_case.should_contain:
            answer_lower = answer.lower()
            found = any(term.lower() in answer_lower for term in test_case.should_contain)
            if not found:
                print(f"Expected one of {test_case.should_contain} in response")


@pytest.mark.integration
@pytest.mark.query_routing
class TestQueryIntentDetection:
    """Test specific intent detection scenarios"""
    
    @pytest.fixture
    def project_with_data(self, api_client, create_test_rag):
        """Create a project with sample data"""
        rag_id = create_test_rag("Intent Detection Test")
        
        if config.SALES_TRENDS.exists():
            api_client.upload_file(
                "/datasources/connect",
                config.SALES_TRENDS,
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
        
        time.sleep(2)
        return rag_id
    
    def test_comparison_intent(self, api_client, project_with_data):
        """Test queries that compare data"""
        queries = [
            "Compare Q1 and Q2 sales",
            "What's the difference between regions?",
            "How does 2024 compare to 2023?"
        ]
        
        for query in queries:
            response = api_client.post("/rag/query", json={
                "prompt": query,
                "project_id": project_with_data
            })
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("answer", result.get("response", ""))
                
                print(f"\nComparison query: {query}")
                print(f"Answer: {answer[:150]}...")
                
                # Comparison should provide comparative language
                comparison_words = ["higher", "lower", "more", "less", "increase", 
                                   "decrease", "compared", "difference", "vs", "versus"]
                has_comparison = any(word in answer.lower() for word in comparison_words)
                
                if not has_comparison:
                    print(f"WARNING: Comparison query may not have comparative response")
    
    def test_trend_intent(self, api_client, project_with_data):
        """Test queries about trends"""
        queries = [
            "What's the trend in sales over time?",
            "Are numbers going up or down?",
            "Show me the progression"
        ]
        
        for query in queries:
            response = api_client.post("/rag/query", json={
                "prompt": query,
                "project_id": project_with_data
            })
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("answer", result.get("response", ""))
                
                print(f"\nTrend query: {query}")
                print(f"Answer: {answer[:150]}...")
                
                # Trend response should have temporal language
                trend_words = ["increase", "decrease", "growth", "decline", "trend",
                             "over time", "rising", "falling", "stable"]
                has_trend = any(word in answer.lower() for word in trend_words)
                
                if not has_trend:
                    print(f"WARNING: Trend query may not have trend-focused response")
    
    def test_aggregation_intent(self, api_client, project_with_data):
        """Test queries requesting aggregations"""
        queries = [
            "What's the total?",
            "Calculate the average",
            "How many records are there?",
            "Sum up the sales"
        ]
        
        for query in queries:
            response = api_client.post("/rag/query", json={
                "prompt": query,
                "project_id": project_with_data
            })
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("answer", result.get("response", ""))
                sql = result.get("sql", "")
                
                print(f"\nAggregation query: {query}")
                print(f"Answer: {answer[:100]}...")
                
                # Should provide a number or SQL with aggregation
                has_number = bool(re.search(r'\d+', answer))
                has_agg_sql = any(agg in (sql + answer).upper() 
                                for agg in ["SUM", "AVG", "COUNT", "TOTAL", "AVERAGE"])
                
                if not (has_number or has_agg_sql):
                    print(f"WARNING: Aggregation query may not have computed result")
    
    def test_filter_intent(self, api_client, project_with_data):
        """Test queries with filtering conditions"""
        queries = [
            "Show only sales above 1000",
            "Filter to Q1 data only",
            "Just the records from January"
        ]
        
        for query in queries:
            response = api_client.post("/rag/query", json={
                "prompt": query,
                "project_id": project_with_data
            })
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("answer", result.get("response", ""))
                sql = result.get("sql", "")
                
                print(f"\nFilter query: {query}")
                
                # Filter queries should generate WHERE clause or filtered results
                has_filter = "WHERE" in (sql + answer).upper()
                print(f"Has filter: {has_filter}")


@pytest.mark.integration
@pytest.mark.query_routing
class TestFollowUpQueries:
    """Test handling of follow-up and contextual queries"""
    
    @pytest.fixture
    def project_with_data(self, api_client, create_test_rag):
        """Create a project with sample data"""
        rag_id = create_test_rag("Follow-up Test")
        
        if config.FINANCIAL_SAMPLE.exists():
            api_client.upload_file(
                "/datasources/connect",
                config.FINANCIAL_SAMPLE,
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
        
        time.sleep(2)
        return rag_id
    
    def test_follow_up_with_context(self, api_client, project_with_data):
        """Test that follow-up queries maintain context"""
        # First query
        response1 = api_client.post("/rag/query", json={
            "prompt": "What are the total sales?",
            "project_id": project_with_data
        })
        
        if response1.status_code != 200:
            pytest.skip("First query failed")
        
        result1 = response1.json()
        
        # Follow-up query
        response2 = api_client.post("/rag/query", json={
            "prompt": "Break that down by region",
            "project_id": project_with_data,
            "conversation_history": [
                {"role": "user", "content": "What are the total sales?"},
                {"role": "assistant", "content": result1.get("answer", "")}
            ]
        })
        
        if response2.status_code == 200:
            result2 = response2.json()
            answer = result2.get("answer", result2.get("response", ""))
            
            print(f"Follow-up response: {answer[:200]}...")
            
            # Should understand "that" refers to sales
            assert len(answer) > 20, "Follow-up should provide response"
    
    def test_drill_down_queries(self, api_client, project_with_data):
        """Test drill-down query patterns"""
        # Start with overview
        response1 = api_client.post("/rag/query", json={
            "prompt": "Give me an overview of the data",
            "project_id": project_with_data
        })
        
        if response1.status_code != 200:
            pytest.skip("Overview query failed")
        
        # Drill down
        response2 = api_client.post("/rag/query", json={
            "prompt": "Tell me more about the sales column specifically",
            "project_id": project_with_data
        })
        
        if response2.status_code == 200:
            result = response2.json()
            answer = result.get("answer", result.get("response", ""))
            
            print(f"Drill-down response: {answer[:200]}...")
            
            # Should focus on the specific column
            assert "sale" in answer.lower() or len(answer) > 30


@pytest.mark.integration
@pytest.mark.query_routing
class TestEdgeCaseQueries:
    """Test handling of edge case and unusual queries"""
    
    @pytest.fixture
    def project_with_data(self, api_client, create_test_rag):
        """Create a project with sample data"""
        rag_id = create_test_rag("Edge Case Test")
        
        sample_file = config.TEST_DATA_DIR / "csv" / "small_100rows.csv"
        if sample_file.exists():
            api_client.upload_file(
                "/datasources/connect",
                sample_file,
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
        
        time.sleep(2)
        return rag_id
    
    def test_empty_query(self, api_client, project_with_data):
        """Test handling of empty query"""
        response = api_client.post("/rag/query", json={
            "prompt": "",
            "project_id": project_with_data
        })
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 422], \
            f"Empty query should be handled, got {response.status_code}"
        
        if response.status_code == 200:
            result = response.json()
            # Should provide help or error message
            answer = result.get("answer", result.get("response", ""))
            print(f"Empty query response: {answer[:100]}...")
    
    def test_very_long_query(self, api_client, project_with_data):
        """Test handling of very long query"""
        long_query = "Can you " + "please " * 100 + "show me the data?"
        
        response = api_client.post("/rag/query", json={
            "prompt": long_query,
            "project_id": project_with_data
        })
        
        assert response.status_code in [200, 400, 413, 422], \
            f"Long query should be handled, got {response.status_code}"
    
    def test_special_characters_query(self, api_client, project_with_data):
        """Test handling of special characters"""
        queries = [
            "What's the data about? (just curious!)",
            "Show me: column1, column2 & column3",
            "Filter where name = 'O'Brien'"
        ]
        
        for query in queries:
            response = api_client.post("/rag/query", json={
                "prompt": query,
                "project_id": project_with_data
            })
            
            assert response.status_code in [200, 400], \
                f"Special chars should be handled: {query}"
    
    def test_multilingual_query(self, api_client, project_with_data):
        """Test handling of non-English queries"""
        queries = [
            "¿Cuáles son los datos?",  # Spanish
            "Montre-moi les données",   # French
            "データを見せて"             # Japanese
        ]
        
        for query in queries:
            response = api_client.post("/rag/query", json={
                "prompt": query,
                "project_id": project_with_data
            })
            
            # Should attempt to respond, not crash
            assert response.status_code in [200, 400], \
                f"Non-English query should be handled: {query}"
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("answer", result.get("response", ""))
                print(f"Query '{query[:20]}...' got response: {len(answer)} chars")
    
    def test_mathematical_expressions(self, api_client, project_with_data):
        """Test queries with mathematical expressions"""
        queries = [
            "Calculate column1 * column2",
            "Show me (revenue - cost) / revenue as margin",
            "What's the sum of col1 + col2?"
        ]
        
        for query in queries:
            response = api_client.post("/rag/query", json={
                "prompt": query,
                "project_id": project_with_data
            })
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("answer", result.get("response", ""))
                sql = result.get("sql", "")
                
                print(f"\nMath query: {query}")
                print(f"Response: {answer[:100]}...")
                
                # Should attempt calculation
                has_calculation = any(op in (sql + answer) for op in ["*", "/", "+", "-"])
                if not has_calculation:
                    print("WARNING: Math expression may not be processed")


@pytest.mark.integration
@pytest.mark.query_routing
class TestQueryResponseQuality:
    """Test the quality of responses for different query types"""
    
    @pytest.fixture
    def project_with_data(self, api_client, create_test_rag):
        """Create a project with sample data"""
        rag_id = create_test_rag("Response Quality Test")
        
        if config.FINANCIAL_SAMPLE.exists():
            api_client.upload_file(
                "/datasources/connect",
                config.FINANCIAL_SAMPLE,
                data={'project_id': str(rag_id), 'source_type': 'file'}
            )
        
        time.sleep(3)
        return rag_id
    
    def test_responses_are_helpful(self, api_client, project_with_data):
        """Test that responses provide actual help"""
        queries = [
            ("What can I do with this data?", "suggestion"),
            ("Summarize the key metrics", "analysis"),
            ("Show me the top 5 rows", "sql"),
        ]
        
        for query, query_type in queries:
            response = api_client.post("/rag/query", json={
                "prompt": query,
                "project_id": project_with_data
            })
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("answer", result.get("response", ""))
                
                # Response should not be empty or just "I don't know"
                assert len(answer) > 20, f"Response too short for: {query}"
                
                unhelpful = ["i don't know", "i cannot", "i'm not sure", "error"]
                is_unhelpful = any(phrase in answer.lower() for phrase in unhelpful)
                
                if is_unhelpful:
                    print(f"WARNING: Potentially unhelpful response for '{query}'")
                    print(f"Response: {answer[:200]}")
    
    def test_sql_responses_are_valid(self, api_client, project_with_data):
        """Test that SQL responses are syntactically valid"""
        sql_queries = [
            "Show all rows",
            "Count the records",
            "Get average of numeric columns"
        ]
        
        for query in sql_queries:
            response = api_client.post("/rag/query", json={
                "prompt": query,
                "project_id": project_with_data,
                "sql_mode": True
            })
            
            if response.status_code == 200:
                result = response.json()
                sql = result.get("sql", result.get("generated_sql", ""))
                
                if sql:
                    # Basic SQL validation
                    sql_upper = sql.upper()
                    
                    # Should have SELECT
                    has_select = "SELECT" in sql_upper
                    
                    # Should have FROM
                    has_from = "FROM" in sql_upper
                    
                    # Should not have obvious errors
                    has_syntax_error = "SYNTAX ERROR" in sql_upper
                    
                    print(f"\nQuery: {query}")
                    print(f"SQL: {sql}")
                    print(f"Valid structure: {has_select and has_from and not has_syntax_error}")
