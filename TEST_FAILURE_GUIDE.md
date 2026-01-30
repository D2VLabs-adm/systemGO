# Test Failure Investigation & Repair Guide

## 🔍 Overview

When tests fail, SYSTEM GO provides a **complete investigation and repair workflow**:

1. ✅ **Detect** - Tests identify failures automatically
2. 🔍 **Investigate** - Detailed logs, screenshots, and metrics
3. 🛠️ **Repair** - Fix the root cause
4. ✅ **Verify** - Re-run to confirm fix
5. 📊 **Document** - Update golden dataset

This is an **iterative process** - not just pass/fail validation.

---

## 🚨 When Tests Fail

### Automatic Failure Detection

Tests fail in several ways:

#### 1. **Assertion Failures**
```
AssertionError: Expected 100 rows, got 95
AssertionError: RAG faithfulness 0.62 < required 0.70
AssertionError: Memory usage 2.5GB > max 2GB
```

#### 2. **Timeout Failures**
```
TimeoutError: Backend did not respond within 30s
TimeoutError: Import took 75s > max 60s
```

#### 3. **Error/Exception Failures**
```
FileNotFoundError: Model file not found
ConnectionError: Backend not available at http://127.0.0.1:9000
```

#### 4. **Visual Regression Failures**
```
Screenshot mismatch: 150 pixels differ (max: 100)
```

---

## 📋 Investigation Workflow

### Step 1: Review Test Output

```bash
cd "/Users/vadim/.cursor/worktrees/Validator/SYSTEM GO"
source venv/bin/activate

# Run failing test with verbose output
PYTHONPATH=. pytest rangerio_tests/backend/test_data_ingestion.py::TestDataIngestion::test_import_large_csv -vv

# Capture full traceback
PYTHONPATH=. pytest rangerio_tests/backend/ -vv --tb=long > test_failure_log.txt
```

**What to look for:**
- ✅ Exact assertion that failed
- ✅ Expected vs actual values
- ✅ Full stack trace
- ✅ Timestamps (timing issues?)

### Step 2: Check HTML Report

```bash
# Open the HTML report
open reports/html/report.html
```

**HTML Report shows:**
- ✅ Which tests passed/failed
- ✅ Test duration (performance issues?)
- ✅ Full output and errors
- ✅ System information

### Step 3: Review Logs

```bash
# Check RangerIO backend logs
tail -100 /Users/vadim/.cursor/worktrees/rangerio-backend__Workspace_/udp/backend.log

# Check for errors
grep -i "error\|exception\|failed" /path/to/rangerio/backend.log | tail -20
```

### Step 4: Check Screenshots (E2E failures)

```bash
# View screenshots from failed E2E tests
ls -lht reports/screenshots/*.png | head -5
open reports/screenshots/
```

### Step 5: Check Performance Metrics

```python
# Review performance data from failed tests
# Performance monitor outputs are in test output
```

---

## 🛠️ Common Failure Scenarios & Repairs

### Scenario 1: Backend Not Available

**Symptom:**
```
ConnectionError: Backend not available at http://127.0.0.1:9000
```

**Investigation:**
```bash
# Check if backend is running
curl http://127.0.0.1:9000/health

# Check backend logs
tail -50 ~/path/to/backend.log
```

**Repair:**
```bash
# Start RangerIO backend
cd /Users/vadim/.cursor/worktrees/rangerio-backend__Workspace_/udp
python api/server.py
```

**Verify:**
```bash
# Re-run test
PYTHONPATH=. pytest rangerio_tests/backend/test_data_ingestion.py -v
```

---

### Scenario 2: Model Not Found

**Symptom:**
```
FileNotFoundError: Model file not found: /path/to/qwen3-4b-q4_k_m.gguf
```

**Investigation:**
```bash
# Check if model file exists
ls -lh /Users/vadim/onprem_data/models/qwen3-4b-q4_k_m.gguf

# Check model configuration
cat model_configs.json | grep qwen3
```

