#!/bin/bash
#
# SAFE Mode Testing - Prevents Memory Crashes
# Runs tests sequentially with memory checks and cooldowns
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║          SYSTEM GO - SAFE MODE (Memory-Conscious)                      ║"
echo "║          Prevents Crashes on Systems with Limited RAM                  ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "⚠️  This system has experienced memory crashes during heavy testing."
echo "   Running in SAFE MODE with:"
echo "   - Memory checks before each phase"
echo "   - Longer cooldown periods"
echo "   - Sequential test execution (no parallel)"
echo "   - Option to skip heavy tests"
echo ""

# Check available memory
check_memory() {
    free_pages=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
    free_mb=$((free_pages * 4096 / 1024 / 1024))
    echo $free_mb
}

# Function to wait for user confirmation if memory is low
check_memory_and_confirm() {
    local phase_name=$1
    local free_mb=$(check_memory)
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Memory Check Before: $phase_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Available RAM: ${free_mb}MB"
    
    if [ $free_mb -lt 1500 ]; then
        echo "❌ WARNING: Low memory (<1.5GB free)"
        echo "   Recommendation: Close other applications or skip this phase"
        echo ""
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "⏭️  Skipping $phase_name"
            return 1
        fi
    elif [ $free_mb -lt 3000 ]; then
        echo "⚠️  Moderate memory (${free_mb}MB free)"
        echo "   Tests will run but may be slow"
    else
        echo "✅ Good memory (${free_mb}MB free)"
    fi
    
    echo ""
    return 0
}

# Cooldown between phases
cooldown() {
    local seconds=$1
    echo ""
    echo "😴 Cooldown period: ${seconds}s (letting system recover memory)..."
    sleep $seconds
    echo ""
}

# ============================================================================
# Phase 1: Already Complete
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PHASE 1: Backend API Enhancements"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Already complete (backend has new fields)"
echo ""

# Verify backend
if ! curl -s http://127.0.0.1:9000/health > /dev/null 2>&1; then
    echo "❌ Backend not running! Starting it..."
    cd /Users/vadim/.cursor/worktrees/rangerio-backend__Workspace_/udp
    source venv/bin/activate
    nohup python -m api.server > /tmp/rangerio_backend_safe.log 2>&1 &
    cd "$SCRIPT_DIR"
    source venv/bin/activate
    sleep 15
fi

if curl -s http://127.0.0.1:9000/health > /dev/null 2>&1; then
    echo "✅ Backend responding"
else
    echo "❌ Backend failed to start!"
    exit 1
fi

cooldown 5

# ============================================================================
# Phase 2: Interactive Accuracy Testing (LIGHT)
# ============================================================================
if check_memory_and_confirm "Phase 2: Interactive Accuracy Testing"; then
    echo "Running: 5 queries × 4 modes = 20 LLM calls"
    echo "Expected time: 15-25 minutes"
    echo "Memory impact: MODERATE (sequential queries)"
    echo ""
    
    PYTHONPATH=. pytest \
      rangerio_tests/integration/test_interactive_mode_accuracy.py \
      -v -s \
      --html=reports/html/phase2_interactive_accuracy.html \
      --self-contained-html \
      --tb=short \
      || echo "⚠️  Phase 2 had errors (check report)"
    
    echo ""
    echo "✅ Phase 2 Complete (or skipped due to errors)"
    cooldown 15
fi

# ============================================================================
# Phase 3A: Re-run Stage 3 (MEDIUM - Can Skip)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PHASE 3A: Re-run Stage 3 (Verification)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "This re-runs Stage 3 to verify fixes. You can skip if memory is low."
echo ""
read -p "Run Stage 3 rerun? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]] && check_memory_and_confirm "Phase 3A: Stage 3 Rerun"; then
    echo "Running: Mode combination matrix (8 tests)"
    echo "Expected time: 25-35 minutes"
    echo "Memory impact: MODERATE-HIGH"
    echo ""
    
    PYTHONPATH=. pytest \
      rangerio_tests/integration/test_mode_combinations.py \
      -v \
      --html=reports/html/phase3a_stage3_rerun.html \
      --self-contained-html \
      --tb=short \
      || echo "⚠️  Phase 3A had errors (check report)"
    
    echo ""
    echo "✅ Phase 3A Complete (or skipped due to errors)"
    cooldown 20
else
    echo "⏭️  Skipping Phase 3A"
fi

# ============================================================================
# Phase 3B: Stage 4 Benchmarks (HEAVY - Optional)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PHASE 3B: Stage 4 Performance Benchmarks"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  WARNING: This is the HEAVY phase (50+ queries per mode)"
echo "   It WILL use significant memory and take 15-20 minutes"
echo "   Skip this if you've experienced crashes"
echo ""
read -p "Run Stage 4 benchmarks? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]] && check_memory_and_confirm "Phase 3B: Stage 4 Benchmarks"; then
    echo "Running: 5 benchmark tests (HEAVY)"
    echo "Expected time: 15-20 minutes"
    echo "Memory impact: HIGH (many concurrent queries)"
    echo ""
    
    PYTHONPATH=. pytest \
      rangerio_tests/performance/test_mode_performance.py \
      -v \
      --html=reports/html/phase3b_stage4_benchmarks.html \
      --self-contained-html \
      --tb=short \
      || echo "⚠️  Phase 3B had errors (likely memory crash)"
    
    echo ""
    echo "✅ Phase 3B Complete (or crashed)"
else
    echo "⏭️  Skipping Phase 3B (recommended for low-memory systems)"
fi

# ============================================================================
# Final Report
# ============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SAFE MODE TESTING COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Generated Reports:"
ls -lh reports/html/*.html 2>/dev/null | tail -5 || echo "No HTML reports found"
echo ""
echo "📝 Next Steps:"
echo "   1. Review HTML reports in reports/html/"
echo "   2. If Phase 2 completed, rate answers in interactive report"
echo "   3. If Phase 3B was skipped, you can run it later when memory is available"
echo ""
echo "💡 To run skipped phases later:"
echo "   cd /Users/vadim/.cursor/worktrees/Validator/SYSTEM\ GO"
echo "   source venv/bin/activate"
echo "   PYTHONPATH=. pytest rangerio_tests/performance/test_mode_performance.py -v"
echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo ""






