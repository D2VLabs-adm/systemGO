#!/bin/bash
#
# RangerIO User Scenario Test Runner
# ==================================
#
# Runs realistic user scenario tests in batches (~10 min each)
#
# Usage:
#   ./run_user_scenarios.sh batch1     # Run Batch 1: Financial Sample
#   ./run_user_scenarios.sh batch2     # Run Batch 2: Sales 5-Year
#   ./run_user_scenarios.sh batch3     # Run Batch 3: Quarterly Trends
#   ./run_user_scenarios.sh batch4     # Run Batch 4: Mixed Quality
#   ./run_user_scenarios.sh all        # Run all batches continuously
#   ./run_user_scenarios.sh interactive # Run batches with pauses between
#
# Model Options:
#   ./run_user_scenarios.sh batch1 --model=micro   # Use Granite Micro
#   ./run_user_scenarios.sh batch1 --model=tiny    # Use Granite Tiny (default)
#
# Mode Options:
#   ./run_user_scenarios.sh batch1 --assistant     # Enable Assistant mode
#   ./run_user_scenarios.sh batch1 --no-streaming  # Use non-streaming endpoint
#
# UI Mode:
#   ./run_user_scenarios.sh ui        # Launch System GO web UI
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORTS_DIR="${SCRIPT_DIR}/reports/user_scenarios"
BACKEND_URL="http://127.0.0.1:9000"

# Default options (can be overridden by command line)
export SYSTEM_GO_MODEL="${SYSTEM_GO_MODEL:-tiny}"
export SYSTEM_GO_ASSISTANT="${SYSTEM_GO_ASSISTANT:-false}"
export SYSTEM_GO_STREAMING="${SYSTEM_GO_STREAMING:-true}"

# Parse command line options
parse_options() {
    for arg in "$@"; do
        case $arg in
            --model=*)
                export SYSTEM_GO_MODEL="${arg#*=}"
                ;;
            --assistant)
                export SYSTEM_GO_ASSISTANT="true"
                ;;
            --no-streaming)
                export SYSTEM_GO_STREAMING="false"
                ;;
        esac
    done
}

# Create reports directory
mkdir -p "${REPORTS_DIR}"

# Timestamp for this run
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${REPORTS_DIR}/run_${TIMESTAMP}.log"

log() {
    echo -e "$1" | tee -a "${LOG_FILE}"
}

header() {
    log ""
    log "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    log "${BLUE}║${NC}  $1"
    log "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    log ""
}

show_config() {
    log "${YELLOW}Configuration:${NC}"
    log "  Model:     ${SYSTEM_GO_MODEL}"
    log "  Assistant: ${SYSTEM_GO_ASSISTANT}"
    log "  Streaming: ${SYSTEM_GO_STREAMING}"
    log ""
}

check_backend() {
    log "Checking RangerIO backend..."
    if curl -s --connect-timeout 5 "${BACKEND_URL}/health" > /dev/null 2>&1; then
        log "${GREEN}✓ Backend is healthy${NC}"
        return 0
    else
        log "${RED}✗ Backend is not responding at ${BACKEND_URL}${NC}"
        log "  Please start the backend first: cd /path/to/udp && ./run.sh"
        exit 1
    fi
}

run_batch() {
    local batch_name=$1
    local marker=$2
    local description=$3
    
    header "$description"
    
    log "Starting: $(date)"
    log "Marker: ${marker}"
    log ""
    
    # Activate virtual environment if exists
    if [ -f "${SCRIPT_DIR}/venv/bin/activate" ]; then
        source "${SCRIPT_DIR}/venv/bin/activate"
    fi
    
    # Run pytest with the batch marker
    cd "${SCRIPT_DIR}"
    
    PYTHONPATH=. pytest \
        rangerio_tests/integration/test_realistic_user_scenarios.py \
        -m "${marker}" \
        -v \
        --tb=short \
        --html="${REPORTS_DIR}/${batch_name}_${TIMESTAMP}.html" \
        --self-contained-html \
        --timeout=600 \
        2>&1 | tee -a "${LOG_FILE}"
    
    local exit_code=${PIPESTATUS[0]}
    
    log ""
    if [ $exit_code -eq 0 ]; then
        log "${GREEN}✓ ${batch_name} completed successfully${NC}"
    else
        log "${RED}✗ ${batch_name} had failures (exit code: ${exit_code})${NC}"
    fi
    
    log "Completed: $(date)"
    log ""
    
    return $exit_code
}

pause_between_batches() {
    log ""
    log "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    log "${YELLOW}Batch complete. Press ENTER to continue to next batch, or Ctrl+C to stop${NC}"
    log "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    read -r
}

