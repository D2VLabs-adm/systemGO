"""
Diagnostic Reporter for RangerIO Performance Optimization

Generates actionable reports with specific recommendations for improving
backend performance based on profiling data.

The recommendations are based on:
1. Timing breakdown analysis
2. Memory usage patterns
3. Error rate analysis
4. Industry best practices for RAG systems
"""
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from .performance_diagnostics import PerformanceDiagnostics, Bottleneck, Recommendation


# ============================================================================
# Optimization Knowledge Base
# ============================================================================

# Thresholds for different severity levels
THRESHOLDS = {
    "response_time": {
        "excellent": 10000,   # < 10s
        "good": 20000,        # < 20s
        "acceptable": 45000,  # < 45s
        "poor": 90000,        # < 90s
    },
    "memory_growth": {
        "stable": 50,         # < 50MB
        "minor": 200,         # < 200MB
        "concerning": 500,    # < 500MB
    },
    "error_rate": {
        "excellent": 1,       # < 1%
        "good": 5,            # < 5%
        "acceptable": 10,     # < 10%
    },
    "llm_time_pct": {
        "optimal": 50,        # < 50%
        "acceptable": 70,     # < 70%
        "concerning": 85,     # < 85%
    }
}

# Optimization suggestions by category
OPTIMIZATION_SUGGESTIONS = {
    "llm_inference": {
        "high_impact": [
            {
                "suggestion": "Switch to a smaller model",
                "details": "Consider Qwen 1.5B or Phi-3-mini instead of larger models. "
                          "Expect 2-3x speedup with minimal quality loss for most queries.",
                "implementation": "Update DEFAULT_MODEL in config/settings.py",
                "estimated_improvement": "50-70% faster inference"
            },
            {
                "suggestion": "Enable response streaming",
                "details": "Stream tokens as they're generated for better perceived performance. "
                          "Users see results faster even if total time is the same.",
                "implementation": "Set stream=True in LLM call, update frontend to handle SSE",
                "estimated_improvement": "80%+ improvement in time-to-first-token"
            },
            {
                "suggestion": "Use more aggressive quantization",
                "details": "Switch from Q4_K_M to Q4_K_S or even Q4_0. "
                          "Smaller memory footprint and faster inference.",
                "implementation": "Download Q4_K_S variant of your model",
                "estimated_improvement": "10-20% faster, 20% less memory"
            },
        ],
        "medium_impact": [
            {
                "suggestion": "Reduce max_tokens",
                "details": "Limit response length from 2048 to 512-1024 tokens. "
                          "Most queries don't need long responses.",
                "implementation": "Set max_tokens=1024 in LLM config",
                "estimated_improvement": "20-40% faster for long responses"
            },
            {
                "suggestion": "Optimize prompt template",
                "details": "Shorter system prompts = faster processing. "
                          "Remove verbose instructions, keep only essential guidance.",
                "implementation": "Review and trim prompts in api/llm.py",
                "estimated_improvement": "5-15% faster"
            },
            {
                "suggestion": "Cache repeated queries",
                "details": "Implement semantic similarity cache for near-duplicate queries.",
                "implementation": "Add LRU cache with embedding-based similarity check",
                "estimated_improvement": "100% faster for cache hits"
            },
        ]
    },
    "vector_retrieval": {
        "high_impact": [
            {
                "suggestion": "Reduce top_k retrieval count",
                "details": "Lower top_k from 10-20 to 3-5. Most relevant context is in top results. "
                          "Use reranking instead of retrieving more chunks.",
                "implementation": "Set top_k=5 in RAG query config",
                "estimated_improvement": "30-50% faster retrieval"
            },
            {
                "suggestion": "Add reranking layer",
                "details": "Use a small reranker model (e.g., BAAI/bge-reranker-base) to filter "
                          "retrieved chunks before sending to LLM. Better quality with fewer chunks.",
                "implementation": "Add reranker after vector search, before LLM",
                "estimated_improvement": "Better quality + 20% less LLM input"
            },
        ],
        "medium_impact": [
            {
                "suggestion": "Use HNSW index",
                "details": "Ensure ChromaDB/vector store is using HNSW index for approximate search. "
                          "Much faster than exact search for large collections.",
                "implementation": "Check ChromaDB config, enable HNSW if not active",
                "estimated_improvement": "10-100x faster for large indexes"
            },
            {
                "suggestion": "Cache embeddings",
                "details": "Cache query embeddings to avoid re-computing for similar queries.",
                "implementation": "Add embedding cache with TTL",
                "estimated_improvement": "50ms+ per query saved"
            },
        ]
    },
    "database": {
        "high_impact": [
            {
                "suggestion": "Add database indexes",
                "details": "Index frequently queried columns: project_id, data_source_id, created_at.",
                "implementation": "CREATE INDEX on key columns in SQLite",
                "estimated_improvement": "10-100x faster for filtered queries"
            },
            {
                "suggestion": "Use connection pooling",
                "details": "Reuse database connections instead of creating new ones per request.",
                "implementation": "Already using SQLAlchemy pool - verify pool_size settings",
                "estimated_improvement": "5-20ms per query saved"
            },
        ],
        "medium_impact": [
            {
                "suggestion": "Cache metadata",
                "details": "Cache frequently accessed metadata (project info, data source stats).",
                "implementation": "Add TTL cache for /projects and /datasources endpoints",
                "estimated_improvement": "Reduce DB load by 30-50%"
            },
        ]
    },
    "memory": {
        "high_impact": [
            {
                "suggestion": "Implement response cache limits",
                "details": "Add LRU eviction to response caches. Unbounded caches lead to memory leaks.",
                "implementation": "Use functools.lru_cache with maxsize or cachetools.TTLCache",
                "estimated_improvement": "Stable memory usage"
            },
            {
                "suggestion": "Unload models when idle",
                "details": "Unload LLM after periods of inactivity to free memory.",
                "implementation": "Add idle timeout in model_backends/factory.py",
                "estimated_improvement": "2-4GB freed when idle"
            },
        ],
        "medium_impact": [
            {
                "suggestion": "Force garbage collection",
                "details": "Call gc.collect() after large operations (imports, batch queries).",
                "implementation": "Add gc.collect() in cleanup paths",
                "estimated_improvement": "Faster memory reclamation"
            },
            {
                "suggestion": "Stream large files during import",
                "details": "Process files in chunks instead of loading entirely into memory.",
                "implementation": "Use pandas read_csv(chunksize=...) for large files",
                "estimated_improvement": "Handle files larger than RAM"
            },
        ]
    },
    "concurrency": {
        "high_impact": [
            {
                "suggestion": "Implement LLM request queue",
                "details": "Queue LLM requests instead of running all concurrently. "
                          "LLM can only process one request efficiently at a time.",
                "implementation": "Add asyncio.Queue or threading.Queue for LLM requests",
                "estimated_improvement": "Stable performance under load"
            },
            {
                "suggestion": "Add request timeout with fallback",
                "details": "Timeout long-running requests gracefully instead of letting them block.",
                "implementation": "Add timeout parameter with graceful degradation response",
                "estimated_improvement": "Better UX under load"
            },
        ],
        "medium_impact": [
            {
                "suggestion": "Rate limit concurrent requests",
                "details": "Limit concurrent LLM requests to 2-3 max to prevent resource exhaustion.",
                "implementation": "Use semaphore or rate limiter middleware",
                "estimated_improvement": "Prevent cascading failures"
            },
        ]
    }
}