**Repair:**
```bash
# Option 1: Fix path in model_configs.json
# Edit model_configs.json with correct path

# Option 2: Download missing model
# Download qwen3-4b model to ~/onprem_data/models/

# Option 3: Use different model
export TEST_MODEL_NAME="llama-3-2-3b-instruct-q4-k-m"
```

**Verify:**
```bash
# Test model is accessible
PYTHONPATH=. python -c "from rangerio_tests.utils.rag_evaluator import RangerIOLLM; llm = RangerIOLLM(); print('Model OK')"
```

---

### Scenario 3: Performance Threshold Exceeded

**Symptom:**
```
AssertionError: Performance: Took 75.2s (max: 60s)
AssertionError: Memory usage 2.3GB > max 2GB
```

**Investigation:**
```bash
# Run test with performance monitoring
PYTHONPATH=. pytest rangerio_tests/backend/test_data_ingestion.py::TestDataIngestion::test_import_large_csv -v

# Check system resources
htop  # or top on macOS
```

**Repair Options:**

**Option 1: Optimize RangerIO**
```python
# Adjust RangerIO settings for performance
# In RangerIO's config/settings.json:
{
  "model_threads": 8,  # Increase threads
  "optimization_profile": "maximum_performance"
}
```

**Option 2: Adjust Test Thresholds**
```python
# In rangerio_tests/config.py:
MAX_IMPORT_TIME_S: int = 90  # Increase from 60 to 90
MAX_MEMORY_MB: int = 3072     # Increase from 2048 to 3072
```

**Option 3: Use Smaller Test Data**
```python
# Generate smaller test file
from rangerio_tests.utils.data_generators import generate_large_dataset
df = generate_large_dataset(25000)  # Half size
df.to_csv('fixtures/test_data/csv/medium_25krows.csv', index=False)
```

**Verify:**
```bash
PYTHONPATH=. pytest rangerio_tests/backend/test_data_ingestion.py::TestDataIngestion::test_import_large_csv -v
```

---

### Scenario 4: RAG Accuracy Too Low

**Symptom:**
```
AssertionError: RAG faithfulness 0.62 < required 0.70
AssertionError: Answer relevancy 0.58 < required 0.70
```

**Investigation:**
```bash
# Run RAG tests with verbose output
PYTHONPATH=. pytest rangerio_tests/integration/test_rag_accuracy.py -vv -s

# Check what answer was generated
# (verbose output shows question, answer, contexts, scores)
```

**Potential Causes:**
- ❌ Model not suitable for task
- ❌ Poor quality test data
- ❌ RAG not properly ingested
- ❌ Prompts need optimization

**Repair Options:**

**Option 1: Use Better Model**
```bash
# Try Qwen 4B instead of Llama 3.2 3B
export TEST_MODEL_NAME="qwen3-4b-q4-k-m"
PYTHONPATH=. pytest rangerio_tests/integration/test_rag_accuracy.py -v
```

**Option 2: Adjust Thresholds (if scores are close)**
```python
# In rangerio_tests/config.py:
MIN_RAG_FAITHFULNESS: float = 0.65  # Lower from 0.70 to 0.65
MIN_RAG_RELEVANCY: float = 0.65     # Lower from 0.70 to 0.65
```

**Option 3: Improve Test Data Quality**
```bash
# Use better quality test documents
# Add more relevant context to RAG
# Ensure data is properly ingested
```

**Option 4: Interactive Validation**
```bash
# Use interactive validation to review borderline cases
PYTHONPATH=. pytest rangerio_tests/ -m interactive

# This will show you the actual answers and ask for validation
# Helps identify if thresholds are too strict
```

**Verify:**
```bash
PYTHONPATH=. pytest rangerio_tests/integration/test_rag_accuracy.py -v
```

---

### Scenario 5: Frontend E2E Test Failure

**Symptom:**
```
TimeoutError: Element not found: text=Prepare Data
Screenshot mismatch: 250 pixels differ
```

