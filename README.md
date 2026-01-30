# SYSTEM GO - RangerIO Automated Testing Suite

**Comprehensive automated testing framework for RangerIO with 95%+ automation coverage**

**⚠️ IMPORTANT: This includes a complete Investigation & Repair workflow - not just pass/fail reporting!**

## 📥 Installation (Client Setup)

### 1. Clone the Repository

```bash
git clone https://github.com/D2VLabs-adm/systemGO.git
cd systemGO
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt

# For E2E tests (optional)
playwright install chromium
```

### 4. Download Kaggle Datasets (Optional)

For extended test coverage with real-world datasets:

```bash
# Set up Kaggle API key first: https://www.kaggle.com/settings/account
# Save to ~/.kaggle/kaggle.json

python rangerio_tests/utils/kaggle_dataset_downloader.py
```

---

## 📋 Overview

SYSTEM GO is a production-grade testing suite that validates RangerIO's:
- ✅ Backend API & data processing
- ✅ Frontend UI/UX workflows
- ✅ RAG accuracy & prompt optimization
- ✅ Performance & memory management
- ✅ Load testing & concurrency
- ✅ Visual regression
- ✅ Interactive validation with golden dataset generation

### 🎯 Testing Philosophy

> **"When tests fail, we investigate, fix, and verify - not just report!"**

This is an **iterative improvement workflow**:
```
Run → Fail → Investigate → Fix → Verify → Document → Repeat until success ✅
```

See **`TESTING_EXECUTION_PLAN.md`** for the complete approach.

## 🚀 Quick Start

### 1. Prerequisites

Ensure RangerIO is running:
- **Backend**: http://127.0.0.1:9000
- **Frontend**: http://localhost:5173

### 2. Activate Environment

```bash
cd systemGO
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Run All Tests

```bash
# Run complete test suite
PYTHONPATH=. pytest rangerio_tests/

# Run with HTML report
PYTHONPATH=. pytest rangerio_tests/ --html=reports/html/report.html
```

### 4. Run Specific Test Categories

```bash
# Backend tests only
PYTHONPATH=. pytest rangerio_tests/backend/

# Frontend E2E tests only
PYTHONPATH=. pytest rangerio_tests/frontend/

# Integration tests (RAG quality)
PYTHONPATH=. pytest rangerio_tests/ -m integration

# Mode testing (Assistant & Deep Search)
PYTHONPATH=. pytest rangerio_tests/integration/test_assistant_mode.py
PYTHONPATH=. pytest rangerio_tests/integration/test_deep_search_mode.py
PYTHONPATH=. pytest rangerio_tests/integration/test_mode_combinations.py

# Skip slow tests
PYTHONPATH=. pytest rangerio_tests/ -m "not slow"
```

### 5. Run Load Tests

```bash
# Locust load testing (100 concurrent users)
locust -f rangerio_tests/load/locustfile.py \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --html reports/html/load_test.html
```

### 6. Run Model Comparison

```bash
# Compare Qwen 4B vs Llama 3.2 3B (your primary test models)
python run_comparative_tests.py \
  --models qwen3-4b-q4-k-m llama-3-2-3b-instruct-q4-k-m \
  --model-configs model_configs.json \
  --compare

# Or compare all 5 available models
python run_comparative_tests.py \
  --models qwen3-4b-q4-k-m llama-3-2-3b-instruct-q4-k-m phi3-mini-q4 qwen2-5-coder-1-5b-instruct-q4 ministral-3-3b-instruct \
  --compare
