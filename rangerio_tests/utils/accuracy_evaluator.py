"""
Accuracy Evaluator for RangerIO User Scenario Tests
====================================================

Provides AI-powered validation of RAG responses to ensure:
1. Factual accuracy (response matches data)
2. Query relevance (response answers the question)
3. Hallucination detection (no unsupported claims)
4. Logical reasoning (calculations/comparisons are valid)

Uses the RangerIO backend's own LLM for evaluation to keep tests self-contained.
"""

import json
import re
import logging
import requests
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger("rangerio_tests.accuracy")


class QueryType(Enum):
    """Types of queries for categorized testing"""
    CONTENT_LOOKUP = "content_lookup"      # "What products are listed?"
    AGGREGATION = "aggregation"            # "What is the total revenue?"
    CALCULATION = "calculation"            # "What is the average margin %?"
    CROSS_FIELD_LOGIC = "cross_field"      # "Which region has highest X but lowest Y?"
    TREND_ANALYSIS = "trend"               # "How did Q4 compare to Q3?"
    COMPLEX_REASONING = "complex"          # Multi-step reasoning required


class AccuracyVerdict(Enum):
    """Accuracy evaluation verdicts"""
    ACCURATE = "accurate"           # Response is correct
    PARTIALLY_ACCURATE = "partial"  # Some correct, some issues
    INACCURATE = "inaccurate"       # Response is wrong
    HALLUCINATED = "hallucinated"   # Contains unsupported claims
    NO_ANSWER = "no_answer"         # Model refused to answer
    ERROR = "error"                 # Evaluation failed


@dataclass
class QuerySpec:
    """Specification for a test query with validation criteria"""
    query: str
    query_type: QueryType
    description: str = ""
    
    # Pattern-based validation
    must_contain: List[str] = field(default_factory=list)
    must_not_contain: List[str] = field(default_factory=list)
    must_contain_pattern: Optional[str] = None  # Regex pattern
    
    # Numeric validation
    expected_number_range: Optional[tuple] = None  # (min, max)
    
    # Custom validator function
    custom_validator: Optional[Callable[[str], bool]] = None
    
    # Whether to use AI evaluation
    use_ai_eval: bool = True
    
    # Expected response time (seconds)
    max_response_time: float = 90.0


@dataclass
class EvaluationResult:
    """Result of evaluating a single query response"""
    query: str
    query_type: str
    response: str
    response_time_s: float
    
    # Validation results
    verdict: AccuracyVerdict
    accuracy_score: float  # 0-10
    relevance_score: float  # 0-10
    
    # Detailed checks
    pattern_checks_passed: bool = True
    contains_required: List[str] = field(default_factory=list)
    missing_required: List[str] = field(default_factory=list)
    contains_forbidden: List[str] = field(default_factory=list)
    
    # AI evaluation details
    ai_evaluation: Optional[Dict[str, Any]] = None
    
    # Issues found
    issues: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['verdict'] = self.verdict.value
        result['query_type'] = self.query_type
        return result
    
    @property
    def passed(self) -> bool:
        """Whether this evaluation passed"""
        return self.verdict in [AccuracyVerdict.ACCURATE, AccuracyVerdict.PARTIALLY_ACCURATE]


@dataclass
class BatchResult:
    """Result of a complete test batch"""
    batch_name: str
    data_source: str
    total_queries: int
    passed_queries: int
    failed_queries: int
    
    total_time_s: float
    avg_response_time_s: float
    avg_accuracy_score: float
    avg_relevance_score: float
    
    results: List[EvaluationResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "batch_name": self.batch_name,
            "data_source": self.data_source,
            "summary": {
                "total_queries": self.total_queries,
                "passed": self.passed_queries,
                "failed": self.failed_queries,
                "pass_rate": f"{(self.passed_queries/self.total_queries)*100:.1f}%" if self.total_queries > 0 else "N/A",
            },
            "timing": {
                "total_time_s": round(self.total_time_s, 2),
                "avg_response_time_s": round(self.avg_response_time_s, 2),
            },
            "quality": {
                "avg_accuracy_score": round(self.avg_accuracy_score, 2),
                "avg_relevance_score": round(self.avg_relevance_score, 2),
            },
            "results": [r.to_dict() for r in self.results]
        }


