"""
Integration tests for RAG evaluation using ragas
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from rangerio_tests.utils.rag_evaluator import RAGEvaluator, RAGEvaluation


@pytest.mark.integration
class TestRAGEvaluation:
    """Test RAG answer quality using ragas metrics"""
    
    def test_rag_evaluator_initialization(self):
        """Test that RAG evaluator initializes"""
        evaluator = RAGEvaluator()
        assert evaluator is not None
        assert evaluator.backend_url == "http://127.0.0.1:9000"
    
    def test_evaluate_simple_answer(self):
        """Test evaluating a simple RAG answer"""
        evaluator = RAGEvaluator()
        
        # Simple test case
        question = "What is the capital of France?"
        answer = "The capital of France is Paris."
        contexts = [
            "Paris is the capital and most populous city of France.",
            "France is a country in Western Europe with Paris as its capital."
        ]
        
        result = evaluator.evaluate_answer(
            question=question,
            answer=answer,
            contexts=contexts
        )
        
        assert isinstance(result, RAGEvaluation)
        assert result.question == question
        assert result.answer == answer
        assert result.contexts == contexts
        # Scores should be between 0 and 1
        assert 0 <= result.faithfulness <= 1
        assert 0 <= result.relevancy <= 1
        assert 0 <= result.precision <= 1
    
    def test_evaluate_factual_answer(self):
        """Test RAG evaluation with factual data"""
        evaluator = RAGEvaluator()
        
        # Data analysis question
        question = "How many rows are in the dataset?"
        answer = "The dataset contains 100 rows."
        contexts = [
            "Dataset Statistics:\n- Total Rows: 100\n- Total Columns: 9",
            "The data file has 100 records with 9 fields each."
        ]
        
        result = evaluator.evaluate_answer(
            question=question,
            answer=answer,
            contexts=contexts,
            ground_truth="100 rows"
        )
        
        assert result.faithfulness >= 0.5, "Factual answer should have decent faithfulness"
        assert result.relevancy >= 0.5, "Relevant answer expected"
        print(f"\n✅ RAG Evaluation Scores:")
        print(f"   Faithfulness: {result.faithfulness:.2f}")
        print(f"   Relevancy: {result.relevancy:.2f}")
        print(f"   Precision: {result.precision:.2f}")
    
    def test_evaluate_poor_answer(self):
        """Test RAG evaluation with answer not supported by context"""
        evaluator = RAGEvaluator()
        
        question = "What is the average salary?"
        answer = "The average salary is $500,000."  # Not in context
        contexts = [
            "The dataset contains salary information ranging from $30,000 to $150,000.",
            "Employee salaries vary by role and experience."
        ]
        
        result = evaluator.evaluate_answer(
            question=question,
            answer=answer,
            contexts=contexts
        )
        
        # Faithfulness should be lower since answer isn't supported by context
        print(f"\n⚠️ Poor Answer Evaluation:")
        print(f"   Faithfulness: {result.faithfulness:.2f} (should be lower)")
        print(f"   Relevancy: {result.relevancy:.2f}")
    
    def test_evaluate_batch(self):
        """Test batch evaluation of multiple answers"""
        evaluator = RAGEvaluator()
        
        test_cases = [
            {
                "question": "What types of data are in the dataset?",
                "answer": "The dataset contains numerical, categorical, and date information.",
                "contexts": [
                    "Dataset columns: id (integer), name (string), age (integer), category (string), join_date (date)",
                ],
                "ground_truth": "Mixed data types including integers, strings, and dates"
            },
            {
                "question": "Are there any missing values?",
                "answer": "Yes, there are some missing values in the dataset.",
                "contexts": [
                    "Data quality check found 5% missing values in the 'age' column.",
                    "The 'category' column has 2% null values."
                ]
            }
        ]
        
        results = evaluator.evaluate_batch(test_cases)
        
        assert len(results) == 2
        for i, result in enumerate(results):
            print(f"\n📊 Test Case {i+1}:")
            print(f"   Question: {result.question}")
            print(f"   Faithfulness: {result.faithfulness:.2f}")
            print(f"   Relevancy: {result.relevancy:.2f}")
            print(f"   Precision: {result.precision:.2f}")
            
            # All scores should be valid
            assert isinstance(result, RAGEvaluation)
            assert 0 <= result.faithfulness <= 1
            assert 0 <= result.relevancy <= 1
            assert 0 <= result.precision <= 1
    
    @pytest.mark.slow
    def test_rag_evaluation_end_to_end(self, api_client, create_test_rag, sample_csv_small):
        """Test RAG evaluation with actual RangerIO RAG query"""
        # Create RAG and upload data
        rag_id = create_test_rag("RAG Eval Test")
        
        # Upload data
        upload_response = api_client.upload_file(
            "/datasources/connect",
            sample_csv_small,
            data={'project_id': str(rag_id), 'source_type': 'file'}
        )
        assert upload_response.status_code == 200
        
        # Query RAG
        query_response = api_client.post("/rag/query", json={
            "prompt": "How many people are in this dataset?",
            "project_id": rag_id
        })
        
        if query_response.status_code == 200:
            result = query_response.json()
            answer = result.get("response", "")
            contexts = result.get("contexts", [])
            
            # Evaluate the answer
            evaluator = RAGEvaluator()
            evaluation = evaluator.evaluate_answer(
                question="How many people are in this dataset?",
                answer=answer,
                contexts=contexts
            )
            
            print(f"\n🎯 End-to-End RAG Evaluation:")
            print(f"   Answer: {answer[:100]}...")
            print(f"   Contexts: {len(contexts)} chunks")
            print(f"   Faithfulness: {evaluation.faithfulness:.2f}")
            print(f"   Relevancy: {evaluation.relevancy:.2f}")
            print(f"   Precision: {evaluation.precision:.2f}")
            
            # Should have reasonable scores
            assert evaluation.faithfulness >= 0.3, "Faithfulness too low"
            assert evaluation.relevancy >= 0.3, "Relevancy too low"