```

## 📊 Test Coverage

| Category | Files | Coverage |
|----------|-------|----------|
| Backend API | `backend/` | 100% |
| **Mode Testing** | **`integration/test_*_mode.py`** | **NEW! 4 modes** |
| Frontend E2E | `frontend/` | Key workflows |
| RAG Evaluation | `integration/test_rag_*.py` | ragas + custom |
| Performance | `performance/` | All modes |
| Load Testing | `load/` | API endpoints |
| Interactive | `integration/test_interactive_*.py` | Human-in-loop |
| Data Ingestion | `backend/test_data_ingestion.py` | All file types |
| Data Quality & PII | `backend/test_data_ingestion.py` | 95%+ detection |
| PandasAI Integration | `backend/test_data_ingestion.py` | Core features |
| Memory Management | `backend/test_data_ingestion.py` | < 2GB threshold |
| Frontend E2E | `frontend/` | Major workflows |
| Visual Regression | `frontend/` | Screenshot-based |
| Load Testing | `load/locustfile.py` | 100 concurrent users |
| RAG Evaluation | `utils/rag_evaluator.py` | ragas + local LLM |

## 🎯 Interactive Validation

For subjective quality assessments:

```bash
# Run with interactive validation markers
PYTHONPATH=. pytest rangerio_tests/ -m interactive
```

During execution, you'll be shown:
- 📋 Formatted RAG answers with ragas scores
- 📊 Chart images for visual inspection
- ⚖️ Side-by-side prompt comparisons

Your feedback is saved to `fixtures/golden_outputs/` for future automated testing.

## 📁 Directory Structure

```
SYSTEM GO/
├── rangerio_tests/          # Test package
│   ├── backend/             # Backend API tests
│   ├── frontend/            # Frontend E2E tests
│   ├── integration/         # RAG quality tests
│   ├── load/                # Load testing
│   └── utils/               # Test utilities
├── fixtures/                # Test data
│   ├── test_data/           # Generated test files
│   └── golden_outputs/      # Validated answers
├── reports/                 # Test outputs
│   ├── html/                # HTML test reports
│   ├── screenshots/         # Visual regression
│   └── comparisons/         # Model comparisons
├── requirements.txt         # Python dependencies
├── pytest.ini               # Pytest configuration
├── model_configs.json       # Model configurations
└── run_comparative_tests.py # Model comparison runner
```

## 🔧 Configuration

Edit `rangerio_tests/config.py` to customize:
- Backend/Frontend URLs
- Performance thresholds
- Test file sizes
- Interactive validation settings

## 📈 Performance Targets

| Operation | Target Time |
|-----------|-------------|
| RAG query | < 5s |
| File import (50K rows) | < 60s |
| Data profile | < 10s |
| Chart generation | < 15s |
| Memory usage | < 2GB |

## 🧪 Test Data

Test fixtures are auto-generated in `fixtures/test_data/`:
- **CSV**: 4 files (100 - 50,000 rows)
- **Excel**: Multi-sheet workbook
- **JSON**: 200 nested records
- **Parquet**: 50,000 rows
- **PDF/DOCX**: Placeholder files (add real documents)

Regenerate fixtures:
```bash
PYTHONPATH=. python rangerio_tests/utils/data_generators.py
```

## 🎨 Visual Regression

Screenshots are captured in `reports/screenshots/` for:
- Main page
- Import wizard steps
- Prepare wizard states
- RAGs management
- Prompts management

Use Playwright's `toHaveScreenshot()` for pixel-perfect comparisons.

## 🎛️ Mode Testing (NEW!)

**CRITICAL**: Previous tests ran in Basic mode only. Now testing all 4 modes!

### Understanding Modes

RangerIO has 4 query modes with different features and performance:

| Mode | Features | Speed | Use Case |
|------|----------|-------|----------|
| **Basic** | None | Fast (1-3s) | Simple queries |
| **Assistant** | Smart features | Medium (2-5s) | User-facing |
| **Deep Search** | Thorough analysis | Slow (5-15s) | Complex analysis |
| **Both** | All features | Slowest (5-20s) | Maximum accuracy |

### Run Mode Tests

```bash
# Test all modes
PYTHONPATH=. pytest rangerio_tests/integration/test_mode_combinations.py -v

# Test Assistant features (confidence, clarification, constraints)
PYTHONPATH=. pytest rangerio_tests/integration/test_assistant_mode.py -v

# Test Deep Search features (compound queries, validation)
PYTHONPATH=. pytest rangerio_tests/integration/test_deep_search_mode.py -v

# Performance benchmarks for all modes
PYTHONPATH=. pytest rangerio_tests/performance/test_mode_performance.py -v

