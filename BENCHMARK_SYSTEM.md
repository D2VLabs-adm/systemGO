# RangerIO Benchmark System

## Overview

The SYSTEM GO testing framework includes a comprehensive benchmarking system that:

1. ✅ **Saves benchmark results** for historical comparison
2. ✅ **Compares different models** (e.g., Qwen 4B vs Llama3 3B)
3. ✅ **Tracks performance trends** over time
4. ✅ **Generates comparison reports** for analysis

---

## Benchmark Tests (Stage 4)

### Test Suite: `test_mode_performance.py`

The following 5 benchmark tests run in Stage 4:

#### 1. `test_mode_response_time_distribution`
- **What it measures:** P50, P95, P99 latencies across all modes
- **Sample size:** 50 queries per mode (10 iterations × 5 queries)
- **Duration:** ~15-20 minutes
- **Saved metrics:**
  - `count`: Number of successful queries
  - `avg_ms`: Average response time
  - `p50_ms`: Median (50th percentile)
  - `p95_ms`: 95th percentile
  - `p99_ms`: 99th percentile
  - `std_ms`: Standard deviation
  - `min_ms`, `max_ms`: Range

#### 2. `test_mode_overhead_analysis`
- **What it measures:** Overhead of smart modes vs Basic mode
- **Sample size:** 10 queries per mode
- **Expected overheads:**
  - Assistant: +1-3 seconds
  - Deep Search: +4-12 seconds
  - Both: +4-15 seconds

#### 3. `test_throughput_comparison`
- **What it measures:** Queries per second (QPS) for each mode
- **Duration:** 30 seconds per mode
- **Saved metrics:**
  - `queries`: Total query count
  - `success`: Successful queries
  - `qps`: Queries per second
  - `avg_response_ms`: Average response time

#### 4. `test_model_comparison_benchmark`
- **What it measures:** Cross-model performance
- **Queries:** 3 representative queries
- **Saved metrics:**
  - `avg_response_time_ms`
  - `avg_answer_length`
  - `accuracy_score` (from validation tests)

#### 5. `test_generate_performance_report`
- **What it measures:** Comprehensive performance snapshot
- **Queries:** 5 queries per mode
- **Output:** Formatted report with all key metrics

---

## Where Results Are Saved

### File Structure
```
/Users/vadim/.cursor/worktrees/Validator/SYSTEM GO/reports/benchmarks/
├── benchmark_20251229_204500.json    # Run 1 (Qwen 4B)
├── benchmark_20251229_210730.json    # Run 2 (Llama3 3B)
├── benchmark_20251230_093045.json    # Run 3 (future)
└── index.json                        # Quick lookup index
```

### Benchmark File Format
```json
{
  "run_id": "benchmark_20251229_204500",
  "results": [
    {
      "timestamp": "2025-12-29T20:45:00",
      "test_name": "test_mode_response_time_distribution",
      "mode": "basic",
      "model": "qwen3-4b-q4-k-m",
      "metrics": {
        "avg_ms": 1250,
        "p50_ms": 1180,
        "p95_ms": 1520,
        "p99_ms": 1680,
        "count": 50
      },
      "metadata": {
        "rag_id": 123,
        "sample_size": 50
      }
    }
  ]
}
```

---

## How to Use

### 1. Run Benchmarks (Already Built-In)

Stage 4 tests **automatically save** to the benchmark database:

```bash
cd "/Users/vadim/.cursor/worktrees/Validator/SYSTEM GO"
./run_mode_tests_safely.sh  # Runs all 4 stages, Stage 4 = benchmarks
```

Or run just Stage 4:

```bash
cd "/Users/vadim/.cursor/worktrees/Validator/SYSTEM GO"
source venv/bin/activate
PYTHONPATH=. pytest rangerio_tests/performance/test_mode_performance.py -v \
  --html=reports/html/4_performance_benchmarks.html \
  --self-contained-html
```

---

### 2. Compare Two Models

After running benchmarks with different models:

```bash
python compare_benchmarks.py compare \
  --models qwen3-4b-q4-k-m llama-3-2-3b-instruct-q4-k-m \
  --mode basic
```

