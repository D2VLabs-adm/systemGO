# Mode Testing Issues - Analysis & Fixes

**Date:** 2025-12-29
**Test Run:** Stage 3 (Mode Combinations)
**Status:** 8/8 tests passed, but 4 critical issues identified

---

## 🔍 Issues Identified

### 1. ❌ **No Accuracy Metrics**
**Problem:** All tests show `accuracy_score: 'N/A'`

**Root Cause:**
```python
# In test_mode_combinations.py line 251
comparison_results[mode_name] = {
    'avg_response_time_ms': elapsed_ms,
    'accuracy_score': 'N/A',  # ← Hardcoded!
    'answer_length': len(result.get('answer', '')),
    'features': []
}
```

**Why:**
- Accuracy requires **human evaluation** or **ragas scoring**
- Tests were designed to run without ragas to avoid delays
- **Solution:** Add accuracy scoring using ragas or golden dataset comparison

---

### 2. ❌ **Clarification Tests Failed (✗ in output)**
**Problem:** All clarification tests show `✗` (not present)

**Root Cause:**
The backend **does not return `clarification` field** in standard queries!

**Current Response Structure** (from `api/rag.py:1620-1649`):
```python
return {
    "answer": answer,
    "sources": sources,
    "used_rag": True,
    "confidence": {...},
    "disambiguation": {...},        # ✅ Present
    "hallucination_check": {...},   # ✅ Present
    "constraints": {...},           # ✅ Present
    "performance": {...}            # ✅ Present
    # ❌ NO 'clarification' field!
    # ❌ NO 'validation' field (unless use_validation=True)
    # ❌ NO 'metadata' field!
}
```

**Only when `use_validation=True`** (line 1504-1535):
```python
return {
    ...
    "validation": validated_result.validation_details,  # ✅ Only in deep validation mode
    # But still NO 'clarification' or 'metadata'!
}
```

**The `clarification` field exists in `ValidatedRAGResponse`** but is never mapped to the API response!

---

### 3. ❌ **Validation Tests Failed (✗ in output)**
**Problem:** All validation tests show `✗` (not present)

**Root Cause:**
- Validation is **only enabled** when `use_validation=True`
- BUT the test modes use `deep_search_mode=True`, which doesn't trigger validation
- Validation path (line 1504): `if body.use_validation and body.data_source_ids:`

**What's Happening:**
```python
# In test_mode_combinations.py:
mode_config.to_api_params()  # Returns { assistant_mode: True/False, deep_search_mode: True/False }

# Backend expects:
use_validation = True  # But this is never set by the tests!
```

---

### 4. ❌ **Metadata Tests Failed (✗ in output)**
**Problem:** All metadata tests show `✗` (not present)

**Root Cause:**
The backend **never returns a top-level `metadata` field**!

**What's Available:**
- `performance.cache_hit` ✅
- `performance.response_time_ms` ✅
- `confidence.score` ✅
- But no `metadata.strategy` or `metadata.mode` ❌

**Tests expect** (line 261):
```python
if result.get('metadata', {}).get('strategy'):
    comparison_results[mode_name]['features'].append(result['metadata']['strategy'])
```

**Backend provides:** (line 1645-1649)
```python
"performance": {
    "cache_hit": cache_hit,
    "response_time_ms": response_time_ms,
    "tokens": tokens
}
# ❌ No 'metadata' field!
```

---

## 🛠️ Required Fixes

### Fix 1: Add Accuracy Scoring

**Option A: Use ragas (slow but accurate)**
```python
# In test_mode_combinations.py
from rangerio_tests.utils.rag_evaluator import RAGEvaluator

evaluator = RAGEvaluator(backend_url=api_client.base_url)
metrics = evaluator.evaluate_answer(
    question=query,
    answer=result.get('answer', ''),
    contexts=[s.get('document', '') for s in result.get('sources', [])]
)

comparison_results[mode_name] = {
    'accuracy_score': metrics.get('faithfulness', 0.0),  # ✅ Real score
    ...
}
```

**Option B: Golden dataset comparison (fast)**
```python
# Compare answer against known correct answers
golden_answers = load_golden_dataset()
accuracy = calculate_similarity(result.get('answer'), golden_answers[query])
```

---

### Fix 2: Add Clarification Field to Backend Response

**File:** `api/rag.py` (line 1620)

**Add:**
```python
def should_request_clarification(prompt: str, confidence_score: float, constraints: ConstraintInfo) -> dict:
    """Determine if clarification is needed."""
    reasons = []
    
    # Check ambiguity
    ambiguous_indicators = ['this', 'that', 'analyze', 'summarize', 'explain']
    if any(word in prompt.lower().split() for word in ambiguous_indicators):
        if len(prompt.split()) < 5:  # Short ambiguous query
            reasons.append("Query is too vague - please specify what you want to analyze")
    
    # Check low confidence
    if confidence_score < 0.3:
        reasons.append("Low confidence in answer - please provide more context")
    
    # Check conflicting constraints
    if constraints.word_limit and constraints.word_limit < 10:
        reasons.append("Word limit too restrictive for meaningful answer")
    
    needs_clarification = len(reasons) > 0
    
    return {
        "needed": needs_clarification,
        "reasons": reasons,
        "suggested_questions": generate_clarifying_questions(prompt, reasons) if needs_clarification else []
    }
```