# Interactive mode comparison (generates HTML report)
PYTHONPATH=. pytest rangerio_tests/integration/test_interactive_modes.py -v -s
```

### Mode Testing Documentation

- **[MODE_TESTING_GUIDE.md](MODE_TESTING_GUIDE.md)** - Complete guide
- **[UPDATING_TESTS_FOR_MODES.md](UPDATING_TESTS_FOR_MODES.md)** - How to add modes to existing tests

### Quick Mode Usage Example

```python
from rangerio_tests.utils.mode_config import get_mode

# Use Assistant mode in test
mode = get_mode('assistant')
response = api_client.post("/rag/query", json={
    "prompt": "How many records?",
    "project_id": rag_id,
    **mode.to_api_params()  # Adds assistant_mode=True
})

# Validate Assistant features
assert 'confidence' in response.json()
```

## 📊 Reports

Test reports are generated in `reports/`:
- **HTML**: `reports/html/report.html` (pytest-html)
- **Screenshots**: `reports/screenshots/` (Playwright)
- **Videos**: `reports/videos/` (test failures)
- **Comparisons**: `reports/comparisons/` (model benchmarks)

## 🔄 CI/CD Integration

Add to your CI pipeline:

```yaml
# Example GitHub Actions
- name: Run Tests
  run: |
    cd "/path/to/SYSTEM GO"
    source venv/bin/activate
    PYTHONPATH=. pytest rangerio_tests/ --html=reports/html/ci_report.html
    
- name: Upload Reports
  uses: actions/upload-artifact@v2
  with:
    name: test-reports
    path: reports/
```

## 🐛 Troubleshooting & Test Failures

### ⚠️ IMPORTANT: Investigation & Repair is Part of the Process

**When tests fail, we don't just report them - we investigate and fix them!**

This is an **iterative workflow**, not a one-shot validation:

```
Run → Fail → Investigate → Fix → Verify → Repeat until all tests pass ✅
```

### When Tests Fail

**SYSTEM GO includes a complete investigation and repair workflow that WILL BE APPLIED!**

See **`TEST_FAILURE_GUIDE.md`** for comprehensive guidance on:
- 🔍 Investigating root causes
- 🛠️ Repairing failures
- ✅ Verifying fixes
- 📊 Common scenarios & solutions

### Quick Debugging

```bash
# Run failing test with verbose output
PYTHONPATH=. pytest path/to/test.py::test_name -vv -s

# Check if backend is running
curl http://127.0.0.1:9000/health

# Check if frontend is running
curl http://localhost:5173

# View test failure screenshots
open reports/screenshots/

# Run with different model
TEST_MODEL_NAME="qwen3-4b-q4-k-m" PYTHONPATH=. pytest rangerio_tests/ -v
```

### Common Issues

**Backend not available:**
```bash
# Navigate to your RangerIO installation directory
cd /path/to/rangerio-backend
python api/server.py
# Or use: python -m uvicorn api.server:app --port 9000
```

**Frontend not loading:**
```bash
cd /path/to/rangerio-backend/frontend
npm run dev
```

**Import errors:**
```bash
# Set PYTHONPATH to your systemGO directory
export PYTHONPATH=$(pwd)
# Or explicitly: export PYTHONPATH=/path/to/systemGO
```

**Playwright issues:**
```bash
playwright install chromium --force
```

## 📚 Additional Resources

- **GitHub Repo**: https://github.com/D2VLabs-adm/systemGO
- **Backend API Docs**: http://127.0.0.1:9000/docs (when RangerIO is running)
- **Test Plan**: See `TESTING_EXECUTION_PLAN.md` for detailed implementation

## 🎉 Success Metrics

- ✅ 95%+ test coverage
- ✅ All tests < 30 minutes
- ✅ RAG faithfulness ≥ 0.70
- ✅ PII detection ≥ 95%
- ✅ Zero memory leaks
- ✅ Performance within targets

## 📞 Support

For issues or questions, refer to the main RangerIO documentation.

---

**SYSTEM GO** - Automated Testing Excellence for RangerIO

