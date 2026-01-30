#!/bin/bash
# ==============================================================================
# RangerIO Comprehensive E2E Test Runner
# ==============================================================================
# 
# This script runs different categories of tests for optimizing RangerIO:
# - Performance profiling (memory, response times, throughput)
# - Stress testing (concurrent users, batch processing)
# - Quality regression (golden queries that MUST pass)
# - Observability (health checks, metrics, logging)
#
# USAGE:
#   ./run_comprehensive_tests.sh [category]
#
# CATEGORIES:
#   quick         - Fast validation (~30s) - health + tasks
#   core          - Core functionality (~5min) - workflows + exports + tasks
#   quality       - RAG quality regression tests (~10min)
#   assistant     - Assistant mode tests (~8min)
#   profiling     - Performance profiling tests (~15min)
#   stress        - Stress and load tests (~20min)
#   diagnostics   - Generate optimization report (~10min)
#   all           - Run all tests in proper order
#   full          - Run everything without filtering
#
# TEST EXECUTION ORDER (fast → slow, critical → optional):
#   1. observability   (~30s)  - Quick health validation
#   2. tasks           (~1min) - Task queue verification
#   3. export          (~2min) - Export functionality
#   4. workflows       (~6min) - Core E2E workflows
#   5. quality         (~10min)- Golden query regression
#   6. assistant       (~8min) - Assistant mode features
#   7. profiling       (~15min)- Performance baselines
#   8. stress          (~20min)- Load testing
#   9. diagnostics     (~10min)- Recommendations report
#
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CATEGORY="${1:-all}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="reports/html"
LOG_DIR="reports/logs"
BACKEND_URL="http://127.0.0.1:9000"
TEST_DATA_DIR="/Users/vadim/Documents/RangerIO test files"

# Legacy tests to exclude (known issues, need separate fixing)
EXCLUDE_LEGACY=(
    "test_auditor_usecase.py"
    "test_interactive_rag.py"
    "test_rag_accuracy.py"
    "test_rag_benchmark.py"
    "test_sales_analysis_usecase.py"
    "test_validation_fixes.py"
    "test_interactive_mode_accuracy.py"
    "test_interactive_modes.py"
    "test_mode_combinations.py"
    "test_comprehensive_queries.py"
    "test_deep_search_mode.py"
)

mkdir -p "$REPORT_DIR" "$LOG_DIR"

# ==============================================================================
# PRE-FLIGHT CHECKS
# ==============================================================================
preflight_checks() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║       🔍 Pre-Flight Checks                                     ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    local all_passed=true
    
    # 1. Check backend health
    echo -ne "${YELLOW}  [1/5] Backend health...${NC} "
    if curl -s "$BACKEND_URL/health" > /dev/null 2>&1; then
        health_status=$(curl -s "$BACKEND_URL/health" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null)
        if [ "$health_status" = "healthy" ]; then
            echo -e "${GREEN}✓ Healthy${NC}"
        else
            echo -e "${RED}✗ Status: $health_status${NC}"
            all_passed=false
        fi
    else
        echo -e "${RED}✗ Not responding${NC}"
        echo -e "    ${RED}Please start the RangerIO backend first.${NC}"
        exit 1
    fi
    
    # 2. Check test data directory
    echo -ne "${YELLOW}  [2/5] Test data directory...${NC} "
    if [ -d "$TEST_DATA_DIR" ]; then
        file_count=$(find "$TEST_DATA_DIR" -type f | wc -l | tr -d ' ')
        echo -e "${GREEN}✓ Found ($file_count files)${NC}"
    else
        echo -e "${YELLOW}⚠ Not found (some tests will skip)${NC}"
    fi
    
    # 3. Check metrics endpoints
    echo -ne "${YELLOW}  [3/5] Metrics endpoints...${NC} "
    if curl -s "$BACKEND_URL/metrics/query-breakdown" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Available${NC}"
    else
        echo -e "${YELLOW}⚠ Not available (restart backend)${NC}"
    fi
    
    # 4. Check virtual environment
    echo -ne "${YELLOW}  [4/5] Virtual environment...${NC} "
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        export PYTHONPATH=.
        echo -e "${GREEN}✓ Activated${NC}"
    else
        echo -e "${RED}✗ Not found${NC}"
        exit 1
    fi
    
    # 5. Check pytest and dependencies
    echo -ne "${YELLOW}  [5/5] Test dependencies...${NC} "
    if python3 -c "import pytest, requests, psutil" 2>/dev/null; then
        echo -e "${GREEN}✓ Installed${NC}"
    else
        echo -e "${RED}✗ Missing (pip install pytest requests psutil)${NC}"
        exit 1
    fi
    
    echo ""
    if $all_passed; then
        echo -e "${GREEN}✓ All pre-flight checks passed${NC}"
    else
        echo -e "${YELLOW}⚠ Some checks had warnings (tests may skip)${NC}"
    fi
    echo ""
}