class AccuracyEvaluator:
    """
    Evaluates RAG response accuracy using pattern matching and AI evaluation.
    """
    
    def __init__(self, backend_url: str = "http://127.0.0.1:9000"):
        self.backend_url = backend_url
        self.logger = logging.getLogger("rangerio_tests.accuracy")
    
    def evaluate_response(
        self,
        query_spec: QuerySpec,
        response: str,
        response_time: float,
        data_context: Optional[str] = None
    ) -> EvaluationResult:
        """
        Evaluate a single response against the query specification.
        
        Args:
            query_spec: The query specification with validation criteria
            response: The actual response from the RAG system
            response_time: Time taken to get the response (seconds)
            data_context: Optional context about the data for AI evaluation
        
        Returns:
            EvaluationResult with detailed evaluation metrics
        """
        result = EvaluationResult(
            query=query_spec.query,
            query_type=query_spec.query_type.value,
            response=response[:2000],  # Truncate for storage
            response_time_s=response_time,
            verdict=AccuracyVerdict.ACCURATE,
            accuracy_score=10.0,
            relevance_score=10.0,
        )
        
        # Check for no answer / refusal
        if self._is_no_answer(response):
            result.verdict = AccuracyVerdict.NO_ANSWER
            result.accuracy_score = 0.0
            result.relevance_score = 0.0
            result.issues.append("Model refused to answer or said 'I don't know'")
            return result
        
        # Pattern-based validation
        self._check_patterns(query_spec, response, result)
        
        # AI evaluation if enabled
        if query_spec.use_ai_eval:
            self._ai_evaluate(query_spec, response, data_context, result)
        
        # Calculate final verdict
        self._calculate_verdict(result)
        
        return result
    
    def _is_no_answer(self, response: str) -> bool:
        """Check if response is a refusal or non-answer"""
        no_answer_patterns = [
            r"i don'?t know",
            r"cannot determine",
            r"no information available",
            r"unable to find",
            r"not enough context",
            r"data does not contain",
        ]
        response_lower = response.lower()
        return any(re.search(p, response_lower) for p in no_answer_patterns)
    
    def _check_patterns(self, spec: QuerySpec, response: str, result: EvaluationResult):
        """Check pattern-based validation criteria"""
        response_lower = response.lower()
        
        # Check must_contain
        for required in spec.must_contain:
            if required.lower() in response_lower:
                result.contains_required.append(required)
            else:
                result.missing_required.append(required)
                result.issues.append(f"Missing required term: '{required}'")
        
        # Check must_not_contain
        for forbidden in spec.must_not_contain:
            if forbidden.lower() in response_lower:
                result.contains_forbidden.append(forbidden)
                result.issues.append(f"Contains forbidden term: '{forbidden}'")
        
        # Check regex pattern
        if spec.must_contain_pattern:
            if not re.search(spec.must_contain_pattern, response, re.IGNORECASE):
                result.issues.append(f"Missing required pattern: {spec.must_contain_pattern}")
                result.pattern_checks_passed = False
        
        # Check numeric range if specified
        if spec.expected_number_range:
            numbers = re.findall(r'[\d,]+\.?\d*', response.replace(',', ''))
            if numbers:
                try:
                    found_num = float(numbers[0])
                    min_val, max_val = spec.expected_number_range
                    if not (min_val <= found_num <= max_val):
                        result.issues.append(
                            f"Number {found_num} outside expected range [{min_val}, {max_val}]"
                        )
                except ValueError:
                    pass
        
        # Custom validator
        if spec.custom_validator:
            try:
                if not spec.custom_validator(response):
                    result.issues.append("Custom validation failed")
            except Exception as e:
                result.issues.append(f"Custom validator error: {e}")
        
        # Update pattern check status
        result.pattern_checks_passed = (
            len(result.missing_required) == 0 and
            len(result.contains_forbidden) == 0
        )
    
    def _ai_evaluate(
        self,
        spec: QuerySpec,
        response: str,
        data_context: Optional[str],
        result: EvaluationResult
    ):
        """Use AI to evaluate response accuracy"""
        eval_prompt = f"""You are evaluating a data analysis response for accuracy.

ORIGINAL QUERY: {spec.query}
QUERY TYPE: {spec.query_type.value}

RESPONSE TO EVALUATE:
{response[:1500]}

{f"DATA CONTEXT (for reference): {data_context[:1000]}" if data_context else ""}

Evaluate the response on these criteria:
1. ACCURACY (1-10): Is the response factually correct? Does it use real data?
2. RELEVANCE (1-10): Does it directly answer the question asked?
3. HALLUCINATION: Does it make claims not supported by data? (true/false)
4. LOGICAL: Is the reasoning/calculation logical? (true/false)

Return ONLY valid JSON (no markdown, no explanation):
{{"accuracy": 8, "relevance": 9, "hallucinated": false, "logical": true, "issues": []}}
"""
        
        try:
            # Use the RangerIO backend's LLM for evaluation
            eval_response = requests.post(
                f"{self.backend_url}/llm/generate",
                json={
                    "prompt": eval_prompt,
                    "max_tokens": 200,
                    "temperature": 0.1  # Low temp for consistent evaluation
                },
                timeout=60
            )
            
            if eval_response.status_code == 200:
                eval_text = eval_response.json().get("response", "")
                
                # Extract JSON from response
                json_match = re.search(r'\{[^}]+\}', eval_text)
                if json_match:
                    ai_result = json.loads(json_match.group())
                    result.ai_evaluation = ai_result
                    
                    # Update scores from AI evaluation
                    if "accuracy" in ai_result:
                        result.accuracy_score = min(10, max(0, float(ai_result["accuracy"])))
                    if "relevance" in ai_result:
                        result.relevance_score = min(10, max(0, float(ai_result["relevance"])))
                    if ai_result.get("hallucinated"):
                        result.issues.append("AI detected potential hallucination")
                    if ai_result.get("logical") is False:
                        result.issues.append("AI detected illogical reasoning")
                    if ai_result.get("issues"):
                        result.issues.extend(ai_result["issues"])
            else:
                self.logger.warning(f"AI evaluation failed: {eval_response.status_code}")
                
        except requests.exceptions.Timeout:
            self.logger.warning("AI evaluation timed out")
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse AI evaluation: {e}")
        except Exception as e:
            self.logger.warning(f"AI evaluation error: {e}")
    
    def _calculate_verdict(self, result: EvaluationResult):
        """Calculate final verdict based on all checks"""
        # Check for hallucination
        if result.ai_evaluation and result.ai_evaluation.get("hallucinated"):
            result.verdict = AccuracyVerdict.HALLUCINATED
            return
        
        # Check accuracy thresholds
        if result.accuracy_score >= 7 and result.relevance_score >= 7:
            if len(result.issues) == 0:
                result.verdict = AccuracyVerdict.ACCURATE
            else:
                result.verdict = AccuracyVerdict.PARTIALLY_ACCURATE
        elif result.accuracy_score >= 4:
            result.verdict = AccuracyVerdict.PARTIALLY_ACCURATE
        else:
            result.verdict = AccuracyVerdict.INACCURATE


