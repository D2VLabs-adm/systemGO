#!/bin/bash
# Stage 3: Mode Combinations with REAL-TIME progress tracking

set -e
cd "/Users/vadim/.cursor/worktrees/Validator/SYSTEM GO"
source venv/bin/activate

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 STAGE 3/4: Mode Combination Matrix Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Tests: 8 tests (6 query types × 4 modes + 2 comparison tests)"
echo "Expected time: 8-12 minutes"
echo "🔄 Progress will be shown in real-time below..."
echo ""
sleep 3

# Run pytest with -s flag to show print statements in real-time
# Use unbuffered output for immediate display
PYTHONPATH=. PYTHONUNBUFFERED=1 pytest \
  rangerio_tests/integration/test_mode_combinations.py \
  -v -s \
  --html=reports/html/3_mode_combinations.html \
  --self-contained-html \
  --tb=short \
  2>&1 | while IFS= read -r line; do
    echo "$line"
    # Show progress markers
    if [[ "$line" == *"PASSED"* ]]; then
      echo "  ✅ Test passed!"
    elif [[ "$line" == *"FAILED"* ]]; then
      echo "  ❌ Test failed!"
    elif [[ "$line" == *"test_"* ]]; then
      echo "  ⏳ Running..."
    fi
  done

echo ""
echo "✅ Stage 3 Complete!"
echo "📊 Report: file://$(pwd)/reports/html/3_mode_combinations.html"
echo ""






