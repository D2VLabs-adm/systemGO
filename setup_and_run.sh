#!/bin/bash
#
# System GO - Quick Setup and Run Script
# =======================================
#
# This script sets up System GO for testing RangerIO.
#
# Prerequisites:
#   - Python 3.10+ installed
#   - RangerIO backend running on localhost:9000
#   - RangerIO frontend running on localhost:5173 (optional, for UI tests)
#
# Usage:
#   ./setup_and_run.sh          # Full setup + run basic tests
#   ./setup_and_run.sh --quick  # Skip setup, run quick tests only
#   ./setup_and_run.sh --ui     # Include UI tests (requires frontend)
#   ./setup_and_run.sh --all    # Run all tests including slow ones
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║           SYSTEM GO - RangerIO Testing Suite                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Parse arguments
SKIP_SETUP=false
RUN_UI=false
RUN_ALL=false
RUN_QUALITY=false

for arg in "$@"; do
    case $arg in
        --quick)
            SKIP_SETUP=true
            ;;
        --ui)
            RUN_UI=true
            ;;
        --all)
            RUN_ALL=true
            ;;
        --quality)
            RUN_QUALITY=true
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --quick     Skip setup, run quick tests only"
            echo "  --ui        Include UI tests (requires frontend running)"
            echo "  --quality   Run quality scenario tests (LLM-as-judge)"
            echo "  --all       Run all tests including slow ones"
            echo "  --help      Show this help message"
            echo ""
            echo "Prerequisites:"
            echo "  - RangerIO backend on http://127.0.0.1:9000"
            echo "  - RangerIO frontend on http://localhost:5173 (for --ui)"
            exit 0
            ;;
    esac
done

# =============================================================================
# STEP 1: Check Prerequisites
# =============================================================================
echo -e "${YELLOW}[1/5] Checking prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.10+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "  ✓ Python $PYTHON_VERSION found"

# Check RangerIO backend
echo -n "  Checking RangerIO backend... "
if curl -s --max-time 5 http://127.0.0.1:9000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    echo -e "${YELLOW}  Please start RangerIO backend on port 9000${NC}"
    echo "  Example: cd /path/to/rangerio && python -m uvicorn api.server:app --port 9000"
    exit 1
fi

# Check frontend if UI tests requested
if [ "$RUN_UI" = true ]; then
    echo -n "  Checking RangerIO frontend... "
    if curl -s --max-time 5 http://localhost:5173 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${YELLOW}⚠ Not running (UI tests will be skipped)${NC}"
        RUN_UI=false
    fi
fi

# =============================================================================
# STEP 2: Setup Virtual Environment
# =============================================================================
if [ "$SKIP_SETUP" = false ]; then
    echo -e "\n${YELLOW}[2/5] Setting up virtual environment...${NC}"
    
    if [ ! -d "venv" ]; then
        echo "  Creating virtual environment..."
        python3 -m venv venv
    fi
    
    echo "  Activating virtual environment..."
    source venv/bin/activate
    
    echo "  Installing dependencies..."
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    
    echo -e "  ${GREEN}✓ Dependencies installed${NC}"
    
    # Install Playwright for UI tests
    if [ "$RUN_UI" = true ]; then
        echo "  Installing Playwright browser..."
        playwright install chromium --with-deps 2>/dev/null || true
    fi
else
    echo -e "\n${YELLOW}[2/5] Skipping setup (--quick mode)${NC}"
    source venv/bin/activate 2>/dev/null || {
        echo -e "${RED}❌ Virtual environment not found. Run without --quick first.${NC}"
        exit 1
    }
fi

# =============================================================================
# STEP 3: Create Reports Directory
# =============================================================================
echo -e "\n${YELLOW}[3/5] Preparing reports directory...${NC}"
mkdir -p reports/html reports/screenshots reports/videos
echo "  ✓ Reports directory ready"

# =============================================================================
# STEP 4: Run Tests
# =============================================================================
echo -e "\n${YELLOW}[4/5] Running tests...${NC}"
echo ""

# Build pytest command
PYTEST_CMD="PYTHONPATH=. pytest"
PYTEST_ARGS="-v --tb=short"

if [ "$RUN_ALL" = true ]; then
    # Run everything
    echo -e "${BLUE}Running ALL tests (this may take a while)...${NC}"
    PYTEST_CMD="$PYTEST_CMD rangerio_tests/"
    PYTEST_ARGS="$PYTEST_ARGS --html=reports/html/full_report.html"
elif [ "$RUN_QUALITY" = true ]; then
    # Run quality scenarios
    echo -e "${BLUE}Running quality scenario tests...${NC}"
    PYTEST_CMD="$PYTEST_CMD rangerio_tests/integration/test_user_quality_scenarios.py"
    PYTEST_ARGS="$PYTEST_ARGS -s --html=reports/html/quality_report.html"
elif [ "$RUN_UI" = true ]; then
    # Run UI tests
    echo -e "${BLUE}Running UI workflow tests...${NC}"
    PYTEST_CMD="$PYTEST_CMD rangerio_tests/frontend/"
    PYTEST_ARGS="$PYTEST_ARGS --html=reports/html/ui_report.html"
else
    # Run quick backend tests (default)
    echo -e "${BLUE}Running quick backend tests...${NC}"
    PYTEST_CMD="$PYTEST_CMD rangerio_tests/backend/ -m 'not slow'"
    PYTEST_ARGS="$PYTEST_ARGS --html=reports/html/quick_report.html"
fi

# Execute tests
echo ""
eval "$PYTEST_CMD $PYTEST_ARGS" || TEST_EXIT_CODE=$?

# =============================================================================
# STEP 5: Summary
# =============================================================================
echo ""
echo -e "${YELLOW}[5/5] Test Summary${NC}"
echo "════════════════════════════════════════════════════════════════"

if [ -z "$TEST_EXIT_CODE" ] || [ "$TEST_EXIT_CODE" -eq 0 ]; then
    echo -e "${GREEN}✅ Tests completed successfully!${NC}"
else
    echo -e "${RED}❌ Some tests failed (exit code: $TEST_EXIT_CODE)${NC}"
fi

echo ""
echo "Reports saved to:"
echo "  📊 HTML Report: reports/html/"
echo "  📸 Screenshots: reports/screenshots/"
if [ "$RUN_UI" = true ]; then
    echo "  🎥 Videos:      reports/videos/"
fi

echo ""
echo "Next steps:"
echo "  • View HTML report: open reports/html/*.html"
echo "  • Run quality tests: ./setup_and_run.sh --quality"
echo "  • Run UI tests:      ./setup_and_run.sh --ui"
echo "  • Run all tests:     ./setup_and_run.sh --all"

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

exit ${TEST_EXIT_CODE:-0}
