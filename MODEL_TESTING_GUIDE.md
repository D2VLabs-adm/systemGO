# Model Configuration for Testing

## 🎯 Test Models - RangerIO Available Models

Based on your actual RangerIO installation at `~/onprem_data/models/`, the following models are configured for testing:

### Primary Test Models

#### 1. **Qwen 4B (Q4_K_M)** - PRIMARY
- **Model ID**: `qwen3-4b-q4-k-m`
- **File**: `qwen3-4b-q4_k_m.gguf` (2.3GB)
- **Size**: 4B parameters
- **Context**: 4096 tokens
- **Use Case**: Primary model for all tests
- **Speed**: Fast ⚡
- **Quality**: Excellent 🌟

#### 2. **Llama 3.2 3B Instruct (Q4_K_M)** - SECONDARY
- **Model ID**: `llama-3-2-3b-instruct-q4-k-m`
- **File**: `llama-3.2-3b-instruct-q4_k_m.gguf` (1.9GB)
- **Size**: 3B parameters
- **Context**: 32768 tokens (8x larger!)
- **Use Case**: Comparison testing, long context tests
- **Speed**: Very Fast ⚡⚡
- **Quality**: Very Good 🌟

### Additional Available Models

#### 3. **Phi-3 Mini (Q4_K_M)** - OPTIONAL
- **Model ID**: `phi3-mini-q4`
- **File**: `phi3-mini-q4.gguf` (2.2GB)
- **Size**: 3.8B parameters
- **Context**: 4096 tokens
- **Use Case**: Optional comparison, Microsoft model

#### 4. **Qwen2.5 Coder 1.5B (Q4_K_M)** - SPECIALIZED
- **Model ID**: `qwen2-5-coder-1-5b-instruct-q4`
- **File**: `qwen2.5-coder-1.5b-instruct-q4_k_m.gguf` (1.0GB)
- **Size**: 1.5B parameters
- **Context**: 32768 tokens
- **Use Case**: Code-specific tests

#### 5. **Ministral 3B (Q4_K_M)** - ALTERNATIVE
- **Model ID**: `ministral-3-3b-instruct`
- **File**: `Ministral-3-3B-Instruct-2512-Q4_K_M.gguf` (2.0GB)
- **Size**: 3B parameters
- **Context**: 4096 tokens
- **Use Case**: Alternative comparison

---

## 🚀 Running Tests with Specific Models

### Quick Start - Default Model (Qwen 4B)

```bash
cd "/Users/vadim/.cursor/worktrees/Validator/SYSTEM GO"
source venv/bin/activate

# Tests will use Qwen 4B by default
PYTHONPATH=. pytest rangerio_tests/backend/
```

### Test with Specific Model

```bash
# Set model via environment variable
export TEST_MODEL_NAME="llama-3-2-3b-instruct-q4-k-m"
PYTHONPATH=. pytest rangerio_tests/backend/

# Or inline
TEST_MODEL_NAME="qwen3-4b-q4-k-m" PYTHONPATH=. pytest rangerio_tests/
```

### Compare Two Models

```bash
# Compare Qwen 4B vs Llama 3.2 3B
python run_comparative_tests.py \
  --models qwen3-4b-q4-k-m llama-3-2-3b-instruct-q4-k-m \
  --model-configs model_configs.json \
  --compare
```

### Compare All Available Models

```bash
# Full comparison of all 5 models
python run_comparative_tests.py \
  --models qwen3-4b-q4-k-m llama-3-2-3b-instruct-q4-k-m phi3-mini-q4 qwen2-5-coder-1-5b-instruct-q4 ministral-3-3b-instruct \
  --model-configs model_configs.json \
  --compare
```

---

## 📊 Expected Performance

Based on model sizes and quantization:

| Model | Size | Context | Speed | Quality | Best For |
|-------|------|---------|-------|---------|----------|
| **Qwen 4B** | 2.3GB | 4K | ⚡⚡ | 🌟🌟🌟🌟 | General testing |
| **Llama 3.2 3B** | 1.9GB | 32K | ⚡⚡⚡ | 🌟🌟🌟 | Long context |
| Phi-3 Mini | 2.2GB | 4K | ⚡⚡ | 🌟🌟🌟 | Comparison |
| Qwen2.5 Coder | 1.0GB | 32K | ⚡⚡⚡⚡ | 🌟🌟 | Code tasks |
| Ministral 3B | 2.0GB | 4K | ⚡⚡⚡ | 🌟🌟🌟 | Alternative |

### Performance Targets

#### Qwen 4B (Primary)
- **RAG Query**: < 5s
- **Import 50K rows**: < 60s
- **Memory**: < 2GB
- **Faithfulness**: ≥ 0.70
- **Relevancy**: ≥ 0.70