**Investigation:**
```bash
# Check screenshots
open reports/screenshots/

# Check if frontend is running
curl http://localhost:5173

# Run with visible browser for debugging
export PLAYWRIGHT_HEADLESS=false
PYTHONPATH=. pytest rangerio_tests/frontend/test_e2e_prepare_wizard.py -v
```

**Repair:**

**Option 1: Frontend Not Running**
```bash
# Start RangerIO frontend
cd /Users/vadim/.cursor/worktrees/rangerio-backend__Workspace_/udp/frontend
npm run dev
```

**Option 2: UI Changed (visual regression)**
```bash
# Update baseline screenshots
PYTHONPATH=. pytest rangerio_tests/frontend/test_visual_regression.py --update-snapshots

# Or adjust tolerance
# In test file: maxDiffPixels=200 (increase from 100)
```

**Option 3: Timing Issue**
```python
# In rangerio_tests/config.py:
PLAYWRIGHT_TIMEOUT: int = 60000  # Increase from 30000 to 60000 (60s)
```

**Verify:**
```bash
PYTHONPATH=. pytest rangerio_tests/frontend/ -v
```

---

### Scenario 6: PII Detection Rate Too Low

**Symptom:**
```
AssertionError: Expected ≥4 PII columns, found 2
AssertionError: PII detection rate 0.85 < required 0.95
```

**Investigation:**
```python
# Check what PII was detected
PYTHONPATH=. pytest rangerio_tests/backend/test_data_ingestion.py::TestDataQuality::test_pii_detection -vv -s

# Review test data
head -20 fixtures/test_data/csv/pii_data.csv
```

**Repair:**

**Option 1: Improve Test Data**
```bash
# Regenerate test data with more obvious PII
PYTHONPATH=. python rangerio_tests/utils/data_generators.py
```

**Option 2: Check RangerIO PII Detection Config**
```python
# Ensure RangerIO has PII detection enabled
# Check config/settings.py or settings UI
```

**Option 3: Adjust Threshold**
```python
# In rangerio_tests/config.py:
MIN_PII_DETECTION_RATE: float = 0.90  # Lower from 0.95 to 0.90
```

**Verify:**
```bash
PYTHONPATH=. pytest rangerio_tests/backend/test_data_ingestion.py::TestDataQuality::test_pii_detection -v
```

---

## 🔄 Repair Iteration Workflow

### The Fix-Verify Cycle

```
┌─────────────────────────────────────────────┐
│ 1. Run Tests                                │
│    pytest rangerio_tests/                   │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ 2. Test Fails                               │
│    - Capture error details                  │
│    - Review HTML report                     │
│    - Check logs & screenshots               │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ 3. Investigate Root Cause                   │
│    - Backend issue?                         │
│    - Model issue?                           │
│    - Performance issue?                     │
│    - Test data issue?                       │
│    - Configuration issue?                   │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ 4. Apply Fix                                │
│    - Fix RangerIO code                      │
│    - Adjust configuration                   │
│    - Improve test data                      │
│    - Update thresholds (if reasonable)      │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ 5. Re-run Specific Test                     │
│    pytest path/to/failing_test.py -v        │
└──────────────┬──────────────────────────────┘
               │
               ├─ Still Fails ──┐
               │                 │
               ▼                 │
┌─────────────────────────┐     │
│ 6. Test Passes ✅       │     │
│    - Document fix       │     │
│    - Update golden data │     │
│    - Run full suite     │     │
└─────────────────────────┘     │
                                │
                                ▼
                    (Back to Step 3: Investigate further)
```

---

## 📊 Debugging Tools

### 1. Verbose Output
```bash
# Show all details
PYTHONPATH=. pytest rangerio_tests/ -vv -s

# Show captured output (print statements)
PYTHONPATH=. pytest rangerio_tests/ -s

# Full traceback
PYTHONPATH=. pytest rangerio_tests/ --tb=long
```

### 2. Run Single Test
```bash
# Run just one test for faster iteration
PYTHONPATH=. pytest rangerio_tests/backend/test_data_ingestion.py::TestDataIngestion::test_import_small_csv -v
```