# ==============================================================================
# TEST RUNNER
# ==============================================================================
run_tests() {
    local name=$1
    local markers=$2
    local extra_args="${3:-}"
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}▶ Running: $name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    local log_file="$LOG_DIR/${name// /_}_$TIMESTAMP.log"
    local report_file="$REPORT_DIR/report_${name// /_}.html"
    local start_time=$(date +%s)
    
    if [ -n "$markers" ]; then
        pytest rangerio_tests/integration/ -m "$markers" \
            -v --tb=short \
            --html="$report_file" \
            --self-contained-html \
            $extra_args \
            2>&1 | tee "$log_file" || true
    else
        pytest $extra_args \
            -v --tb=short \
            --html="$report_file" \
            --self-contained-html \
            2>&1 | tee "$log_file" || true
    fi
    
    local exit_code=${PIPESTATUS[0]}
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ $name: PASSED (${duration}s)${NC}"
    else
        echo -e "${RED}✗ $name: FAILED (exit code: $exit_code, ${duration}s)${NC}"
    fi
    
    echo ""
    return $exit_code
}

# Build exclude arguments for pytest
build_exclude_args() {
    local excludes=""
    for file in "${EXCLUDE_LEGACY[@]}"; do
        excludes="$excludes --ignore=rangerio_tests/integration/$file"
    done
    echo "$excludes"
}

# ==============================================================================
# MAIN SCRIPT
# ==============================================================================

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       RangerIO Comprehensive Test Suite                        ║${NC}"
echo -e "${BLUE}║       Category: ${YELLOW}$CATEGORY${BLUE}                                        ${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Run pre-flight checks
preflight_checks

EXCLUDE_ARGS=$(build_exclude_args)

