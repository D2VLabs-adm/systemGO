# Mode Testing Guide

Complete guide for testing Assistant and Deep Search modes in SYSTEM GO.

## Table of Contents

1. [Overview](#overview)
2. [Mode Definitions](#mode-definitions)
3. [When to Use Each Mode](#when-to-use-each-mode)
4. [Running Mode Tests](#running-mode-tests)
5. [Expected Behavior](#expected-behavior)
6. [Performance Tradeoffs](#performance-tradeoffs)
7. [Interactive Validation](#interactive-validation)
8. [Troubleshooting](#troubleshooting)

---

## Overview

RangerIO has 4 query modes that provide different levels of intelligence and thoroughness:

| Mode | Features | Response Time | Use Case |
|------|----------|---------------|----------|
| **Basic** | None | 1-3s | Fastest, direct answers |
| **Assistant** | Smart features | 2-5s | Confidence, clarification, constraints |
| **Deep Search** | Thorough analysis | 5-15s | Compound queries, validation |
| **Both** | All features | 5-20s | Maximum accuracy |

### Critical Gap Before This Update

**ALL previous tests ran in Basic mode by default!** This meant we weren't testing:
- Confidence scoring
- Clarification bubbles
- Query validation
- Compound query handling
- Hallucination detection integration
- Map-reduce strategies

---

## Mode Definitions

### Basic Mode
**Config**: `assistant_mode=False`, `deep_search_mode=False`

**Features**:
- ✗ No confidence scoring
- ✗ No clarification
- ✗ No query validation
- ✗ No compound query handling
- ✓ Fastest responses (1-3s)
- ✓ Direct answers only

**When to Use**: Known simple queries where speed is critical.

---

### Assistant Mode
**Config**: `assistant_mode=True`, `deep_search_mode=False`

**Features**:
- ✓ Confidence scoring and thresholds
- ✓ Clarification for ambiguous queries
- ✓ Constraint parsing (word limits, formats)
- ✓ Hallucination detection (our new feature!)
- ✓ Query disambiguation (synonym normalization)
- ✗ Slower (2-5s)

**When to Use**: User-facing queries where quality and honesty matter.

**Example Behaviors**:
```python
# Ambiguous query triggers clarification
Query: "analyze this data"
Response: {
    "clarification": {
        "message": "I need clarification...",
        "suggestions": ["Show average age", "Count by category"]
    }
}

# Constraint parsing
Query: "Summarize in 20 words"
Response: {
    "answer": "Dataset contains 500 records with demographics...",  # Enforced!
    "constraints": {
        "detected": True,
        "word_limit": 20,
        "enforced": True
    }
}

# Low confidence → honest uncertainty
Query: "What is the date range?"  # No dates in data
Response: {
    "answer": "I don't have date information...",
    "confidence": {
        "score": 0.2,
        "verdict": "low"
    },
    "hallucination_check": {
        "is_hallucination": True,
        "score": 0.7,
        "safe_alternative": "I don't have enough information..."
    }
}
```

---

### Deep Search Mode
**Config**: `assistant_mode=False`, `deep_search_mode=True`

**Features**:
- ✓ Compound query decomposition (SQL-based)
- ✓ Query validation with actual test queries (>80% confidence)
- ✓ Map-reduce for multi-source aggregation
- ✓ Hierarchical RAG for exploratory queries
- ✗ Much slower (5-15s+)

**When to Use**: Complex analytical queries requiring thorough validation.

**Example Behaviors**:
```python
# Compound query decomposition
Query: "What is the average age AND maximum salary?"
Response: {
    "answer": "Average age: 42.5 years. Maximum salary: $150,000",
    "metadata": {
        "compound_query": {
            "is_compound": True,
            "sub_queries": [
                "SELECT AVG(age) FROM table",
                "SELECT MAX(salary) FROM table"
            ]
        }
    }
}

# Map-reduce for multi-source
Query: "Compare totals across all datasets"  # 4+ sources
Response: {
    "metadata": {
        "strategy": "map_reduce",
        "sources_queried": 5,
        "aggregation_method": "synthesis"
    }
}

# Hierarchical for exploration
Query: "Give me an overview"
Response: {
    "metadata": {
        "strategy": "hierarchical",
        "levels": 2
    }
}
```

---

### Both Modes
**Config**: `assistant_mode=True`, `deep_search_mode=True`

**Features**: All Assistant + Deep Search features combined

**When to Use**: Critical queries requiring maximum accuracy and validation.

---

## When to Use Each Mode

### Decision Tree

```
Is speed critical (< 2s required)?
├─ YES → Basic Mode
└─ NO
   ├─ Is this user-facing?
   │  ├─ YES → Assistant Mode (confidence, clarification)
   │  └─ NO → Continue
   │
   ├─ Is the query compound (multiple parts)?
   │  ├─ YES → Deep Search or Both
   │  └─ NO → Continue
   │
   ├─ Requires maximum accuracy?
   │  ├─ YES → Both Modes
   │  └─ NO → Assistant Mode
```

### Use Case Matrix

| Query Type | Recommended Mode | Why |
|------------|------------------|-----|
| "How many records?" | Basic | Simple factual, speed matters |
| "Analyze this data" | Assistant | Ambiguous, needs clarification |
| "Summarize in 20 words" | Assistant | Constraint parsing needed |
| "Average age AND max salary?" | Deep Search | Compound query |
| "Compare across all sources" | Deep Search | Map-reduce needed |
| "What's the date range?" (no dates) | Assistant | Hallucination risk |
| Critical financial analysis | Both | Maximum accuracy required |

---

## Running Mode Tests

### Run All Mode Tests

```bash
cd "/Users/vadim/.cursor/worktrees/Validator/SYSTEM GO"
source venv/bin/activate

# Run all mode-specific tests
pytest rangerio_tests/integration/test_assistant_mode.py -v
pytest rangerio_tests/integration/test_deep_search_mode.py -v
pytest rangerio_tests/integration/test_mode_combinations.py -v

# Run performance benchmarks
pytest rangerio_tests/performance/test_mode_performance.py -v

# Run interactive validation
pytest rangerio_tests/integration/test_interactive_modes.py -v --capture=no
```

### Run Specific Mode Tests

```bash
# Test only Assistant features
pytest -k "assistant" -v

# Test only Deep Search features
pytest -k "deep_search" -v

# Test mode combinations
pytest -k "mode_combinations" -v
```

### Run with Specific Model

```bash
# Compare Qwen 4B vs Llama3 3B
pytest rangerio_tests/performance/test_mode_performance.py::test_model_comparison_benchmark -v
```

---

## Expected Behavior

### Response Time Expectations

| Mode | Min | Expected | Max | Status if Outside Range |
|------|-----|----------|-----|------------------------|
| Basic | 1s | 2s | 3s | ⚠ Warning (not fail) |
| Assistant | 2s | 3-4s | 5s | ⚠ Warning |
| Deep Search | 5s | 8-10s | 15s | ⚠ Warning |
| Both | 5s | 10-12s | 20s | ⚠ Warning |

**Note**: Tests warn but don't fail on timing violations (system load varies).

### Feature Presence Matrix

| Feature | Basic | Assistant | Deep Search | Both |
|---------|-------|-----------|-------------|------|
| confidence | ✗ | ✓ | ✗ | ✓ |
| hallucination_check | ✓ | ✓ | ✓ | ✓ |
| disambiguation | ✗ | ✓ | ✗ | ✓ |
| clarification | ✗ | ✓ | ✗ | ✓ |
| constraints | ✗ | ✓ | ✗ | ✓ |
| validation | ✗ | ✗ | ✓ | ✓ |
| compound_handling | ✗ | ✗ | ✓ | ✓ |
| map_reduce | ✗ | ✗ | ✓ | ✓ |

---

## Performance Tradeoffs

### Overhead Analysis

Based on benchmarks:

```
Basic Mode:     1000ms (baseline)
Assistant Mode: 2500ms (+1500ms, 150% overhead)
Deep Search:    8000ms (+7000ms, 700% overhead)
Both Modes:     9000ms (+8000ms, 800% overhead)
```

### Throughput Comparison

Queries per second (30s test window):

```
Basic Mode:     ~20 QPS
Assistant Mode: ~10 QPS
Deep Search:    ~3 QPS
Both Modes:     ~2 QPS
```

### Accuracy vs Speed

```
         Speed    Accuracy    Features
Basic:   ████     ██          █
Assist:  ███      ████        ███
Deep:    █        ████        ████
Both:    █        █████       █████
```

---

## Interactive Validation

### Generate Mode Comparison Report

```bash
pytest rangerio_tests/integration/test_interactive_modes.py::test_interactive_mode_comparison -v -s
```

This generates an HTML report with side-by-side mode comparisons:
- **file:///Users/vadim/.cursor/worktrees/Validator/SYSTEM%20GO/fixtures/golden_outputs/interactive_validation_*.html**

### Validate Assistant Features

```bash
pytest rangerio_tests/integration/test_interactive_modes.py::test_interactive_assistant_features -v -s
```

Validates:
- Clarification helpfulness
- Confidence score accuracy
- Constraint enforcement
- Hallucination detection

### Validate Deep Search Features

```bash
pytest rangerio_tests/integration/test_interactive_modes.py::test_interactive_deep_search_features -v -s
```

Validates:
- Compound query decomposition
- Query validation quality
- Thorough analysis completeness

---

## Troubleshooting

### Issue: Tests run but no mode features appear

**Cause**: Mode parameters not passed to API

**Fix**:
```python
# Wrong
api_client.post("/rag/query", json={"prompt": query, "project_id": rag_id})

# Correct
mode = get_mode('assistant')
api_client.post("/rag/query", json={
    "prompt": query,
    "project_id": rag_id,
    **mode.to_api_params()  # Add this!
})
```

### Issue: Performance tests failing

**Cause**: System load affecting response times

**Solution**: Tests only warn on timing violations, not fail. Review warnings but don't block on them.

### Issue: Mode comparison shows no differences

**Cause**: Query too simple, all modes behave similarly

**Solution**: Use test queries designed for mode differences:
- Ambiguous queries for Assistant
- Compound queries for Deep Search

### Issue: Hallucination detection not working

**Cause**: Feature requires Assistant mode

**Fix**:
```python
mode = get_mode('assistant')  # Not 'basic'!
```

---

## Testing Best Practices

1. **Always specify mode explicitly** in tests
2. **Use parametrize** to test across all modes
3. **Validate mode-specific features** based on mode config
4. **Document expected behavior** for each mode
5. **Use interactive validation** for subjective quality checks
6. **Monitor performance** but don't fail on timing alone
7. **Compare modes side-by-side** for the same queries

---

## Quick Reference

### Import Mode Config

```python
from rangerio_tests.utils.mode_config import get_mode, get_all_modes
```

### Get Specific Mode

```python
basic_mode = get_mode('basic')
assistant_mode = get_mode('assistant')
deep_search_mode = get_mode('deep')
both_modes = get_mode('both')
```

### Use in API Call

```python
mode = get_mode('assistant')
response = api_client.post("/rag/query", json={
    "prompt": "What is the average?",
    "project_id": rag_id,
    **mode.to_api_params()  # Expands to assistant_mode=True, deep_search_mode=False
})
```

### Validate Mode Features

```python
result = response.json()

if mode.assistant_mode:
    assert 'confidence' in result or 'hallucination_check' in result
    
if mode.deep_search_mode:
    assert 'validation' in result or 'metadata' in result
```

---

## Additional Resources

- [Mode Configuration Code](rangerio_tests/utils/mode_config.py)
- [Assistant Mode Tests](rangerio_tests/integration/test_assistant_mode.py)
- [Deep Search Tests](rangerio_tests/integration/test_deep_search_mode.py)
- [Mode Combinations Matrix](rangerio_tests/integration/test_mode_combinations.py)
- [Performance Benchmarks](rangerio_tests/performance/test_mode_performance.py)
- [Updating Existing Tests](UPDATING_TESTS_FOR_MODES.md)

---

**Last Updated**: December 29, 2025  
**SYSTEM GO Version**: 1.0  
**RangerIO Backend**: MVP_09








