#!/bin/bash
#
# Master Automation Script - All 3 Phases
# Fixes backend, runs interactive tests, completes benchmarks, generates report
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║          SYSTEM GO - 3-Phase Automation                                ║"
echo "║          Mode Testing Enhancement & Completion                          ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Phase 1: ✅ Backend API fixes applied (clarification, validation, metadata)"
echo "Phase 2: 🧪 Interactive accuracy testing"
echo "Phase 3: 📊 Stage 4 performance benchmarks"
echo ""
echo "Estimated time: 60-90 minutes total"
echo ""

# ============================================================================
# Phase 1: Backend Already Fixed (completed before this script)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PHASE 1: Backend API Enhancements"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Added 'clarification' field (Assistant mode)"
echo "✅ Added 'validation' field (Deep Search mode)"
echo "✅ Added 'metadata' field (all modes)"
echo "✅ Backend restarted with changes"
echo ""
echo "🔍 Verifying backend..."
if curl -s http://127.0.0.1:9000/health > /dev/null 2>&1; then
    echo "✅ Backend responding on port 9000"
else
    echo "❌ Backend not responding! Please start it first."
    exit 1
fi
echo ""
sleep 3

# ============================================================================
# Phase 2: Interactive Accuracy Testing
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PHASE 2: Interactive Mode Accuracy Testing"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Running: Side-by-side mode comparison tests"
echo "Expected time: 15-25 minutes"
echo ""

PYTHONPATH=. pytest \
  rangerio_tests/integration/test_interactive_mode_accuracy.py \
  -v -s \
  --html=reports/html/phase2_interactive_accuracy.html \
  --self-contained-html \
  --tb=short

echo ""
echo "✅ Phase 2 Complete!"
echo "📊 Interactive HTML report generated for human review"
echo ""
sleep 3

# ============================================================================
# Phase 3: Re-run Stage 3 to Verify Fixes
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PHASE 3A: Re-run Stage 3 (Verify Fixes)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Running: Mode combination matrix tests (should show ✓ for all features)"
echo "Expected time: 25-35 minutes"
echo ""

PYTHONPATH=. pytest \
  rangerio_tests/integration/test_mode_combinations.py \
  -v \
  --html=reports/html/phase3a_stage3_rerun.html \
  --self-contained-html \
  --tb=short

echo ""
echo "✅ Phase 3A Complete!"
echo "🔍 Check report to verify all features now show ✓"
echo ""
sleep 3

# ============================================================================
# Phase 4: Stage 4 Performance Benchmarks
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PHASE 3B: Stage 4 Performance Benchmarks"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Running: Response time distribution, overhead, throughput, model comparison"
echo "Expected time: 15-20 minutes (HEAVY - this is the benchmarking stage)"
echo "⚠️  This runs 50+ queries per mode for statistical analysis"
echo ""

PYTHONPATH=. pytest \
  rangerio_tests/performance/test_mode_performance.py \
  -v \
  --html=reports/html/phase3b_stage4_benchmarks.html \
  --self-contained-html \
  --tb=short

echo ""
echo "✅ Phase 3B Complete!"
echo "💾 Benchmark results saved to database"
echo ""
sleep 3

# ============================================================================
# Final Report Generation
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "FINAL: Generating Comprehensive Report"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Generate benchmark comparison report
python compare_benchmarks.py report --output reports/benchmarks/final_comparison.md

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║                    🎉 ALL PHASES COMPLETE! 🎉                          ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Generated Reports:"
echo "   1. Phase 2 (Interactive): reports/html/phase2_interactive_accuracy.html"
echo "   2. Phase 3A (Stage 3 Rerun): reports/html/phase3a_stage3_rerun.html"
echo "   3. Phase 3B (Stage 4 Benchmarks): reports/html/phase3b_stage4_benchmarks.html"
echo "   4. Benchmark Comparison: reports/benchmarks/final_comparison.md"
echo ""
echo "📝 Next Steps:"
echo "   1. Open phase2_interactive_accuracy.html in your browser"
echo "   2. Rate the accuracy of each mode's answers (1-5 stars)"
echo "   3. Add notes for comparison"
echo "   4. Export results when done"
echo "   5. Review Stage 3 rerun to verify all features now work (should show ✓)"
echo ""
echo "✅ Testing Status:"
echo "   Stages 1-4: Complete"
echo "   Interactive Validation: Generated (awaiting human review)"
echo "   Benchmark Database: First baseline saved!"
echo ""
echo "🎯 You can now:"
echo "   - Compare models: python compare_benchmarks.py compare --models model1 model2"
echo "   - View trends: python compare_benchmarks.py trend --model qwen3-4b"
echo "   - Generate reports: python compare_benchmarks.py report"
echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo ""






