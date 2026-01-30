"""
RangerIO Test Utilities

This module provides utilities for testing and performance analysis:
- performance_diagnostics: Collect timing and memory data during tests
- diagnostic_reporter: Generate optimization recommendations from test data
"""

from .performance_diagnostics import (
    PerformanceDiagnostics,
    QueryTiming,
    MemorySnapshot,
    Bottleneck,
    Recommendation,
)

from .diagnostic_reporter import (
    DiagnosticReporter,
    print_diagnostic_report,
    get_quick_recommendations,
    OPTIMIZATION_SUGGESTIONS,
)

__all__ = [
    # Diagnostics
    "PerformanceDiagnostics",
    "QueryTiming", 
    "MemorySnapshot",
    "Bottleneck",
    "Recommendation",
    # Reporter
    "DiagnosticReporter",
    "print_diagnostic_report",
    "get_quick_recommendations",
    "OPTIMIZATION_SUGGESTIONS",
]