print_summary() {
    log ""
    log "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    log "${BLUE}║${NC}  ${GREEN}TEST RUN COMPLETE${NC}"
    log "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    log ""
    log "Reports saved to: ${REPORTS_DIR}"
    log "Log file: ${LOG_FILE}"
    log ""
    log "JSON Reports:"
    ls -la "${REPORTS_DIR}"/*.json 2>/dev/null | tail -5 || true
    log ""
    log "HTML Reports:"
    ls -la "${REPORTS_DIR}"/*.html 2>/dev/null | tail -5 || true
    log ""
}

# Main
parse_options "$@"

case "${1:-help}" in
    ui)
        header "Starting System GO Web UI"
        log "Starting server at http://127.0.0.1:9001"
        log "Press Ctrl+C to stop"
        log ""
        cd "${SCRIPT_DIR}"
        if [ -f "venv/bin/activate" ]; then
            source "venv/bin/activate"
        fi
        python3 system_go_server.py
        ;;
    
    batch1)
        check_backend
        show_config
        run_batch "batch1" "batch1" "BATCH 1: Financial Sample (~10 min)"
        print_summary
        ;;
    
    batch2)
        check_backend
        run_batch "batch2" "batch2" "BATCH 2: Sales 5-Year Comprehensive (~10 min)"
        print_summary
        ;;
    
    batch3)
        check_backend
        run_batch "batch3" "batch3" "BATCH 3: Quarterly Trends (~10 min)"
        print_summary
        ;;
    
    batch4)
        check_backend
        run_batch "batch4" "batch4" "BATCH 4: Mixed Quality Data (~10 min)"
        print_summary
        ;;
    
    all)
        header "RUNNING ALL BATCHES CONTINUOUSLY"
        check_backend
        
        FAILED=0
        
        run_batch "batch1" "batch1" "BATCH 1: Financial Sample" || FAILED=$((FAILED + 1))
        run_batch "batch2" "batch2" "BATCH 2: Sales 5-Year" || FAILED=$((FAILED + 1))
        run_batch "batch3" "batch3" "BATCH 3: Quarterly Trends" || FAILED=$((FAILED + 1))
        run_batch "batch4" "batch4" "BATCH 4: Mixed Quality" || FAILED=$((FAILED + 1))
        
        print_summary
        
        if [ $FAILED -gt 0 ]; then
            log "${RED}${FAILED} batch(es) had failures${NC}"
            exit 1
        fi
        ;;
    
    interactive)
        header "INTERACTIVE MODE: Batches with pauses"
        check_backend
        
        FAILED=0
        
        run_batch "batch1" "batch1" "BATCH 1: Financial Sample" || FAILED=$((FAILED + 1))
        pause_between_batches
        
        run_batch "batch2" "batch2" "BATCH 2: Sales 5-Year" || FAILED=$((FAILED + 1))
        pause_between_batches
        
        run_batch "batch3" "batch3" "BATCH 3: Quarterly Trends" || FAILED=$((FAILED + 1))
        pause_between_batches
        
        run_batch "batch4" "batch4" "BATCH 4: Mixed Quality" || FAILED=$((FAILED + 1))
        
        print_summary
        
        if [ $FAILED -gt 0 ]; then
            log "${RED}${FAILED} batch(es) had failures${NC}"
            exit 1
        fi
        ;;
    
    summary)
        # Generate summary from existing reports
        cd "${SCRIPT_DIR}"
        if [ -f "venv/bin/activate" ]; then
            source "venv/bin/activate"
        fi
        
        python3 -c "
import json
from pathlib import Path
import glob

reports_dir = Path('${REPORTS_DIR}')
json_files = sorted(reports_dir.glob('batch*.json'), key=lambda x: x.stat().st_mtime, reverse=True)

if not json_files:
    print('No batch reports found')
    exit(0)

print('\\n' + '='*60)
print('LATEST BATCH RESULTS')
print('='*60)

for f in json_files[:4]:  # Show last 4 batches
    with open(f) as fp:
        data = json.load(fp)
    
    summary = data.get('summary', {})
    quality = data.get('quality', {})
    
    print(f\"\\n{data['batch_name']}:\")
    print(f\"  Pass Rate: {summary.get('pass_rate', 'N/A')}\")
    print(f\"  Accuracy:  {quality.get('avg_accuracy_score', 'N/A')}/10\")
    print(f\"  Queries:   {summary.get('passed', 0)}/{summary.get('total_queries', 0)} passed\")

print('\\n' + '='*60)
"
        ;;
    
    help|*)
        echo ""
        echo "RangerIO User Scenario Test Runner"
        echo "==================================="
        echo ""
        echo "Usage: $0 <command> [options]"
        echo ""
        echo "Commands:"
        echo "  ui           Launch System GO web UI (recommended)"
        echo "  batch1       Run Batch 1: Financial Sample queries (~10 min)"
        echo "  batch2       Run Batch 2: Sales 5-Year comprehensive (~10 min)"
        echo "  batch3       Run Batch 3: Quarterly Trends time series (~10 min)"
        echo "  batch4       Run Batch 4: Mixed Quality data (~10 min)"
        echo "  all          Run all batches continuously (~40 min)"
        echo "  interactive  Run batches with pauses between each"
        echo "  summary      Show summary of latest batch results"
        echo "  help         Show this help message"
        echo ""
        echo "Options:"
        echo "  --model=micro     Use Granite Micro model (faster)"
        echo "  --model=tiny      Use Granite Tiny model (default, better quality)"
        echo "  --assistant       Enable Assistant mode"
        echo "  --no-streaming    Use non-streaming endpoint"
        echo ""
        echo "Examples:"
        echo "  $0 ui                              # Launch web UI"
        echo "  $0 batch1 --model=micro            # Fast tests with Micro"
        echo "  $0 all --assistant                 # All batches with Assistant mode"
        echo "  $0 batch1 --model=tiny --assistant # Tiny + Assistant mode"
        echo ""
        echo "Reports are saved to: ${REPORTS_DIR}"
        echo ""
        ;;
esac
