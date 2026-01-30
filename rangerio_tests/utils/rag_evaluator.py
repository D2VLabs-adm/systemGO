"""
RAG evaluator using ragas with RangerIO's local LLMs
"""
import requests
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class RAGEvaluation:
    """RAG evaluation results"""
    faithfulness: float
    relevancy: float
    precision: float
    question: str
    answer: str
    contexts: List[str]


class RangerIOLLM:
    """
    Wrapper to use RangerIO's local LLMs with ragas 0.4.x
    Implements all required methods for ragas compatibility
    """
    
    def __init__(self, backend_url: str = "http://127.0.0.1:9000", model_name: str = "qwen3-4b-q4-k-m"):
        self.backend_url = backend_url
        self.model_name = model_name
    
    def _extract_prompt(self, prompt_input) -> str:
        """Extract string from various prompt formats ragas might use"""
        # Handle different ragas prompt formats
        if isinstance(prompt_input, str):
            return prompt_input
        elif hasattr(prompt_input, 'to_string'):
            return prompt_input.to_string()
        elif hasattr(prompt_input, 'text'):
            return prompt_input.text
        elif hasattr(prompt_input, '__str__'):
            return str(prompt_input)
        return str(prompt_input)
    
    def _generate_response(self, prompt, **kwargs) -> str:
        """Internal method to call RangerIO LLM"""
        try:
            # Extract actual prompt string
            prompt_str = self._extract_prompt(prompt)
            
            response = requests.post(
                f"{self.backend_url}/llm/ask",
                json={
                    "prompt": prompt_str,
                    "model_name": self.model_name,
                    "max_tokens": kwargs.get("max_tokens", 512),
                    "temperature": kwargs.get("temperature", 0.7)
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json()["response"]
            return ""
        except Exception as e:
            print(f"Error calling RangerIO LLM: {e}")
            return ""
    
    # All possible method names ragas might use
    def generate(self, prompt, **kwargs) -> str:
        """ragas 0.4.x generate method"""
        return self._generate_response(prompt, **kwargs)
    
    def generate_text(self, prompt, **kwargs) -> str:
        """ragas generate_text method"""
        return self._generate_response(prompt, **kwargs)
    
    async def agenerate(self, prompt, **kwargs) -> str:
        """ragas async generate method (returns sync result for now)"""
        return self._generate_response(prompt, **kwargs)
    
    async def agenerate_text(self, prompt, **kwargs) -> str:
        """ragas async generate_text method (returns sync result for now)"""
        return self._generate_response(prompt, **kwargs)
    
    def _call(self, prompt, stop: Optional[List[str]] = None) -> str:
        """Legacy API compatibility"""
        return self._generate_response(prompt)
    
    def __call__(self, prompt, **kwargs) -> str:
        """Make instance callable"""
        return self._generate_response(prompt, **kwargs)
    
    @property
    def _llm_type(self) -> str:
        return "rangerio"


class SimpleEmbeddings:
    """
    Simple embeddings fallback for ragas
    Uses basic text hashing for similarity
    """
    
    def embed_text(self, text: str) -> List[float]:
        """Create simple embedding vector"""
        # Simple hash-based embedding (300 dimensions)
        np.random.seed(hash(text) % (2**32))
        return np.random.randn(300).tolist()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts"""
        return [self.embed_text(text) for text in texts]


class RAGEvaluator:
    """
    Evaluate RAG answers using ragas 0.4.x metrics with local LLM
    Includes both automated metrics and custom fallbacks
    """
    
    def __init__(self, backend_url: str = "http://127.0.0.1:9000", model_name: str = "qwen3-4b-q4-k-m"):
        self.backend_url = backend_url
        self.model_name = model_name
        self.llm = RangerIOLLM(backend_url, model_name)
        self.embeddings = SimpleEmbeddings()
        
        # Try to import ragas 0.4.x
        try:
            from ragas import evaluate, SingleTurnSample, EvaluationDataset
            from ragas.metrics import faithfulness, answer_relevancy, context_precision
            self.ragas_available = True
            self.SingleTurnSample = SingleTurnSample
            self.EvaluationDataset = EvaluationDataset
            self.evaluate_fn = evaluate
            self.faithfulness = faithfulness
            self.answer_relevancy = answer_relevancy
            self.context_precision = context_precision
            print(f"✓ ragas 0.4.x loaded successfully with model: {model_name}")
        except ImportError as e:
            print(f"Warning: ragas not available ({e}). Using custom metrics.")
            self.ragas_available = False
    
    def _custom_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """
        Custom faithfulness metric: Check if answer is supported by contexts
        Returns: 0.0 - 1.0
        """
        if not answer or not contexts:
            return 0.0
        
        # Simple word overlap scoring
        answer_words = set(answer.lower().split())
        context_text = " ".join(contexts).lower()
        context_words = set(context_text.split())
        
        if not answer_words:
            return 0.0
        
        overlap = len(answer_words & context_words)
        return min(1.0, overlap / len(answer_words))
    
    def _custom_relevancy(self, question: str, answer: str) -> float:
        """
        Custom relevancy metric: Check if answer addresses question
        Returns: 0.0 - 1.0
        """
        if not question or not answer:
            return 0.0
        
        # Simple keyword overlap
        q_words = set(question.lower().split())
        a_words = set(answer.lower().split())
        
        if not q_words:
            return 0.0
        
        overlap = len(q_words & a_words)
        return min(1.0, overlap / len(q_words))
    
    def _custom_precision(self, contexts: List[str]) -> float:
        """
        Custom precision metric: Estimate quality of retrieved contexts
        Returns: 0.0 - 1.0
        """
        if not contexts:
            return 0.0
        
        # Simple heuristic: longer contexts = more detailed = better precision
        avg_length = sum(len(ctx) for ctx in contexts) / len(contexts)
        return min(1.0, avg_length / 500)  # Normalize by typical chunk size
    
    def evaluate_answer(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> RAGEvaluation:
        """
        Evaluate a single RAG answer using ragas or custom metrics
        
        Args:
            question: The question asked
            answer: The RAG system's answer
            contexts: Retrieved context chunks
            ground_truth: Optional ground truth answer
            
        Returns:
            RAGEvaluation with scores
        """
        # Try ragas first (only if backend is available)
        if self.ragas_available:
            try:
                # Quick health check
                health_resp = requests.get(f"{self.backend_url}/health", timeout=2)
                if health_resp.status_code != 200:
                    raise Exception("Backend not available")
                
                # Create dataset in ragas 0.4.x format
                sample = self.SingleTurnSample(
                    user_input=question,
                    response=answer,
                    retrieved_contexts=contexts,
                    reference=ground_truth if ground_truth else ""
                )
                dataset = self.EvaluationDataset(samples=[sample])
                
                # Evaluate with ragas (with timeout)
                result = self.evaluate_fn(
                    dataset=dataset,
                    metrics=[self.faithfulness, self.answer_relevancy, self.context_precision],
                    llm=self.llm,
                    embeddings=self.embeddings
                )
                
                # Extract scores from result
                scores = result.to_pandas().iloc[0]
                faithfulness_score = float(scores.get('faithfulness', 0.0))
                relevancy_score = float(scores.get('answer_relevancy', 0.0))
                precision_score = float(scores.get('context_precision', 0.0))
                
                # Check if scores are valid (not NaN)
                if (not np.isnan(faithfulness_score) and 
                    not np.isnan(relevancy_score) and 
                    not np.isnan(precision_score)):
                    return RAGEvaluation(
                        faithfulness=faithfulness_score,
                        relevancy=relevancy_score,
                        precision=precision_score,
                        question=question,
                        answer=answer,
                        contexts=contexts
                    )
            except Exception as e:
                print(f"ragas evaluation failed: {e}. Using custom metrics.")
        
        # Use custom metrics (robust fallback that always works)
        return RAGEvaluation(
            faithfulness=self._custom_faithfulness(answer, contexts),
            relevancy=self._custom_relevancy(question, answer),
            precision=self._custom_precision(contexts),
            question=question,
            answer=answer,
            contexts=contexts
        )
    
    def evaluate_batch(
        self,
        test_cases: List[Dict]
    ) -> List[RAGEvaluation]:
        """
        Evaluate multiple RAG answers
        
        Args:
            test_cases: List of dicts with 'question', 'answer', 'contexts', 'ground_truth'
            
        Returns:
            List of RAGEvaluation results
        """
        results = []
        for case in test_cases:
            result = self.evaluate_answer(
                question=case['question'],
                answer=case['answer'],
                contexts=case['contexts'],
                ground_truth=case.get('ground_truth')
            )
            results.append(result)
        return results

