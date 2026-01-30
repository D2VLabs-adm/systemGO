# How to Update Existing Tests with Mode Parameters

## Overview
This guide shows how to add mode testing support to existing RAG query tests.

## Before (Without Mode Support)

```python
def test_rag_query(api_client, sample_csv_small):
    # Create RAG
    rag_response = api_client.post("/projects", json={"name": "Test"})
    rag_id = rag_response.json()["id"]
    
    # Upload data
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    
    # Query (missing mode parameters!)
    query_resp = api_client.post("/rag/query", json={
        "prompt": "How many records?",
        "project_id": rag_id
    })
    
    assert query_resp.status_code == 200
```

## After (With Mode Support)

### Option 1: Add Default Mode (Quick Fix)

```python
def test_rag_query(api_client, sample_csv_small, assistant_mode):
    # Create RAG
    rag_response = api_client.post("/projects", json={"name": "Test"})
    rag_id = rag_response.json()["id"]
    
    # Upload data
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    
    # Query with Assistant mode
    query_resp = api_client.post("/rag/query", json={
        "prompt": "How many records?",
        "project_id": rag_id,
        **assistant_mode.to_api_params()  # NEW: Add mode parameters
    })
    
    assert query_resp.status_code == 200
```

### Option 2: Parametrize Across All Modes (Comprehensive)

```python
@pytest.mark.parametrize("mode_name", ['basic', 'assistant', 'deep', 'both'])
def test_rag_query_all_modes(api_client, sample_csv_small, mode_name):
    from rangerio_tests.utils.mode_config import get_mode
    
    mode = get_mode(mode_name)
    
    # Create RAG
    rag_response = api_client.post("/projects", json={"name": f"Test {mode_name}"})
    rag_id = rag_response.json()["id"]
    
    # Upload data
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    
    # Query with specified mode
    query_resp = api_client.post("/rag/query", json={
        "prompt": "How many records?",
        "project_id": rag_id,
        **mode.to_api_params()  # NEW: Add mode parameters
    })
    
    assert query_resp.status_code == 200
    
    # Validate mode-specific features
    result = query_resp.json()
    if mode.assistant_mode:
        assert 'confidence' in result or 'hallucination_check' in result
```

### Option 3: Use mode_config Fixture

```python
def test_rag_query_with_fixture(api_client, sample_csv_small, mode_config):
    """This test will run 4 times (once per mode) automatically"""
    
    # Create RAG
    rag_response = api_client.post("/projects", json={
        "name": f"Test {mode_config.name}"
    })
    rag_id = rag_response.json()["id"]
    
    # Upload data
    upload_resp = api_client.upload_file(
        "/datasources/connect",
        sample_csv_small,
        data={'project_id': str(rag_id), 'source_type': 'file'}
    )
    
    # Query with mode from fixture
    query_resp = api_client.post("/rag/query", json={
        "prompt": "How many records?",
        "project_id": rag_id,
        **mode_config.to_api_params()  # Use fixture
    })
    
    assert query_resp.status_code == 200
```

## Files to Update

Update these files with mode parameters:

1. **test_rag_accuracy.py** - Add assistant_mode by default
2. **test_rag_benchmark.py** - Parametrize across all modes
3. **test_interactive_rag.py** - Add mode metadata to HTML reports
4. **test_validation_fixes.py** - Test with assistant_mode (hallucination detection)

## Key Changes

1. **Import mode_config**:
   ```python
   from rangerio_tests.utils.mode_config import get_mode
   ```

2. **Add mode parameters to queries**:
   ```python
   **mode.to_api_params()  # Adds assistant_mode and deep_search_mode
   ```

3. **Validate mode-specific features**:
   ```python
   if mode.assistant_mode:
       assert 'confidence' in result
   if mode.deep_search_mode:
       assert 'validation' in result or 'metadata' in result
   ```

## Testing

Run updated tests:

```bash
# Run with specific mode
pytest rangerio_tests/ -k "test_rag" --mode=assistant

# Run across all modes
pytest rangerio_tests/ -k "test_rag"

# Run only mode-specific tests
pytest rangerio_tests/integration/test_assistant_mode.py
pytest rangerio_tests/integration/test_deep_search_mode.py
pytest rangerio_tests/integration/test_mode_combinations.py
```

## Validation Checklist

After updating tests:

- [ ] All RAG queries include mode parameters
- [ ] Tests validate mode-specific features
- [ ] Performance tests include all modes
- [ ] Interactive tests include mode metadata
- [ ] Documentation updated with mode usage