class StructuredReporter:
    """
    Generates structured output reports for test results.
    """
    
    def __init__(self, output_dir: str = "reports/user_scenarios"):
        self.output_dir = output_dir
        import os
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_batch_report(self, batch_result: BatchResult) -> str:
        """Generate a structured report for a single batch"""
        import os
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_dir}/batch_{batch_result.batch_name}_{timestamp}.json"
        
        report = batch_result.to_dict()
        report["generated_at"] = datetime.now().isoformat()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        return filename
    
    def generate_summary_report(self, all_batches: List[BatchResult]) -> str:
        """Generate a summary report across all batches"""
        import os
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_dir}/summary_{timestamp}.json"
        
        total_queries = sum(b.total_queries for b in all_batches)
        total_passed = sum(b.passed_queries for b in all_batches)
        total_time = sum(b.total_time_s for b in all_batches)
        
        summary = {
            "generated_at": datetime.now().isoformat(),
            "overall": {
                "total_batches": len(all_batches),
                "total_queries": total_queries,
                "total_passed": total_passed,
                "total_failed": total_queries - total_passed,
                "pass_rate": f"{(total_passed/total_queries)*100:.1f}%" if total_queries > 0 else "N/A",
                "total_time_s": round(total_time, 2),
            },
            "by_query_type": self._aggregate_by_type(all_batches),
            "batches": [b.to_dict() for b in all_batches]
        }
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return filename
    
    def _aggregate_by_type(self, batches: List[BatchResult]) -> Dict[str, Any]:
        """Aggregate results by query type"""
        by_type: Dict[str, List[EvaluationResult]] = {}
        
        for batch in batches:
            for result in batch.results:
                qtype = result.query_type
                if qtype not in by_type:
                    by_type[qtype] = []
                by_type[qtype].append(result)
        
        aggregated = {}
        for qtype, results in by_type.items():
            passed = sum(1 for r in results if r.passed)
            aggregated[qtype] = {
                "total": len(results),
                "passed": passed,
                "failed": len(results) - passed,
                "pass_rate": f"{(passed/len(results))*100:.1f}%",
                "avg_accuracy": round(sum(r.accuracy_score for r in results) / len(results), 2),
                "avg_response_time_s": round(sum(r.response_time_s for r in results) / len(results), 2),
            }
        
        return aggregated
    
    def print_console_summary(self, batch_result: BatchResult):
        """Print a formatted summary to console"""
        print("\n" + "="*70)
        print(f"  BATCH: {batch_result.batch_name}")
        print(f"  Data Source: {batch_result.data_source}")
        print("="*70)
        
        print(f"\n  📊 SUMMARY")
        print(f"     Queries: {batch_result.total_queries}")
        print(f"     Passed:  {batch_result.passed_queries} ✓")
        print(f"     Failed:  {batch_result.failed_queries} ✗")
        rate = (batch_result.passed_queries/batch_result.total_queries)*100 if batch_result.total_queries > 0 else 0
        status = "✓" if rate >= 80 else "⚠" if rate >= 60 else "✗"
        print(f"     Rate:    {rate:.1f}% {status}")
        
        print(f"\n  ⏱️  TIMING")
        print(f"     Total:   {batch_result.total_time_s:.1f}s")
        print(f"     Average: {batch_result.avg_response_time_s:.1f}s per query")
        
        print(f"\n  🎯 QUALITY")
        print(f"     Accuracy:  {batch_result.avg_accuracy_score:.1f}/10")
        print(f"     Relevance: {batch_result.avg_relevance_score:.1f}/10")
        
        print(f"\n  📋 DETAILS")
        for i, r in enumerate(batch_result.results, 1):
            status = "✓" if r.passed else "✗"
            print(f"     {i}. [{status}] {r.query_type}: {r.query[:50]}...")
            if r.issues:
                for issue in r.issues[:2]:
                    print(f"        └─ {issue}")
        
        print("\n" + "="*70)
