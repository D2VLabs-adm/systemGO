#!/bin/bash
# =============================================================================
# RangerIO E2E Test Runner
# =============================================================================
# 
# Runs comprehensive E2E tests against RangerIO backend
#
# Usage:
#   ./run_e2e_tests.sh              # Run all E2E tests
#   ./run_e2e_tests.sh import       # Run import tests only
#   ./run_e2e_tests.sh quality      # Run quality detection tests only
#   ./run_e2e_tests.sh query        # Run RAG query tests only
#   ./run_e2e_tests.sh performance  # Run performance tests only
#   ./run_e2e_tests.sh --debug      # Run with verbose debugging
#
# Prerequisites:
#   - RangerIO backend running at http://127.0.0.1:9000
#   - Test files at /Users/vadim/Documents/RangerIO test files/
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
REPORTS_DIR="$SCRIPT_DIR/reports"
LOG_FILE="$SCRIPT_DIR/logs/e2e_test_$(date +%Y%m%d_%H%M%S).log"

# Create directories
mkdir -p "$REPORTS_DIR/html"
mkdir -p "$SCRIPT_DIR/logs"

# Banner
echo -e "${BLUE}"
echo "============================================================"
echo "  RangerIO E2E Test Suite"
echo "  $(date)"
echo "============================================================"
echo -e "${NC}"

# Check backend health
echo -e "${YELLOW}Checking backend health...${NC}"
HEALTH=$(curl -s http://127.0.0.1:9000/health 2>/dev/null || echo "FAILED")
if [[ "$HEALTH" == *"healthy"* ]]; then
    echo -e "${GREEN}✅ Backend is healthy${NC}"
else
    echo -e "${RED}❌ Backend not responding at http://127.0.0.1:9000${NC}"
    echo "   Please start the backend first"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"
export PYTHONPATH="$SCRIPT_DIR"

# Determine test target
TEST_TARGET=""
PYTEST_ARGS="-v --tb=short"

case "${1:-all}" in
    import)
        TEST_TARGET="rangerio_tests/integration/test_e2e_workflows.py::TestImportWorkflows"
        echo -e "${BLUE}Running: Import Workflow Tests${NC}"
        ;;
    quality)
        TEST_TARGET="rangerio_tests/integration/test_e2e_workflows.py::TestQualityDetection"
        echo -e "${BLUE}Running: Quality Detection Tests${NC}"
        ;;
    query)
        TEST_TARGET="rangerio_tests/integration/test_e2e_workflows.py::TestRAGQueries"
        echo -e "${BLUE}Running: RAG Query Tests${NC}"
        ;;
    performance)
        TEST_TARGET="rangerio_tests/integration/test_e2e_workflows.py::TestPerformance"
        echo -e "${BLUE}Running: Performance Tests${NC}"
        ;;
    accuracy)
        TEST_TARGET="rangerio_tests/integration/test_e2e_extended.py::TestQueryAccuracy"
        echo -e "${BLUE}Running: Query Accuracy Tests${NC}"
        ;;
    filetypes)
        TEST_TARGET="rangerio_tests/integration/test_e2e_extended.py::TestFileTypes"
        echo -e "${BLUE}Running: File Type Tests (PDF, DOCX)${NC}"
        ;;
    benchmark)
        TEST_TARGET="rangerio_tests/integration/test_e2e_extended.py::TestPerformanceBenchmarks"
        echo -e "${BLUE}Running: Performance Benchmark Tests${NC}"
        ;;
    sales)
        TEST_TARGET="rangerio_tests/integration/test_e2e_extended.py::TestSalesDataQueries"
        echo -e "${BLUE}Running: Sales Data Query Tests${NC}"
        ;;
    tasks)
        TEST_TARGET="rangerio_tests/integration/test_e2e_extended.py::TestTaskQueue"
        echo -e "${BLUE}Running: Task Queue Validation Tests${NC}"
        ;;
    assistant)
        TEST_TARGET="rangerio_tests/integration/test_assistant_mode.py"
        echo -e "${BLUE}Running: Assistant Mode Tests${NC}"
        ;;
    export)
        TEST_TARGET="rangerio_tests/integration/test_export_workflows.py"
        echo -e "${BLUE}Running: Export Workflow Tests${NC}"
        ;;
    workflow)
        TEST_TARGET="rangerio_tests/integration/test_e2e_workflows.py::TestCompleteWorkflows"
        echo -e "${BLUE}Running: Complete Workflow Tests${NC}"
        ;;
    extended)
        TEST_TARGET="rangerio_tests/integration/test_e2e_extended.py"
        echo -e "${BLUE}Running: All Extended E2E Tests${NC}"
        ;;
    all|"")
        TEST_TARGET="rangerio_tests/integration/test_e2e_workflows.py"
        echo -e "${BLUE}Running: All E2E Tests${NC}"
        ;;
    full)
        TEST_TARGET="rangerio_tests/integration/"
        echo -e "${BLUE}Running: Full E2E Test Suite (All Test Files)${NC}"
        ;;
    --debug)
        TEST_TARGET="rangerio_tests/integration/"
        PYTEST_ARGS="-v --tb=long -s --log-cli-level=DEBUG"
        echo -e "${BLUE}Running: All E2E Tests (Debug Mode)${NC}"
        ;;
    *)
        echo -e "${RED}Unknown test target: $1${NC}"
        echo "Usage: $0 [import|quality|query|performance|accuracy|filetypes|benchmark|sales|tasks|assistant|export|workflow|extended|all|full|--debug]"
        exit 1
        ;;
esac

# Run tests
echo -e "${YELLOW}Starting tests...${NC}"
echo "Log file: $LOG_FILE"
echo ""

# Run pytest with HTML report
pytest $TEST_TARGET $PYTEST_ARGS \
    --html="$REPORTS_DIR/html/e2e_report.html" \
    --self-contained-html \
    2>&1 | tee "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo -e "${BLUE}============================================================${NC}"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed (exit code: $EXIT_CODE)${NC}"
fi
echo -e "${BLUE}============================================================${NC}"
echo ""
echo "📊 HTML Report: $REPORTS_DIR/html/e2e_report.html"
echo "📝 Log File: $LOG_FILE"
echo ""

exit $EXIT_CODE
