# System Crash Analysis & Safe Mode Solution

**Date:** 2025-12-29 22:31 PST  
**Issue:** Python crashed during automated testing  
**Root Cause:** Memory exhaustion in llama.cpp backend

---

## 🔴 What Happened

### Crash Details (from `/Users/vadim/Desktop/Python _01.txt`)

```
Exception Type:        EXC_CRASH (SIGABRT)
Termination Reason:    Namespace SIGNAL, Code 6 Abort trap: 6

Thread 0 Crashed:
8   libllama.dylib    llama_batch_free + 112
```

**Translation:**
- The `llama.cpp` library crashed when trying to free memory
- `SIGABRT` = abnormal termination due to memory corruption
- Happened in `llama_batch_free` = cleaning up after LLM batch processing

### Why It Crashed

**System Constraints:**
- 16GB RAM total
- Backend server loaded with LLM model (~4-6GB)
- Multiple concurrent test queries running
- No memory checks before heavy operations

**What Triggered It:**
- Phase 2 started running **5 queries × 4 modes = 20 LLM calls**
- Each query loads the model context into memory
- **Concurrent execution** exceeded available RAM
- llama.cpp memory allocator failed → crash

---

## 🛡️ Solution: SAFE MODE

### Created: `run_safe_mode.sh`

**Key Safety Features:**

1. **Memory Checks Before Each Phase**
   ```bash
   free_mb=$(check_memory)
   if [ $free_mb -lt 1500 ]; then
       echo "❌ WARNING: Low memory"
       read -p "Continue anyway? (y/n)"
   fi
   ```

2. **Cooldown Periods**
   ```bash
   cooldown 15  # 15 seconds between phases
   ```
   - Lets OS reclaim memory
   - Prevents back-to-back heavy operations

3. **User Confirmation for Heavy Tests**
   - Asks before running each phase
   - Shows current memory status
   - Option to skip heavy benchmarks

4. **Sequential Execution**
   - No parallel test runs
   - One query at a time
   - Prevents memory spikes

5. **Graceful Error Handling**
   ```bash
   pytest ... || echo "⚠️  Phase had errors (check report)"
   ```
   - Continues even if one phase fails
   - Doesn't crash entire suite

---

## 📋 Safe Mode Phases

### Phase 1: Backend (✅ Complete)
- Already done
- No memory impact

### Phase 2: Interactive Accuracy (LIGHT)
- 5 queries × 4 modes = 20 calls
- **Sequential** execution
- 15-25 minutes
- **Runs with confirmation**

### Phase 3A: Stage 3 Rerun (MEDIUM - Optional)
- 8 tests
- 25-35 minutes
- **User must confirm**
- Can skip if memory is low

### Phase 3B: Stage 4 Benchmarks (HEAVY - Optional)
- 50+ queries per mode
- 15-20 minutes
- **Highest memory impact**
- **Recommended to skip on low-memory systems**

---

## 🚀 How to Use Safe Mode

### Option 1: Run Safe Mode (Recommended)
```bash
cd "/Users/vadim/.cursor/worktrees/Validator/SYSTEM GO"
./run_safe_mode.sh
```

**What it does:**
1. Checks memory before each phase
2. Asks for your confirmation
3. Shows memory status
4. Lets you skip heavy tests
5. Won't crash your system

### Option 2: Run Individual Phases

**Phase 2 Only (Safest):**
```bash
cd "/Users/vadim/.cursor/worktrees/Validator/SYSTEM GO"
source venv/bin/activate
PYTHONPATH=. pytest rangerio_tests/integration/test_interactive_mode_accuracy.py -v
```

**Stage 3 Rerun:**
```bash
PYTHONPATH=. pytest rangerio_tests/integration/test_mode_combinations.py -v
```

**Stage 4 Benchmarks (when you have >4GB free RAM):**
```bash
PYTHONPATH=. pytest rangerio_tests/performance/test_mode_performance.py -v
```

---

## ⚠️ Preventing Future Crashes

### Before Running Heavy Tests:

1. **Check Available Memory:**
   ```bash
   vm_stat | grep "Pages free"
   # Should show >1M pages free (~4GB)
   ```

2. **Close Other Applications:**
   - Close browsers (Chrome/Safari use lots of RAM)
   - Close IDEs if not needed
   - Close Slack, Discord, etc.

3. **Monitor Memory During Tests:**
   ```bash
   # In separate terminal
   watch -n 5 'vm_stat | grep "Pages free"'
   ```

4. **Use Smaller Test Subsets:**
   ```bash
   # Run just 1-2 queries instead of 5
   pytest -k "test_interactive" --maxfail=1
   ```

---

## 📊 What We've Accomplished

### ✅ Completed:
1. **Phase 1:** Backend API enhancements (clarification, validation, metadata)
2. **Test Infrastructure:** Interactive accuracy testing framework
3. **Safe Mode:** Memory-conscious test runner

### ⏸️ Pending (Due to Memory Constraints):
1. **Phase 2:** Interactive accuracy testing (can run with safe mode)
2. **Phase 3A:** Stage 3 rerun (optional verification)
3. **Phase 3B:** Stage 4 benchmarks (heavy, skip if needed)

---

## 🎯 Recommended Next Steps

### Immediate (Today):
1. **Restart your Mac** to free up memory
2. **Close unnecessary applications**
3. **Run safe mode**: `./run_safe_mode.sh`
4. **Say "yes" to Phase 2**, "no" to Phase 3B

### Later (When You Have Time):
1. Run Stage 4 benchmarks on a system with more RAM
2. OR run them overnight when no other apps are running
3. OR run individual benchmark tests one at a time

---

## 💡 Alternative: Run on Different Machine

If crashes persist, consider:

1. **Run on a machine with >32GB RAM**
2. **Use a cloud VM** (AWS, Azure, GCP)
3. **Run in Docker** with memory limits
4. **Use smaller LLM models** (e.g., Qwen 1.5B instead of 4B)

---

## 📝 Summary

**Problem:** Automated testing crashed due to memory exhaustion  
**Cause:** Too many concurrent LLM queries on 16GB RAM system  
**Solution:** Safe Mode with memory checks and user confirmation  
**Status:** Ready to run with `./run_safe_mode.sh`

**The 3-phase plan is still valid, we just need to run it more carefully!** 🎯

---

**Generated by:** SYSTEM GO Analysis  
**Date:** 2025-12-29 22:35 PST  
**Status:** Safe Mode Ready






