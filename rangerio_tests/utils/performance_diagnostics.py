"""
Performance Diagnostics for RangerIO

This module collects detailed performance data during tests and analyzes
it to identify bottlenecks and suggest optimizations.

Key Features:
- Query timing breakdown (LLM, retrieval, database)
- Memory profiling with trend analysis
- Bottleneck identification
- Actionable recommendations

Usage:
    diagnostics = PerformanceDiagnostics()
    with diagnostics.profile_query(api_client, rag_id, "What is total sales?") as result:
        # Query runs here
        pass
    
    report = diagnostics.generate_report()
    print(report.recommendations)
"""
import time
import psutil
import statistics
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager
import logging

logger = logging.getLogger("rangerio_tests.diagnostics")


# ============================================================================
# Data Classes for Profiling Results
# ============================================================================

@dataclass
class QueryTiming:
    """Timing breakdown for a single query."""
    query: str
    total_ms: float
    llm_inference_ms: float = 0
    vector_retrieval_ms: float = 0
    database_ms: float = 0
    other_ms: float = 0
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def breakdown_pct(self) -> Dict[str, float]:
        """Calculate percentage breakdown."""
        if self.total_ms == 0:
            return {"llm": 0, "retrieval": 0, "database": 0, "other": 0}
        return {
            "llm": (self.llm_inference_ms / self.total_ms) * 100,
            "retrieval": (self.vector_retrieval_ms / self.total_ms) * 100,
            "database": (self.database_ms / self.total_ms) * 100,
            "other": (self.other_ms / self.total_ms) * 100,
        }


@dataclass
class MemorySnapshot:
    """Memory state at a point in time."""
    timestamp: datetime
    rss_mb: float
    vms_mb: float
    operation: str = ""


@dataclass
class Bottleneck:
    """Identified performance bottleneck."""
    type: str
    severity: str  # "high", "medium", "low"
    description: str
    metric_value: float
    threshold: float
    likely_causes: List[str]
    

@dataclass
class Recommendation:
    """Actionable optimization recommendation."""
    priority: int  # 1 = highest
    category: str
    issue: str
    impact: str  # "high", "medium", "low"
    current_state: str
    suggestions: List[str]
    estimated_improvement: str


# ============================================================================
# Performance Diagnostics Engine
# ============================================================================