# ============================================================================
# Diagnostic Reporter
# ============================================================================

class DiagnosticReporter:
    """
    Generates actionable diagnostic reports from performance data.
    """
    
    def __init__(self, diagnostics: PerformanceDiagnostics):
        self.diagnostics = diagnostics
    
    def generate_recommendations(self) -> List[Recommendation]:
        """Generate prioritized recommendations based on identified bottlenecks."""
        recommendations = []
        bottlenecks = self.diagnostics.identify_bottlenecks()
        breakdown = self.diagnostics.calculate_breakdown_averages()
        
        priority = 1
        
        for bottleneck in bottlenecks:
            # Map bottleneck to recommendations
            if bottleneck.type == "llm_bottleneck":
                suggestions = OPTIMIZATION_SUGGESTIONS["llm_inference"]
                impact = "high" if bottleneck.severity == "high" else "medium"
                
                for sugg in suggestions.get("high_impact", [])[:2]:  # Top 2 high impact
                    recommendations.append(Recommendation(
                        priority=priority,
                        category="LLM Inference",
                        issue=bottleneck.description,
                        impact=impact,
                        current_state=f"LLM takes {breakdown.get('llm_avg_ms', 0)/1000:.1f}s average ({breakdown.get('llm_pct', 0):.0f}% of total)",
                        suggestions=[sugg["suggestion"]],
                        estimated_improvement=sugg["estimated_improvement"]
                    ))
                    priority += 1
            
            elif bottleneck.type == "retrieval_bottleneck":
                suggestions = OPTIMIZATION_SUGGESTIONS["vector_retrieval"]
                
                for sugg in suggestions.get("high_impact", [])[:1]:
                    recommendations.append(Recommendation(
                        priority=priority,
                        category="Vector Retrieval",
                        issue=bottleneck.description,
                        impact="medium",
                        current_state=f"Retrieval takes {breakdown.get('retrieval_avg_ms', 0)/1000:.1f}s average",
                        suggestions=[sugg["suggestion"]],
                        estimated_improvement=sugg["estimated_improvement"]
                    ))
                    priority += 1
            
            elif bottleneck.type == "memory_growth":
                suggestions = OPTIMIZATION_SUGGESTIONS["memory"]
                
                for sugg in suggestions.get("high_impact", [])[:1]:
                    memory = self.diagnostics.analyze_memory_trend()
                    recommendations.append(Recommendation(
                        priority=priority,
                        category="Memory Management",
                        issue=bottleneck.description,
                        impact=bottleneck.severity,
                        current_state=f"Memory: {memory.get('baseline_mb', 0):.0f}MB → {memory.get('final_mb', 0):.0f}MB",
                        suggestions=[sugg["suggestion"]],
                        estimated_improvement=sugg["estimated_improvement"]
                    ))
                    priority += 1
            
            elif bottleneck.type == "high_error_rate":
                suggestions = OPTIMIZATION_SUGGESTIONS["concurrency"]
                
                for sugg in suggestions.get("high_impact", [])[:1]:
                    recommendations.append(Recommendation(
                        priority=priority,
                        category="Concurrency & Reliability",
                        issue=bottleneck.description,
                        impact="high",
                        current_state=f"Error rate: {bottleneck.metric_value:.0f}%",
                        suggestions=[sugg["suggestion"]],
                        estimated_improvement=sugg["estimated_improvement"]
                    ))
                    priority += 1
            
            elif bottleneck.type == "high_variance":
                recommendations.append(Recommendation(
                    priority=priority,
                    category="Response Consistency",
                    issue=bottleneck.description,
                    impact="medium",
                    current_state="High variance between P50 and P95",
                    suggestions=["Investigate cold start behavior", "Add request warming"],
                    estimated_improvement="More consistent response times"
                ))
                priority += 1
        
        return recommendations
    
    def generate_text_report(self) -> str:
        """Generate a formatted text report."""
        summary = self.diagnostics.get_summary()
        recommendations = self.generate_recommendations()
        
        lines = []
        
        # Header
        lines.append("═" * 70)
        lines.append("RANGERIO PERFORMANCE DIAGNOSTIC REPORT")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("═" * 70)
        lines.append("")
        
        # Test Summary
        lines.append("📊 TEST SUMMARY")
        lines.append("─" * 40)
        perc = summary["percentiles"]
        lines.append(f"   Queries executed: {summary['query_count']}")
        lines.append(f"   Success rate: {summary['success_rate']:.1f}%")
        lines.append(f"   Duration: {summary['duration_s']:.1f}s")
        lines.append("")
        
        # Response Times
        lines.append("⏱️  RESPONSE TIMES")
        lines.append("─" * 40)
        if perc["count"] > 0:
            p50_status = "✓" if perc["p50"] < THRESHOLDS["response_time"]["good"] else "✗"
            p95_status = "✓" if perc["p95"] < THRESHOLDS["response_time"]["acceptable"] else "✗"
            lines.append(f"   P50: {perc['p50']/1000:.1f}s {p50_status}")
            lines.append(f"   P95: {perc['p95']/1000:.1f}s {p95_status}")
            lines.append(f"   P99: {perc['p99']/1000:.1f}s")
            lines.append(f"   Mean: {perc['mean']/1000:.1f}s (±{perc['stdev']/1000:.1f}s)")
        else:
            lines.append("   No query data available")
        lines.append("")
        
        # Timing Breakdown
        lines.append("📈 TIMING BREAKDOWN")
        lines.append("─" * 40)
        breakdown = summary["breakdown"]
        if breakdown.get("llm_pct", 0) > 0:
            lines.append(f"   {'Component':<20} {'Time':<10} {'%':<10}")
            lines.append(f"   {'─'*40}")
            
            llm_bar = "█" * int(breakdown["llm_pct"] / 5) + "░" * (20 - int(breakdown["llm_pct"] / 5))
            ret_bar = "█" * int(breakdown["retrieval_pct"] / 5) + "░" * (20 - int(breakdown["retrieval_pct"] / 5))
            db_bar = "█" * int(breakdown["database_pct"] / 5) + "░" * (20 - int(breakdown["database_pct"] / 5))
            
            lines.append(f"   LLM Inference      {breakdown.get('llm_avg_ms', 0)/1000:>6.1f}s    {llm_bar} {breakdown['llm_pct']:.0f}%")
            lines.append(f"   Vector Retrieval   {breakdown.get('retrieval_avg_ms', 0)/1000:>6.1f}s    {ret_bar} {breakdown['retrieval_pct']:.0f}%")
            lines.append(f"   Database           {breakdown.get('database_avg_ms', 0)/1000:>6.1f}s    {db_bar} {breakdown['database_pct']:.0f}%")
        else:
            lines.append("   No breakdown data available (backend timing info not provided)")
        lines.append("")
        
        # Memory
        lines.append("💾 MEMORY USAGE")
        lines.append("─" * 40)
        memory = summary["memory"]
        trend_icon = "📈" if memory.get("trend") == "growing" else ("📉" if memory.get("trend") == "shrinking" else "➡️")
        lines.append(f"   Baseline: {memory.get('baseline_mb', 0):.0f}MB")
        lines.append(f"   Peak: {memory.get('peak_mb', 0):.0f}MB")
        lines.append(f"   Final: {memory.get('final_mb', 0):.0f}MB")
        lines.append(f"   Trend: {trend_icon} {memory.get('trend', 'unknown')} ({memory.get('growth_mb', 0):+.0f}MB)")
        lines.append("")
        
        # Bottlenecks
        lines.append("🔍 IDENTIFIED BOTTLENECKS")
        lines.append("─" * 40)
        if summary["bottlenecks"]:
            for i, bn in enumerate(summary["bottlenecks"], 1):
                severity_icon = "🔴" if bn["severity"] == "high" else ("🟡" if bn["severity"] == "medium" else "🟢")
                lines.append(f"   {i}. {severity_icon} [{bn['severity'].upper()}] {bn['type']}")
                lines.append(f"      {bn['description']}")
                if bn["causes"]:
                    lines.append(f"      Likely causes:")
                    for cause in bn["causes"][:3]:
                        lines.append(f"        • {cause}")
                lines.append("")
        else:
            lines.append("   ✓ No significant bottlenecks identified")
        lines.append("")
        
        # Recommendations
        lines.append("💡 RECOMMENDATIONS")
        lines.append("═" * 70)
        if recommendations:
            for rec in recommendations[:5]:  # Top 5 recommendations
                impact_icon = "🔴" if rec.impact == "high" else ("🟡" if rec.impact == "medium" else "🟢")
                lines.append(f"\n   {rec.priority}. {impact_icon} {rec.category}")
                lines.append(f"      Issue: {rec.issue}")
                lines.append(f"      Current: {rec.current_state}")
                lines.append(f"      Suggestion: {rec.suggestions[0]}")
                lines.append(f"      Expected improvement: {rec.estimated_improvement}")
        else:
            lines.append("   ✓ No recommendations - performance looks good!")
        
        lines.append("")
        lines.append("═" * 70)
        
        return "\n".join(lines)
    
    def generate_json_report(self) -> Dict[str, Any]:
        """Generate a JSON report for programmatic use."""
        summary = self.diagnostics.get_summary()
        recommendations = self.generate_recommendations()
        
        return {
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "recommendations": [
                {
                    "priority": r.priority,
                    "category": r.category,
                    "issue": r.issue,
                    "impact": r.impact,
                    "current_state": r.current_state,
                    "suggestions": r.suggestions,
                    "estimated_improvement": r.estimated_improvement
                }
                for r in recommendations
            ],
            "optimization_suggestions": OPTIMIZATION_SUGGESTIONS
        }
    
    def save_report(self, output_dir: Path, format: str = "both") -> Dict[str, Path]:
        """Save report to files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        paths = {}
        
        if format in ["text", "both"]:
            text_path = output_dir / f"diagnostic_report_{timestamp}.txt"
            text_path.write_text(self.generate_text_report())
            paths["text"] = text_path
        
        if format in ["json", "both"]:
            json_path = output_dir / f"diagnostic_report_{timestamp}.json"
            json_path.write_text(json.dumps(self.generate_json_report(), indent=2))
            paths["json"] = json_path
        
        return paths


# ============================================================================
# Utility Functions
# ============================================================================

def print_diagnostic_report(diagnostics: PerformanceDiagnostics):
    """Print a diagnostic report to console."""
    reporter = DiagnosticReporter(diagnostics)
    print(reporter.generate_text_report())


def get_quick_recommendations(diagnostics: PerformanceDiagnostics) -> List[str]:
    """Get a quick list of top recommendations."""
    reporter = DiagnosticReporter(diagnostics)
    recommendations = reporter.generate_recommendations()
    
    return [
        f"[{r.impact.upper()}] {r.suggestions[0]} → {r.estimated_improvement}"
        for r in recommendations[:3]
    ]