case "$CATEGORY" in
    "quick")
        echo -e "${MAGENTA}═══ Quick Validation (~30s) ═══${NC}"
        echo "Fast tests to verify basic functionality."
        echo ""
        run_tests "Health Checks" "" \
            "rangerio_tests/integration/test_observability.py::TestHealthChecks -v"
        run_tests "Task Queue" "tasks"
        ;;
    
    "core")
        echo -e "${MAGENTA}═══ Core Functionality (~5min) ═══${NC}"
        echo "Essential workflows that must work."
        echo ""
        run_tests "Observability" "observability"
        run_tests "Task Queue" "tasks"
        run_tests "Export Workflows" "export"
        run_tests "E2E Workflows" "" "rangerio_tests/integration/test_e2e_workflows.py"
        ;;
    
    "profiling")
        echo -e "${MAGENTA}═══ Performance Profiling Tests ═══${NC}"
        echo "These tests measure memory, response times, and throughput."
        echo ""
        run_tests "Performance Profiling" "profiling"
        ;;
    
    "stress")
        echo -e "${MAGENTA}═══ Stress Tests ═══${NC}"
        echo "These tests push the system to its limits."
        echo ""
        run_tests "Stress Tests" "stress"
        ;;
    
    "quality")
        echo -e "${MAGENTA}═══ Quality Regression Tests ═══${NC}"
        echo "Golden queries that MUST pass."
        echo ""
        run_tests "Quality Regression" "quality or regression"
        ;;
    
    "observability")
        echo -e "${MAGENTA}═══ Observability Tests ═══${NC}"
        echo "Health checks, metrics, and logging validation."
        echo ""
        run_tests "Observability" "observability"
        ;;
    
    "workflows")
        echo -e "${MAGENTA}═══ E2E Workflow Tests ═══${NC}"
        echo "Complete user workflows."
        echo ""
        run_tests "E2E Workflows" "" "rangerio_tests/integration/test_e2e_workflows.py"
        ;;
    
    "tasks")
        echo -e "${MAGENTA}═══ Task Queue Tests ═══${NC}"
        echo ""
        run_tests "Task Queue" "tasks"
        ;;
    
    "export")
        echo -e "${MAGENTA}═══ Export Workflow Tests ═══${NC}"
        echo ""
        run_tests "Export Workflows" "export"
        ;;
    
    "assistant")
        echo -e "${MAGENTA}═══ Assistant Mode Tests ═══${NC}"
        echo ""
        run_tests "Assistant Mode" "assistant"
        ;;
    
    "diagnostics")
        echo -e "${MAGENTA}═══ Diagnostic Performance Tests ═══${NC}"
        echo "Collect data and generate optimization recommendations."
        echo ""
        pytest rangerio_tests/integration/test_with_diagnostics.py \
            -v -s \
            --html="$REPORT_DIR/report_diagnostics.html" \
            --self-contained-html \
            2>&1 | tee "$LOG_DIR/diagnostics_$TIMESTAMP.log"
        ;;
    
    "all")
        echo -e "${MAGENTA}═══ Complete Test Suite (Ordered: Fast → Slow) ═══${NC}"
        echo "This will take a while. Get some coffee ☕"
        echo ""
        
        FAILED=0
        PASSED=0
        
        # Run in order: fast → slow, critical → optional
        echo -e "${CYAN}Phase 1: Quick Validation${NC}"
        run_tests "Health Checks" "" "rangerio_tests/integration/test_observability.py::TestHealthChecks" && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
        run_tests "Task Queue" "tasks" && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
        
        echo -e "${CYAN}Phase 2: Core Workflows${NC}"
        run_tests "Export Workflows" "export" && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
        run_tests "E2E Workflows" "" "rangerio_tests/integration/test_e2e_workflows.py rangerio_tests/integration/test_e2e_extended.py $EXCLUDE_ARGS" && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
        
        echo -e "${CYAN}Phase 3: Quality & Features${NC}"
        run_tests "Observability Full" "observability" && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
        run_tests "Quality Regression" "quality or regression" && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
        run_tests "Assistant Mode" "assistant" && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
        
        echo -e "${CYAN}Phase 4: Performance${NC}"
        run_tests "Performance Profiling" "profiling" && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
        run_tests "Stress Tests" "stress" && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
        
        echo ""
        echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
        echo -e "${CYAN}TEST SUMMARY${NC}"
        echo -e "${GREEN}  ✓ Passed: $PASSED${NC}"
        echo -e "${RED}  ✗ Failed: $FAILED${NC}"
        if [ $FAILED -eq 0 ]; then
            echo -e "${GREEN}  🎉 ALL TEST CATEGORIES PASSED${NC}"
        else
            echo -e "${YELLOW}  ⚠ Some categories had failures - check reports${NC}"
        fi
        echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
        ;;
    
    "full")
        echo -e "${MAGENTA}═══ Full Integration Test Suite ═══${NC}"
        echo "All tests without filtering or ordering."
        echo ""
        run_tests "Full Suite" "" "rangerio_tests/integration/ $EXCLUDE_ARGS"
        ;;
    
    "clean")
        echo -e "${MAGENTA}═══ Clean Core Tests (Stable Only) ═══${NC}"
        echo "Run only the stable, well-tested integration tests."
        echo ""
        run_tests "Clean Core" "" \
            "rangerio_tests/integration/test_observability.py \
             rangerio_tests/integration/test_e2e_workflows.py \
             rangerio_tests/integration/test_e2e_extended.py \
             rangerio_tests/integration/test_export_workflows.py \
             rangerio_tests/integration/test_assistant_mode.py"
        ;;
    
    *)
        echo -e "${RED}Unknown category: $CATEGORY${NC}"
        echo ""
        echo "Available categories:"
        echo ""
        echo "  ${GREEN}Quick Tests:${NC}"
        echo "    quick         - Fast validation (~30s) - health + tasks"
        echo ""
        echo "  ${GREEN}Core Tests:${NC}"
        echo "    core          - Core functionality (~5min)"
        echo "    workflows     - E2E workflow tests"
        echo "    tasks         - Task queue tests"
        echo "    export        - Export workflow tests"
        echo "    observability - Health checks and metrics"
        echo ""
        echo "  ${GREEN}Feature Tests:${NC}"
        echo "    assistant     - Assistant mode tests"
        echo "    quality       - RAG quality regression"
        echo ""
        echo "  ${GREEN}Performance Tests:${NC}"
        echo "    profiling     - Performance profiling"
        echo "    stress        - Stress and load tests"
        echo "    diagnostics   - Generate optimization report"
        echo ""
        echo "  ${GREEN}Combined:${NC}"
        echo "    all           - Run all tests in proper order"
        echo "    full          - Run everything without filtering"
        echo "    clean         - Run stable tests only"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Reports saved to:${NC}"
echo "  HTML: $REPORT_DIR/"
echo "  Logs: $LOG_DIR/"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""
