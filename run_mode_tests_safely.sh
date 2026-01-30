#!/bin/bash
# Safe Staggered Mode Testing Runner
# Runs mode tests in 4 stages with cooldown periods to prevent system overload

set -e  # Exit on error

cd "/Users/vadim/.cursor/worktrees/Validator/SYSTEM GO"
source venv/bin/activate

echo ""
echo "🧪 SYSTEM GO - Mode Tests (Safe Staggered Execution)"
echo "========================================================"
echo "Total: 25 tests across 4 stages"
echo "Estimated time: 30-45 minutes"
echo ""

# Check if backend is running
echo "🔍 Checking backend status..."
if ! curl -s http://127.0.0.1:9000/health > /dev/null 2>&1; then
    echo "❌ Backend not running on port 9000"
    echo "Please start the backend first:"
    echo "  cd /Users/vadim/.cursor/worktrees/rangerio-backend__Workspace_/udp"
    echo "  source venv/bin/activate"
    echo "  python -m api.server"
    exit 1
fi
echo "✅ Backend is running"
echo ""

# Create reports directory
mkdir -p reports/html

# Stage 1: Assistant Mode Tests (6 tests, ~3-5 min)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 STAGE 1/4: Assistant Mode Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Tests: 6 (clarification, confidence, constraints, hallucination, performance, comparison)"
echo "Expected time: 3-5 minutes"
echo ""

PYTHONPATH=. pytest rangerio_tests/integration/test_assistant_mode.py -v \
  --html=reports/html/1_assistant_mode.html \
  --self-contained-html \
  --tb=short

echo ""
echo "✅ Stage 1 Complete! Cooling down..."
sleep 10
echo ""

# Stage 2: Deep Search Mode Tests (6 tests, ~5-8 min)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 STAGE 2/4: Deep Search Mode Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Tests: 6 (compound queries, validation, map-reduce, hierarchical, performance, comparison)"
echo "Expected time: 5-8 minutes"
echo ""

PYTHONPATH=. pytest rangerio_tests/integration/test_deep_search_mode.py -v \
  --html=reports/html/2_deep_search_mode.html \
  --self-contained-html \
  --tb=short

echo ""
echo "✅ Stage 2 Complete! Cooling down..."
sleep 10
echo ""

# Stage 3: Mode Combination Tests (8 tests, ~8-12 min)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 STAGE 3/4: Mode Combination Matrix Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Tests: 8 (query matrix, comparison, feature matrix, performance)"
echo "Expected time: 8-12 minutes"
echo ""

PYTHONPATH=. pytest rangerio_tests/integration/test_mode_combinations.py -v \
  --html=reports/html/3_mode_combinations.html \
  --self-contained-html \
  --tb=short

echo ""
echo "✅ Stage 3 Complete! Cooling down..."
sleep 10
echo ""

# Stage 4: Performance Benchmarks (5 tests, ~15-20 min) - HEAVY
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 STAGE 4/4: Performance Benchmarks (HEAVY - This takes longest)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Tests: 5 (response time distribution, overhead, throughput, model comparison, report)"
echo "Expected time: 15-20 minutes"
echo "⚠️  This stage runs 50+ queries per mode for statistical analysis"
echo ""

PYTHONPATH=. pytest rangerio_tests/performance/test_mode_performance.py -v \
  --html=reports/html/4_performance_benchmarks.html \
  --self-contained-html \
  --tb=short

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ALL MODE TESTS COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 HTML Reports Generated:"
echo "  1. Assistant Mode:      file://$(pwd)/reports/html/1_assistant_mode.html"
echo "  2. Deep Search Mode:    file://$(pwd)/reports/html/2_deep_search_mode.html"
echo "  3. Mode Combinations:   file://$(pwd)/reports/html/3_mode_combinations.html"
echo "  4. Performance:         file://$(pwd)/reports/html/4_performance_benchmarks.html"
echo ""
echo "🎉 Testing complete! Open the HTML reports above to review results."
echo ""






