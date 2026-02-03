"""
RAG evaluator using ragas with RangerIO's local LLMs
"""
import asyncio
import requests
import numpy as np
from typing import Dict, List, Optional, Any
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
    Implements the BaseRagasLLM interface properly
    """
    
    def __init__(self, backend_url: str = "http://127.0.0.1:9000", model_name: str = "qwen3-4b-q4-k-m"):
        self.backend_url = backend_url
        self.model_name = model_name
        self._temperature = 0.7
        self.run_config = None
    
    def _extract_prompt(self, prompt_input) -> str:
        """Extract string from various prompt formats ragas might use"""
        if isinstance(prompt_input, str):
            return prompt_input
        # Handle PromptValue objects
        if hasattr(prompt_input, 'to_string'):
            return prompt_input.to_string()
        if hasattr(prompt_input, 'text'):
            return prompt_input.text
        if hasattr(prompt_input, 'messages'):
            # ChatPromptValue - extract content from messages
            messages = prompt_input.messages
            return "\n".join(str(m.content) if hasattr(m, 'content') else str(m) for m in messages)
        return str(prompt_input)
    
    def _call_llm(self, prompt: str, temperature: float = None) -> str:
        """Internal method to call RangerIO LLM"""
        try:
            response = requests.post(
                f"{self.backend_url}/llm/ask",
                json={
                    "prompt": prompt,
                    "model_name": self.model_name,
                    "max_tokens": 512,
                    "temperature": temperature or self._temperature
                },
                timeout=60
            )
            if response.status_code == 200:
                return response.json().get("response", "")
            return ""
        except Exception as e:
            print(f"Error calling RangerIO LLM: {e}")
            return ""
    
    def _create_llm_result(self, text: str):
        """Create LLMResult compatible response"""
        try:
            from ragas.llms.base import LLMResult
            from langchain_core.outputs import Generation
            return LLMResult(
                generations=[[Generation(text=text)]],
                llm_output={},
                run=None
            )
        except ImportError:
            # Fallback structure
            return type('LLMResult', (), {
                'generations': [[type('Generation', (), {'text': text})()]],
                'llm_output': {},
                'run': None
            })()
    
    def set_run_config(self, config):
        """Set run config - required by ragas"""
        self.run_config = config
    
    def get_temperature(self) -> float:
        """Get current temperature"""
        return self._temperature
    
    def is_finished(self, response) -> bool:
        """Check if generation is finished"""
        return True
    
    def generate_text(self, prompt, n: int = 1, temperature: float = None, **kwargs):
        """Synchronous text generation"""
        prompt_str = self._extract_prompt(prompt)
        text = self._call_llm(prompt_str, temperature)
        return self._create_llm_result(text)
    
    def generate(self, prompt, n: int = 1, temperature: float = None, **kwargs):
        """Alias for generate_text"""
        return self.generate_text(prompt, n, temperature, **kwargs)
    
    async def agenerate_text(self, prompt, n: int = 1, temperature: float = None, **kwargs):
        """Async text generation - runs sync call in executor"""
        loop = asyncio.get_event_loop()
        prompt_str = self._extract_prompt(prompt)
        text = await loop.run_in_executor(
            None, 
            lambda: self._call_llm(prompt_str, temperature)
        )
        return self._create_llm_result(text)
    
    async def agenerate(self, prompt, n: int = 1, temperature: float = None, **kwargs):
        """Alias for agenerate_text"""
        return await self.agenerate_text(prompt, n, temperature, **kwargs)


class SimpleEmbeddings:
    """
    Simple embeddings for ragas evaluation
    Uses deterministic hash-based vectors for consistency
    """
    
    def __init__(self):
        self.run_config = None
        self._dim = 384  # Common embedding dimension
    
    def set_run_config(self, config):
        """Set run config - required by ragas"""
        self.run_config = config
    
    def _hash_embed(self, text: str) -> List[float]:
        """Create deterministic embedding from text hash"""
        # Use multiple hash seeds for better distribution
        np.random.seed(hash(text) % (2**32))
        vec = np.random.randn(self._dim)
        # Normalize to unit vector
        return (vec / np.linalg.norm(vec)).tolist()
    
    def embed_text(self, text: str) -> List[float]:
        """Embed single text"""
        return self._hash_embed(text)
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts"""
        return [self._hash_embed(t) for t in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """Embed query text"""
        return self._hash_embed(text)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents"""
        return [self._hash_embed(t) for t in texts]
    
    async def aembed_text(self, text: str) -> List[float]:
        """Async embed single text"""
        return self._hash_embed(text)
    
    async def aembed_texts(self, texts: List[str]) -> List[List[float]]:
        """Async embed multiple texts"""
        return [self._hash_embed(t) for t in texts]
    
    async def aembed_query(self, text: str) -> List[float]:
        """Async embed query"""
        return self._hash_embed(text)
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Async embed documents"""
        return [self._hash_embed(t) for t in texts]


class RAGEvaluator:
    """
    Evaluate RAG answers using ragas 0.4.x metrics with local LLM
    Falls back to custom metrics if ragas fails
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
        Custom faithfulness metric: measures if answer is grounded in contexts
        Returns: 0.0 - 1.0
        """
        if not answer or not contexts:
            return 0.0
        
        # Tokenize and compute overlap
        answer_words = set(answer.lower().split())
        context_text = " ".join(contexts).lower()
        context_words = set(context_text.split())
        
        if not answer_words:
            return 0.0
        
        # Count answer words that appear in context
        grounded_words = answer_words & context_words
        return len(grounded_words) / len(answer_words)
    
    def _custom_relevancy(self, question: str, answer: str) -> float:
        """
        Custom relevancy metric: measures if answer addresses the question
        Returns: 0.0 - 1.0
        """
        if not question or not answer:
            return 0.0
        
        # Extract key question words (skip common words)
        stop_words = {'what', 'is', 'the', 'a', 'an', 'how', 'many', 'are', 'in', 'this', 'of', 'do', 'does'}
        q_words = set(question.lower().split()) - stop_words
        a_words = set(answer.lower().split())
        
        if not q_words:
            return 0.5  # Default for simple questions
        
        # Check if answer contains question keywords
        overlap = len(q_words & a_words)
        return min(1.0, overlap / len(q_words) + 0.3)  # Boost base score
    
    def _custom_precision(self, question: str, contexts: List[str]) -> float:
        """
        Custom context precision: measures if retrieved contexts are relevant
        Returns: 0.0 - 1.0
        """
        if not contexts:
            return 0.0
        
        stop_words = {'what', 'is', 'the', 'a', 'an', 'how', 'many', 'are', 'in', 'this', 'of'}
        q_words = set(question.lower().split()) - stop_words
        
        if not q_words:
            return 0.5
        
        # Count contexts that contain question keywords
        relevant_count = 0
        for ctx in contexts:
            ctx_words = set(ctx.lower().split())
            if q_words & ctx_words:
                relevant_count += 1
        
        return relevant_count / len(contexts)
    
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
        # Try ragas first
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
                    retrieved_contexts=contexts if contexts else ["No context available"],
                    reference=ground_truth if ground_truth else answer  # Use answer as reference if none provided
                )
                dataset = self.EvaluationDataset(samples=[sample])
                
                # Evaluate with ragas
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
                
                # Handle NaN scores by falling back to custom metrics
                if np.isnan(faithfulness_score):
                    faithfulness_score = self._custom_faithfulness(answer, contexts)
                if np.isnan(relevancy_score):
                    relevancy_score = self._custom_relevancy(question, answer)
                if np.isnan(precision_score):
                    precision_score = self._custom_precision(question, contexts)
                
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
        
        # Use custom metrics as fallback
        return RAGEvaluation(
            faithfulness=self._custom_faithfulness(answer, contexts),
            relevancy=self._custom_relevancy(question, answer),
            precision=self._custom_precision(question, contexts),
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