#### Llama 3.2 3B (Secondary)
- **RAG Query**: < 4s (faster, smaller model)
- **Import 50K rows**: < 60s
- **Memory**: < 1.5GB
- **Faithfulness**: ≥ 0.65
- **Relevancy**: ≥ 0.65

---

## 🔧 Configuration Files Updated

All configuration files now point to your actual models:

### 1. `model_configs.json`
✅ Updated with all 5 available models  
✅ Correct file paths (`/Users/vadim/onprem_data/models/`)  
✅ Proper context windows and settings

### 2. `rangerio_tests/config.py`
✅ DEFAULT_MODEL = "qwen3-4b-q4-k-m"  
✅ SECONDARY_MODEL = "llama-3-2-3b-instruct-q4-k-m"

### 3. `rangerio_tests/utils/rag_evaluator.py`
✅ RangerIOLLM defaults to "qwen3-4b-q4-k-m"

---

## 📝 Test Scenarios by Model

### Scenario 1: Quick Validation (Qwen 4B only)
```bash
# Fast validation with primary model
TEST_MODEL_NAME="qwen3-4b-q4-k-m" PYTHONPATH=. pytest rangerio_tests/backend/ -v
```
**Time**: ~5-10 minutes  
**Purpose**: Quick sanity check

### Scenario 2: Dual Model Comparison (Qwen 4B + Llama 3.2 3B)
```bash
# Compare the two main test models
python run_comparative_tests.py \
  --models qwen3-4b-q4-k-m llama-3-2-3b-instruct-q4-k-m \
  --compare
```
**Time**: ~20-30 minutes  
**Purpose**: Performance comparison, quality assessment

### Scenario 3: Full Model Sweep (All 5 models)
```bash
# Test all available models
python run_comparative_tests.py \
  --models qwen3-4b-q4-k-m llama-3-2-3b-instruct-q4-k-m phi3-mini-q4 qwen2-5-coder-1-5b-instruct-q4 ministral-3-3b-instruct \
  --compare
```
**Time**: ~60-90 minutes  
**Purpose**: Comprehensive model evaluation

### Scenario 4: Long Context Testing (Llama 3.2 3B)
```bash
# Use Llama 3.2 for 32K context window tests
TEST_MODEL_NAME="llama-3-2-3b-instruct-q4-k-m" PYTHONPATH=. pytest rangerio_tests/integration/test_rag_accuracy.py -v
```
**Time**: ~10-15 minutes  
**Purpose**: Large context testing

---

## 🎯 Recommended Test Strategy

### Phase 1: Initial Validation (Day 1)
✅ Run with Qwen 4B (primary model)  
✅ Verify all backend tests pass  
✅ Verify frontend E2E tests work  
✅ Check performance baselines

### Phase 2: Comparison (Day 2)
✅ Run with Llama 3.2 3B  
✅ Compare performance metrics  
✅ Compare RAG accuracy scores  
✅ Generate comparison report

### Phase 3: Full Sweep (Day 3)
✅ Test all 5 models  
✅ Generate comprehensive report  
✅ Identify best model for each task  
✅ Document findings

---

## 📈 Expected Results

### RAG Accuracy (ragas scores)

| Model | Faithfulness | Relevancy | Context Precision |
|-------|-------------|-----------|-------------------|
| Qwen 4B | 0.75-0.85 | 0.70-0.80 | 0.65-0.75 |
| Llama 3.2 3B | 0.70-0.80 | 0.68-0.78 | 0.62-0.72 |
| Phi-3 Mini | 0.72-0.82 | 0.69-0.79 | 0.64-0.74 |
| Qwen2.5 Coder | 0.65-0.75 | 0.60-0.70 | 0.55-0.65 |
| Ministral 3B | 0.70-0.80 | 0.67-0.77 | 0.62-0.72 |

*Note: Actual scores will vary based on test data and prompts*

### Performance Metrics

| Metric | Qwen 4B | Llama 3.2 3B |
|--------|---------|--------------|
| Query Time | 3-5s | 2-4s |
| Memory Usage | 1.5-2GB | 1-1.5GB |
| Tokens/sec | 15-25 | 20-30 |

---

## ✅ Verification

Run this to verify model configuration:

```bash
cd "/Users/vadim/.cursor/worktrees/Validator/SYSTEM GO"
source venv/bin/activate

# Check models are accessible
ls -lh /Users/vadim/onprem_data/models/

# Verify configuration
cat model_configs.json | python -m json.tool

# Test import
PYTHONPATH=. python -c "from rangerio_tests.config import config; print(f'Default Model: {config.DEFAULT_MODEL}')"
```

---

**All model configurations are now set to use your actual RangerIO models! 🎉**

Primary testing will use **Qwen 4B** with **Llama 3.2 3B** as comparison.