**Then in response** (line 1620):
```python
# Generate clarification if needed
clarification_info = should_request_clarification(body.prompt, confidence.get('score', 0), constraints)

return {
    "answer": answer,
    "sources": sources,
    "used_rag": True,
    "confidence": confidence,
    "clarification": clarification_info if clarification_info['needed'] else None,  # ✅ NEW
    "disambiguation": ...,
    "hallucination_check": ...,
    "constraints": ...,
    "performance": ...
}
```

---

### Fix 3: Map `deep_search_mode` to `use_validation`

**File:** `api/rag.py` (line 1504)

**Change from:**
```python
if body.use_validation and body.data_source_ids:
```

**To:**
```python
# Map deep_search_mode to use_validation for backward compatibility
use_deep_validation = body.use_validation or body.deep_search_mode

if use_deep_validation and body.data_source_ids:
```

---

### Fix 4: Add Metadata Field

**File:** `api/rag.py` (line 1620)

**Add:**
```python
# Determine which strategy was used
strategy = "standard_rag"
if body.deep_search_mode:
    strategy = "deep_search" if body.deep_search_mode else "standard_rag"
if body.assistant_mode:
    strategy = f"{strategy}_with_assistant" if strategy != "standard_rag" else "assistant"

return {
    "answer": answer,
    "sources": sources,
    "used_rag": True,
    "confidence": confidence,
    "clarification": ...,
    "disambiguation": ...,
    "hallucination_check": ...,
    "constraints": ...,
    "metadata": {  # ✅ NEW
        "strategy": strategy,
        "mode": {
            "assistant": body.assistant_mode,
            "deep_search": body.deep_search_mode
        },
        "features_active": {
            "disambiguation": disambiguation_info is not None,
            "hallucination_check": True,
            "constraints": constraints.has_constraints() if constraints else False,
            "validation": use_deep_validation
        }
    },
    "performance": ...
}
```

---

## 🧪 Add to Interactive Tests

As you correctly identified, these features need **human validation**:

### Test Additions Needed:

**File:** `rangerio_tests/integration/test_interactive_modes.py` (enhance existing)

```python
def test_interactive_clarification_quality(interactive_validator, api_client, sample_csv_small):
    """
    Human validates that clarification requests are helpful and accurate.
    """
    ambiguous_queries = [
        "analyze this",
        "what about that?",
        "explain",
        "summarize the data"
    ]
    
    # Create RAG
    rag_id = create_test_rag(api_client, sample_csv_small)
    
    for query in ambiguous_queries:
        # Test with Assistant mode (should request clarification)
        resp = api_client.post("/rag/query", json={
            "prompt": query,
            "project_id": rag_id,
            "assistant_mode": True
        })
        
        result = resp.json()
        
        # Show user the clarification request
        interactive_validator.display_clarification_request(
            query=query,
            clarification=result.get('clarification'),
            answer=result.get('answer')
        )
```

**Add to InteractiveValidator** (`rangerio_tests/utils/interactive_validator.py`):

```python
def display_clarification_request(self, query: str, clarification: dict, answer: str):
    """Display clarification request for human review."""
    item_id = len(self.html_items)
    self.html_items.append({
        'type': 'clarification',
        'id': item_id,
        'query': query,
        'clarification_needed': clarification.get('needed', False) if clarification else False,
        'reasons': clarification.get('reasons', []) if clarification else [],
        'suggested_questions': clarification.get('suggested_questions', []) if clarification else [],
        'answer_provided': answer
    })
    
    # Auto-assess
    is_appropriate = clarification is not None and clarification.get('needed') == True
    
    return {
        "is_appropriate": is_appropriate,
        "timestamp": datetime.now().isoformat(),
        "item_id": item_id
    }
```

---

## 📊 Summary

| Issue | Status | Impact | Fix Priority |
|-------|--------|--------|--------------|
| No accuracy metrics | ❌ Not implemented | Can't compare model quality | 🔴 HIGH |
| Clarification not returned | ❌ Backend missing | Feature not testable | 🔴 HIGH |
| Validation not triggered | ❌ Logic mismatch | Deep Search incomplete | 🟡 MEDIUM |
| Metadata not returned | ❌ Backend missing | Can't track strategies | 🟢 LOW |

---

## ✅ Action Plan

1. **Immediate:** Add backend fixes to return `clarification` and `metadata` fields
2. **Short-term:** Integrate ragas or golden dataset for accuracy scoring
3. **Interactive tests:** Add clarification quality tests
4. **Validation:** Map `deep_search_mode` → `use_validation`

---

**Generated by:** SYSTEM GO Analysis
**Test Run:** Stage 3 Complete (8/8 passed, 4 improvements needed)
**Next:** Implement fixes and rerun






