#!/bin/bash
# Run realistic use case tests with interactive validation

set -e  # Exit on error

echo "═══════════════════════════════════════════════════════════════"
echo "  RangerIO Realistic Use Case Testing"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Set PYTHONPATH
export PYTHONPATH="/Users/vadim/.cursor/worktrees/Validator/SYSTEM GO:$PYTHONPATH"

# Change to test directory
cd "/Users/vadim/.cursor/worktrees/Validator/SYSTEM GO"

# Check backend is running
echo "🔍 Checking backend availability..."
if ! curl -s -f "http://127.0.0.1:9000/health" > /dev/null 2>&1; then
    echo "❌ Backend not responding at http://127.0.0.1:9000"
    echo "   Please start the backend first"
    exit 1
fi
echo "✅ Backend is running"
echo ""

# Install dependencies if needed
echo "📦 Checking dependencies..."
if ! python3 -c "import kaggle" 2>/dev/null; then
    echo "   Installing kaggle package..."
    pip install --quiet kaggle
fi
echo "✅ Dependencies ready"
echo ""

# Generate test data
echo "📊 Generating test datasets..."
python3 -c "
from pathlib import Path
from rangerio_tests.utils.kaggle_dataset_downloader import download_sales_dataset, create_auditor_scenario
from rangerio_tests.config import config

print('  - Generating sales dataset...')
sales_file = download_sales_dataset(config.TEST_DATA_DIR / 'sales_usecase')
print(f'    ✓ Sales data: {sales_file}')

print('  - Generating auditor scenario files...')
auditor_files = create_auditor_scenario(config.TEST_DATA_DIR)
print(f'    ✓ Auditor files: {len(auditor_files)} files created')
"
echo "✅ Test datasets ready"
echo ""

# Run sales use case tests
echo "═══════════════════════════════════════════════════════════════"
echo "  Phase 1: Sales Data Analysis Use Case"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Testing with realistic 5-year sales data..."
echo "Complex queries: Regional profit margins, team performance, reseller analysis"
echo ""

pytest -v -m "integration and interactive" \
    rangerio_tests/integration/test_sales_analysis_usecase.py \
    --html=reports/html/sales_usecase_report.html \
    --self-contained-html \
    -s

echo ""
echo "✅ Phase 1 Complete"
echo ""
sleep 3

# Run auditor use case tests
echo "═══════════════════════════════════════════════════════════════"
echo "  Phase 2: Auditor Multi-Document Use Case"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Testing with mixed file types (Excel, PDF, DOCX, TXT)..."
echo "Complex queries: Cross-document discrepancies, governance validation, reconciliation"
echo ""

pytest -v -m "integration and interactive" \
    rangerio_tests/integration/test_auditor_usecase.py \
    --html=reports/html/auditor_usecase_report.html \
    --self-contained-html \
    -s

echo ""
echo "✅ Phase 2 Complete"
echo ""

# Generate final summary
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ ALL TESTS COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📊 Interactive HTML Reports:"
echo ""
echo "1. Sales Use Case:"
echo "   reports/html/sales_usecase_report.html"
echo ""
echo "2. Auditor Use Case:"
echo "   reports/html/auditor_usecase_report.html"
echo ""
echo "3. Interactive Validation Report:"
VALIDATION_REPORT=$(find fixtures/golden_outputs -name "interactive_validation_*.html" -type f -print | head -n 1)
if [ -n "$VALIDATION_REPORT" ]; then
    echo "   $VALIDATION_REPORT"
    echo ""
    echo "🔗 CLICK TO OPEN:"
    echo "   file://$VALIDATION_REPORT"
else
    echo "   (Report not generated - check test output)"
fi
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "📝 NEXT STEPS:"
echo ""
echo "1. Open the Interactive Validation Report in your browser"
echo "2. Review each query and provide feedback"
echo "3. Check the 'refinement needed' boxes for issues found"
echo "4. Add detailed notes explaining what needs improvement"
echo "5. Export results when complete"
echo ""
echo "The validation results will help identify specific areas where"
echo "RangerIO needs refinement for complex, real-world use cases."
echo "═══════════════════════════════════════════════════════════════"