### 3. Drop into Debugger
```python
# Add to test file:
import pdb; pdb.set_trace()

# Or use pytest debugger
pytest --pdb  # Drop into debugger on failure
```

### 4. Playwright Debug Mode
```bash
# See browser actions in real-time
export PLAYWRIGHT_HEADLESS=false
PYTHONPATH=. pytest rangerio_tests/frontend/ -v

# Slow down actions
PLAYWRIGHT_SLOWMO=1000 PYTHONPATH=. pytest rangerio_tests/frontend/ -v
```

### 5. Performance Profiling
```bash
# Run with benchmarking
PYTHONPATH=. pytest rangerio_tests/backend/ --benchmark-only

# Profile memory
PYTHONPATH=. pytest rangerio_tests/ --memprof
```

---

## 📝 Documenting Fixes

### Update Golden Dataset

When you fix an issue and validate the answer is now correct:

```python
# In test file or interactively:
from rangerio_tests.utils.interactive_validator import InteractiveValidator

validator = InteractiveValidator(golden_output_dir=Path("fixtures/golden_outputs"))

# Save validated answer
validator.save_validation(
    validation_type="rag_answer",
    data={
        "question": "How many rows?",
        "answer": "There are 100 rows in the dataset",
        "ragas_scores": {"faithfulness": 0.85, "relevancy": 0.82}
    },
    user_feedback="correct"
)

validator.save_golden_dataset()
```

### Update Test Comments

```python
# In test file:
def test_import_large_csv(self, ...):
    """
    Test importing large CSV with performance monitoring
    
    FIXED 2025-12-29: Increased timeout from 60s to 90s
    Reason: 50K row import consistently takes 65-75s on M1 Mac
    """
```

### Document in Test Report

Create a `TEST_FINDINGS.md`:

```markdown
# Test Findings & Fixes

## 2025-12-29

### Issue: Large CSV Import Timeout
- **Test**: test_import_large_csv
- **Symptom**: Took 75s, exceeded 60s threshold
- **Root Cause**: M1 Mac slower than expected for 50K rows
- **Fix**: Increased threshold to 90s
- **Status**: ✅ Resolved

### Issue: RAG Faithfulness Low with Llama 3.2 3B
- **Test**: test_rag_accuracy
- **Symptom**: Faithfulness 0.68, required 0.70
- **Root Cause**: Smaller model less accurate for complex queries
- **Fix**: Switched primary model to Qwen 4B
- **Status**: ✅ Resolved, scores now 0.75+
```

---

## ✅ Success Criteria

A test failure is **successfully repaired** when:

1. ✅ **Test passes** consistently (not flaky)
2. ✅ **Root cause understood** and documented
3. ✅ **Fix is appropriate** (not just raising thresholds arbitrarily)
4. ✅ **Full test suite passes** (no regressions)
5. ✅ **Golden dataset updated** if needed
6. ✅ **Documentation updated** with findings

---

## 🚀 Quick Reference

### Fast Debugging Commands

```bash
# Run failing test with full output
PYTHONPATH=. pytest path/to/test.py::test_name -vv -s

# Check backend is running
curl http://127.0.0.1:9000/health

# Check frontend is running
curl http://localhost:5173

# View latest screenshots
open reports/screenshots/

# Check RangerIO logs
tail -50 /path/to/rangerio/backend.log | grep -i error

# Run with different model
TEST_MODEL_NAME="qwen3-4b-q4-k-m" PYTHONPATH=. pytest rangerio_tests/ -v

# Run single test for quick iteration
PYTHONPATH=. pytest rangerio_tests/backend/test_data_ingestion.py::TestDataIngestion::test_import_small_csv
```

---

## 🎯 Remember

**Testing is iterative!** Every failure is:
- ✅ An opportunity to improve RangerIO
- ✅ A chance to refine test data
- ✅ A way to discover edge cases
- ✅ Feedback to make the system more robust

**Don't just make tests pass - make the system better!**

---

**Investigation and repair are core parts of the SYSTEM GO testing workflow! 🔧**








