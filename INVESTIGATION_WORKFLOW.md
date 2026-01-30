# SYSTEM GO - Investigation & Repair: Quick Reference

## ✅ Yes, We Investigate & Repair Failures!

**SYSTEM GO is designed as an iterative improvement workflow**, not just a pass/fail validator.

---

## 🔄 The Complete Workflow

```
Run Tests → Failures Detected → Investigate → Fix → Verify → Document → Repeat
```

### What Happens When a Test Fails?

1. **🔍 Detailed Diagnostics Generated Automatically**
   - Full HTML report with errors
   - Screenshots (for E2E tests)
   - Performance metrics
   - Stack traces
   - Logs

2. **🛠️ Investigation Tools Available**
   - Verbose output (`-vv -s`)
   - Single test re-runs
   - Debug mode (Playwright)
   - Performance profiling
   - Interactive validation

3. **✅ Fix & Verify Cycle**
   - Identify root cause
   - Apply fix (code, config, or data)
   - Re-run specific test
   - Confirm resolution
   - Run full suite

4. **📊 Documentation & Learning**
   - Update golden dataset
   - Document findings
   - Improve test data
   - Refine thresholds

---

## 📋 Investigation Checklist

When a test fails:

- [ ] **Review verbose output** - What exactly failed?
- [ ] **Check HTML report** - Full context and timing
- [ ] **View screenshots** - Visual state at failure (E2E)
- [ ] **Check logs** - Backend/frontend errors
- [ ] **Verify services** - Backend/frontend running?
- [ ] **Check model** - Correct model loaded?
- [ ] **Review metrics** - Performance/memory issues?

---

## 🛠️ Common Fixes

### Backend Issues
```bash
# Start backend if not running
cd /Users/vadim/.cursor/worktrees/rangerio-backend__Workspace_/udp
python api/server.py
```

### Frontend Issues
```bash
# Start frontend if not running
cd /Users/vadim/.cursor/worktrees/rangerio-backend__Workspace_/udp/frontend
npm run dev
```

### Model Issues
```bash
# Verify model exists
ls -lh /Users/vadim/onprem_data/models/

# Use different model
export TEST_MODEL_NAME="llama-3-2-3b-instruct-q4-k-m"
```

### Performance Issues
```python
# Adjust thresholds in rangerio_tests/config.py
MAX_IMPORT_TIME_S: int = 90  # Increase if needed
MAX_MEMORY_MB: int = 3072     # Adjust for your system
```

### Data Quality Issues
```bash
# Regenerate test data
PYTHONPATH=. python rangerio_tests/utils/data_generators.py
```

---

## 🚀 Fast Iteration Commands

```bash
# Run single failing test with full output
PYTHONPATH=. pytest path/to/test.py::test_name -vv -s

# Re-run just failures
PYTHONPATH=. pytest --lf -v

# Debug with visual browser
export PLAYWRIGHT_HEADLESS=false
PYTHONPATH=. pytest rangerio_tests/frontend/ -v

# Check what's wrong
curl http://127.0.0.1:9000/health
curl http://localhost:5173
```

---

## 📚 Full Documentation

- **TEST_FAILURE_GUIDE.md** - Complete investigation & repair guide
- **MODEL_TESTING_GUIDE.md** - Model-specific testing
- **README.md** - Getting started and usage
- **IMPLEMENTATION_SUMMARY.md** - Full feature overview

---

## 🎯 Philosophy

**Testing is not about passing tests - it's about improving the system!**

Every failure is:
- ✅ A bug discovered
- ✅ An edge case identified  
- ✅ An opportunity to optimize
- ✅ Feedback for better quality

**We investigate → understand → fix → verify → document**

---

## ✅ Success Criteria for a "Fixed" Test

1. ✅ Test passes consistently (not flaky)
2. ✅ Root cause understood and documented
3. ✅ Fix is appropriate (not arbitrary threshold raising)
4. ✅ Full test suite still passes (no regressions)
5. ✅ Golden dataset updated if needed
6. ✅ Findings documented for future reference

---

**SYSTEM GO = Comprehensive Testing + Investigation + Continuous Improvement! 🚀**








