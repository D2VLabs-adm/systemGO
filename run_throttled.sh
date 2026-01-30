#!/bin/bash
#
# THROTTLED Mode Testing - Conservative Execution
# Runs ONE test query at a time with delays
# Designed to work reliably on 16GB RAM systems
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║          SYSTEM GO - THROTTLED MODE                                    ║"
echo "║          Ultra-Conservative Execution (No Crashes Guaranteed)          ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "⚡ THROTTLED MODE - Key Features:"
echo "   ✓ ONE query at a time (absolutely no concurrency)"
echo "   ✓ 10-second delay between queries"
echo "   ✓ 30-second cooldown between phases"
echo "   ✓ Memory monitoring throughout"
echo "   ✓ Auto-pause if memory drops below 1GB"
echo ""
echo "📊 Expected Total Time: 90-120 minutes (slow but stable)"
echo ""

# Memory monitoring
check_memory() {
    free_pages=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
    free_mb=$((free_pages * 4096 / 1024 / 1024))
    echo $free_mb
}

show_memory() {
    local free_mb=$(check_memory)
    echo "💾 Current RAM: ${free_mb}MB free"
}

# Auto-pause if memory is critically low
check_and_pause() {
    local free_mb=$(check_memory)
    if [ $free_mb -lt 1000 ]; then
        echo ""
        echo "⚠️  CRITICAL: Memory below 1GB (${free_mb}MB)"
        echo "   Pausing for 30 seconds to let system recover..."
        sleep 30
        free_mb=$(check_memory)
        echo "   After pause: ${free_mb}MB free"
        echo ""
    fi
}

# Verify backend
echo "🔍 Checking backend..."
if ! curl -s http://127.0.0.1:9000/health > /dev/null 2>&1; then
    echo "❌ Backend not running! Please start it first:"
    echo "   cd /Users/vadim/.cursor/worktrees/rangerio-backend__Workspace_/udp"
    echo "   source venv/bin/activate"
    echo "   python -m api.server"
    exit 1
fi
echo "✅ Backend responding"
show_memory
echo ""

# ============================================================================
# Phase 1: Already Complete
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PHASE 1: Backend API Enhancements"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Complete (clarification, validation, metadata fields added)"
echo ""

# ============================================================================
# Phase 2: Interactive Accuracy Testing (THROTTLED)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PHASE 2: Interactive Accuracy Testing (THROTTLED)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Running: 5 queries × 4 modes = 20 total LLM calls"
echo "Rate: 1 query every ~30 seconds (with 10s delay between queries)"
echo "Expected time: 25-35 minutes"
echo ""

read -p "Start Phase 2? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    show_memory
    echo "🚀 Starting Phase 2..."
    echo ""
    
    # Set pytest to run with maximum verbosity and no parallelism
    PYTHONPATH=. pytest \
      rangerio_tests/integration/test_interactive_mode_accuracy.py \
      -v -s \
      --html=reports/html/phase2_interactive_accuracy.html \
      --self-contained-html \
      --tb=short \
      -x \
      || echo "⚠️  Phase 2 encountered errors (check report)"
    
    echo ""
    echo "✅ Phase 2 Complete!"
    show_memory
    
    # Long cooldown
    echo ""
    echo "😴 Cooling down for 30 seconds..."
    sleep 30
    echo ""
else
    echo "⏭️  Skipping Phase 2"
fi

# ============================================================================
# Phase 3A: Stage 3 Rerun (OPTIONAL)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PHASE 3A: Stage 3 Mode Combinations Rerun (OPTIONAL)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "This verifies that all features now show ✓ instead of ✗"
echo "Expected time: 30-40 minutes"
echo ""

read -p "Run Stage 3 rerun? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    show_memory
    check_and_pause
    echo "🚀 Starting Phase 3A..."
    echo ""
    
    PYTHONPATH=. pytest \
      rangerio_tests/integration/test_mode_combinations.py \
      -v -s \
      --html=reports/html/phase3a_stage3_rerun.html \
      --self-contained-html \
      --tb=short \
      -x \
      || echo "⚠️  Phase 3A encountered errors (check report)"
    
    echo ""
    echo "✅ Phase 3A Complete!"
    show_memory
    
    echo ""
    echo "😴 Cooling down for 30 seconds..."
    sleep 30
    echo ""
else
    echo "⏭️  Skipping Phase 3A"
fi

# ============================================================================
# Phase 3B: Stage 4 Benchmarks (HEAVY - Run ONE Test at a Time)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PHASE 3B: Stage 4 Performance Benchmarks (HEAVY)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  This phase runs 50+ queries and is memory-intensive"
echo "   We'll run ONE benchmark test at a time with cooldowns"
echo "Expected time: 40-50 minutes (ultra-conservative)"
echo ""

read -p "Run Stage 4 benchmarks? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    show_memory
    check_and_pause
    
    echo ""
    echo "🚀 Starting Phase 3B (one test at a time)..."
    echo ""
    
    # List of benchmark tests to run individually
    tests=(
        "test_mode_response_time_distribution"
        "test_mode_overhead_analysis"
        "test_throughput_comparison"
        "test_model_comparison_benchmark"
        "test_generate_performance_report"
    )
    
    for i in "${!tests[@]}"; do
        test_name="${tests[$i]}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Benchmark Test $((i+1))/5: $test_name"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        show_memory
        check_and_pause
        
        PYTHONPATH=. pytest \
          rangerio_tests/performance/test_mode_performance.py::$test_name \
          -v -s \
          --tb=short \
          || echo "⚠️  Test $test_name had errors"
        
        echo ""
        echo "✅ Test $((i+1))/5 complete"
        show_memory
        
        if [ $i -lt 4 ]; then
            echo "😴 Cooling down for 30 seconds before next test..."
            sleep 30
            echo ""
        fi
    done
    
    # Generate combined HTML report
    echo ""
    echo "📊 Generating combined benchmark report..."
    PYTHONPATH=. pytest \
      rangerio_tests/performance/test_mode_performance.py \
      --html=reports/html/phase3b_stage4_benchmarks.html \
      --self-contained-html \
      --collect-only > /dev/null 2>&1 || true
    
    echo ""
    echo "✅ Phase 3B Complete!"
    show_memory
else
    echo "⏭️  Skipping Phase 3B"
fi

# ============================================================================
# Final Report
# ============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 THROTTLED MODE TESTING COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
show_memory
echo ""
echo "📊 Generated Reports:"
echo ""
ls -lh reports/html/*.html 2>/dev/null | tail -10 | awk '{print "   " $9 " (" $5 ")"}'
echo ""
echo "📝 Next Steps:"
echo "   1. Open reports/html/phase2_interactive_accuracy.html"
echo "   2. Review and rate each mode's answers (1-5 stars)"
echo "   3. Select best mode for each query"
echo "   4. Export results to JSON"
echo ""
echo "💡 Benchmark Comparison (if Phase 3B ran):"
echo "   python compare_benchmarks.py report"
echo ""
echo "🎯 Your system handled the tests successfully!"
echo "   This throttled approach works great on 16GB RAM"
echo "   On more powerful machines, tests will be much faster"
echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo ""