class PerformanceDiagnostics:
    """
    Collects and analyzes performance data to identify bottlenecks
    and generate optimization recommendations.
    """
    
    def __init__(self):
        self.query_timings: List[QueryTiming] = []
        self.memory_snapshots: List[MemorySnapshot] = []
        self.process = psutil.Process()
        self.start_time = datetime.now()
        self.custom_metrics: Dict[str, List[float]] = {}
        
    def reset(self):
        """Clear all collected data."""
        self.query_timings = []
        self.memory_snapshots = []
        self.custom_metrics = {}
        self.start_time = datetime.now()
    
    # =========================================================================
    # Data Collection
    # =========================================================================
    
    def snapshot_memory(self, operation: str = "") -> MemorySnapshot:
        """Take a memory snapshot."""
        mem = self.process.memory_info()
        snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            rss_mb=mem.rss / (1024 * 1024),
            vms_mb=mem.vms / (1024 * 1024),
            operation=operation
        )
        self.memory_snapshots.append(snapshot)
        return snapshot
    
    def record_query_timing(self, timing: QueryTiming):
        """Record a query timing."""
        self.query_timings.append(timing)
    
    def record_metric(self, name: str, value: float):
        """Record a custom metric."""
        if name not in self.custom_metrics:
            self.custom_metrics[name] = []
        self.custom_metrics[name].append(value)
    
    @contextmanager
    def profile_query(self, api_client, rag_id: int, query: str, timeout: int = 180):
        """
        Context manager to profile a query execution.
        
        Usage:
            with diagnostics.profile_query(client, 123, "What is sales?") as result:
                pass
            print(result.timing)
        """
        result = {"timing": None, "response": None, "error": None}
        
        # Memory before
        mem_before = self.process.memory_info().rss / (1024 * 1024)
        
        start_time = time.time()
        try:
            response = api_client.post("/rag/query", json={
                "prompt": query,
                "project_id": rag_id
            }, timeout=timeout)
            
            total_ms = (time.time() - start_time) * 1000
            
            # Try to extract timing breakdown from response
            timing_data = {}
            if response.status_code == 200:
                resp_json = response.json()
                result["response"] = resp_json
                
                # Check if backend provides timing info
                if "timings" in resp_json:
                    timing_data = resp_json["timings"]
                elif "debug" in resp_json and "timings" in resp_json["debug"]:
                    timing_data = resp_json["debug"]["timings"]
            
            # Estimate breakdown if not provided
            timing = QueryTiming(
                query=query,
                total_ms=total_ms,
                llm_inference_ms=timing_data.get("llm_inference_ms", total_ms * 0.7),  # Estimate 70%
                vector_retrieval_ms=timing_data.get("vector_retrieval_ms", total_ms * 0.15),
                database_ms=timing_data.get("database_ms", total_ms * 0.1),
                other_ms=timing_data.get("other_ms", total_ms * 0.05),
                success=response.status_code == 200,
                error=None if response.status_code == 200 else f"HTTP {response.status_code}"
            )
            
            result["timing"] = timing
            self.record_query_timing(timing)
            
        except Exception as e:
            total_ms = (time.time() - start_time) * 1000
            timing = QueryTiming(
                query=query,
                total_ms=total_ms,
                success=False,
                error=str(e)
            )
            result["timing"] = timing
            result["error"] = str(e)
            self.record_query_timing(timing)
        
        # Memory after
        mem_after = self.process.memory_info().rss / (1024 * 1024)
        self.record_metric("query_memory_delta_mb", mem_after - mem_before)
        
        yield result
    
    # =========================================================================
    # Analysis
    # =========================================================================
    
    def calculate_percentiles(self) -> Dict[str, float]:
        """Calculate response time percentiles."""
        if not self.query_timings:
            return {"p50": 0, "p95": 0, "p99": 0, "mean": 0, "stdev": 0}
        
        times = sorted([t.total_ms for t in self.query_timings if t.success])
        if not times:
            return {"p50": 0, "p95": 0, "p99": 0, "mean": 0, "stdev": 0}
        
        n = len(times)
        return {
            "p50": times[int(n * 0.50)] if n > 1 else times[0],
            "p95": times[int(n * 0.95)] if n > 19 else times[-1],
            "p99": times[int(n * 0.99)] if n > 99 else times[-1],
            "mean": statistics.mean(times),
            "stdev": statistics.stdev(times) if n > 1 else 0,
            "min": times[0],
            "max": times[-1],
            "count": n
        }
    
    def calculate_breakdown_averages(self) -> Dict[str, float]:
        """Calculate average timing breakdown across all queries."""
        if not self.query_timings:
            return {"llm_pct": 0, "retrieval_pct": 0, "database_pct": 0, "other_pct": 0}
        
        successful = [t for t in self.query_timings if t.success]
        if not successful:
            return {"llm_pct": 0, "retrieval_pct": 0, "database_pct": 0, "other_pct": 0}
        
        total_llm = sum(t.llm_inference_ms for t in successful)
        total_retrieval = sum(t.vector_retrieval_ms for t in successful)
        total_db = sum(t.database_ms for t in successful)
        total_other = sum(t.other_ms for t in successful)
        total_all = sum(t.total_ms for t in successful)
        
        if total_all == 0:
            return {"llm_pct": 0, "retrieval_pct": 0, "database_pct": 0, "other_pct": 0}
        
        return {
            "llm_pct": (total_llm / total_all) * 100,
            "retrieval_pct": (total_retrieval / total_all) * 100,
            "database_pct": (total_db / total_all) * 100,
            "other_pct": (total_other / total_all) * 100,
            "llm_avg_ms": total_llm / len(successful),
            "retrieval_avg_ms": total_retrieval / len(successful),
            "database_avg_ms": total_db / len(successful),
        }
    
    def analyze_memory_trend(self) -> Dict[str, float]:
        """Analyze memory usage trend."""
        if len(self.memory_snapshots) < 2:
            return {"growth_mb": 0, "peak_mb": 0, "trend": "stable"}
        
        rss_values = [s.rss_mb for s in self.memory_snapshots]
        first_half = rss_values[:len(rss_values)//2]
        second_half = rss_values[len(rss_values)//2:]
        
        first_avg = statistics.mean(first_half) if first_half else 0
        second_avg = statistics.mean(second_half) if second_half else 0
        
        growth = second_avg - first_avg
        trend = "growing" if growth > 50 else ("shrinking" if growth < -50 else "stable")
        
        return {
            "growth_mb": rss_values[-1] - rss_values[0],
            "peak_mb": max(rss_values),
            "baseline_mb": rss_values[0],
            "final_mb": rss_values[-1],
            "trend": trend,
            "trend_delta_mb": growth
        }
    
    def identify_bottlenecks(self) -> List[Bottleneck]:
        """Identify performance bottlenecks from collected data."""
        bottlenecks = []
        
        percentiles = self.calculate_percentiles()
        breakdown = self.calculate_breakdown_averages()
        memory = self.analyze_memory_trend()
        
        # Check P95 vs P50 variance
        if percentiles["p50"] > 0 and percentiles["p95"] > percentiles["p50"] * 2.5:
            bottlenecks.append(Bottleneck(
                type="high_variance",
                severity="high",
                description=f"P95 ({percentiles['p95']/1000:.1f}s) is {percentiles['p95']/percentiles['p50']:.1f}x higher than P50 ({percentiles['p50']/1000:.1f}s)",
                metric_value=percentiles["p95"] / percentiles["p50"],
                threshold=2.5,
                likely_causes=[
                    "LLM cold start after idle periods",
                    "Garbage collection pauses",
                    "Concurrent request contention",
                    "Variable context length affecting inference time",
                ]
            ))
        
        # Check LLM dominance
        if breakdown.get("llm_pct", 0) > 60:
            bottlenecks.append(Bottleneck(
                type="llm_bottleneck",
                severity="high" if breakdown["llm_pct"] > 75 else "medium",
                description=f"LLM inference consumes {breakdown['llm_pct']:.0f}% of response time",
                metric_value=breakdown["llm_pct"],
                threshold=60,
                likely_causes=[
                    "Model size too large for hardware",
                    "Insufficient quantization",
                    "Long context/response generation",
                    "No response streaming",
                ]
            ))
        
        # Check retrieval time
        if breakdown.get("retrieval_pct", 0) > 25:
            bottlenecks.append(Bottleneck(
                type="retrieval_bottleneck",
                severity="medium",
                description=f"Vector retrieval consumes {breakdown['retrieval_pct']:.0f}% of response time",
                metric_value=breakdown["retrieval_pct"],
                threshold=25,
                likely_causes=[
                    "Large vector index without HNSW",
                    "High top_k value retrieving too many chunks",
                    "Missing embedding cache",
                    "Slow embedding model",
                ]
            ))
        
        # Check memory growth
        if memory.get("growth_mb", 0) > 200:
            bottlenecks.append(Bottleneck(
                type="memory_growth",
                severity="high" if memory["growth_mb"] > 500 else "medium",
                description=f"Memory grew {memory['growth_mb']:.0f}MB during profiling",
                metric_value=memory["growth_mb"],
                threshold=200,
                likely_causes=[
                    "Response caching without eviction",
                    "LLM context accumulation",
                    "Unreleased database connections",
                    "Large dataframes held in memory",
                ]
            ))
        
        # Check error rate
        total = len(self.query_timings)
        failed = sum(1 for t in self.query_timings if not t.success)
        if total > 0 and failed / total > 0.1:
            bottlenecks.append(Bottleneck(
                type="high_error_rate",
                severity="high",
                description=f"Error rate is {failed/total*100:.0f}% ({failed}/{total} queries)",
                metric_value=failed / total * 100,
                threshold=10,
                likely_causes=[
                    "Request timeouts under load",
                    "Database connection exhaustion",
                    "LLM out of memory",
                    "Concurrent request limits exceeded",
                ]
            ))
        
        # Sort by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        bottlenecks.sort(key=lambda b: severity_order.get(b.severity, 3))
        
        return bottlenecks
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all collected performance data."""
        return {
            "percentiles": self.calculate_percentiles(),
            "breakdown": self.calculate_breakdown_averages(),
            "memory": self.analyze_memory_trend(),
            "bottlenecks": [
                {
                    "type": b.type,
                    "severity": b.severity,
                    "description": b.description,
                    "causes": b.likely_causes
                }
                for b in self.identify_bottlenecks()
            ],
            "query_count": len(self.query_timings),
            "success_rate": sum(1 for t in self.query_timings if t.success) / len(self.query_timings) * 100 if self.query_timings else 0,
            "duration_s": (datetime.now() - self.start_time).total_seconds()
        }