**Output:**
```
📊 Comparing Models: qwen3-4b-q4-k-m, llama-3-2-3b-instruct-q4-k-m
Mode: basic
==================================================================

Test                                     Model 1              Model 2              Difference
---------------------------------------- -------------------- -------------------- ---------------
test_mode_response_time_distribution      1250ms               1480ms               +230ms (+18.4%)
test_mode_overhead_analysis              1180ms               1520ms               +340ms (+28.8%)
test_throughput_comparison               1300ms               1450ms               +150ms (+11.5%)
```

---

### 3. Track Performance Trend Over Time

See how a model's performance changes across runs:

```bash
python compare_benchmarks.py trend \
  --model qwen3-4b-q4-k-m \
  --test test_mode_response_time_distribution \
  --metric p50_ms \
  --mode basic
```

**Output:**
```
📈 Performance Trend
Model: qwen3-4b-q4-k-m
Test: test_mode_response_time_distribution
Metric: p50_ms
==================================================================

Timestamp                 Value
------------------------- ---------------
2025-12-29T20:45:00        1180.00
2025-12-29T22:15:00        1150.00
2025-12-30T09:30:00        1120.00

📊 Summary:
  First:  1180.00
  Latest: 1120.00
  Change: -60.00 (-5.1%)
```

---

### 4. Generate Full Comparison Report

Create a comprehensive markdown report:

```bash
python compare_benchmarks.py report \
  --output reports/benchmarks/my_comparison.md
```

---

## Comparing Against Future Runs

### Scenario 1: Test Code Changes

```bash
# Run 1: Baseline (before optimization)
./run_mode_tests_safely.sh

# ... make code changes ...

# Run 2: After optimization
./run_mode_tests_safely.sh

# Compare
python compare_benchmarks.py report
```

### Scenario 2: Test Different Models

```bash
# Step 1: Test with Qwen 4B (current)
./run_mode_tests_safely.sh

# Step 2: Switch model in RangerIO backend to Llama3 3B
# (Edit config or restart backend with different model)

# Step 3: Run benchmarks again
./run_mode_tests_safely.sh

# Step 4: Compare
python compare_benchmarks.py compare \
  --models qwen3-4b-q4-k-m llama-3-2-3b-instruct-q4-k-m
```

### Scenario 3: Weekly Performance Tracking

```bash
# Run benchmarks weekly and track trends
python compare_benchmarks.py trend \
  --model qwen3-4b-q4-k-m \
  --test test_mode_response_time_distribution \
  --metric p50_ms
```

---

## Current Status

✅ **Stage 1 Complete:** Assistant Mode tests (12/25 tests done)
✅ **Stage 2 Complete:** Deep Search Mode tests (12/25 tests done)
⏳ **Stage 3 Pending:** Mode Combination Matrix (8 tests)
⏳ **Stage 4 Pending:** Performance Benchmarks (5 tests) - **THIS SAVES TO DB**

Once Stage 4 completes, you'll have your first baseline benchmark! 🎯

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `./run_mode_tests_safely.sh` | Run all tests + Stage 4 benchmarks |
| `python compare_benchmarks.py compare --models A B` | Compare two models |
| `python compare_benchmarks.py trend --model X --test Y` | Show performance trend |
| `python compare_benchmarks.py report` | Generate full report |

---

## HTML Reports vs Benchmark DB

| Feature | HTML Reports | Benchmark DB |
|---------|--------------|--------------|
| **Visual test results** | ✅ Yes | ❌ No |
| **Pass/Fail status** | ✅ Yes | ❌ No |
| **Performance metrics** | ⚠️ Static | ✅ Queryable |
| **Cross-run comparison** | ❌ No | ✅ Yes |
| **Trend analysis** | ❌ No | ✅ Yes |
| **Model comparison** | ❌ No | ✅ Yes |

**Both are valuable!** HTML reports are for immediate test review, the Benchmark DB is for long-term performance tracking.

---

**Generated by:** SYSTEM GO Testing Framework
**Documentation Version:** 1.0
**Last Updated:** 2025-12-29






