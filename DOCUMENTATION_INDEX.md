# SYSTEM GO - Documentation Index

**All guides for comprehensive testing with investigation & repair workflow**

---

## 🚀 Start Here

### 1. **README.md** - Main Entry Point
- Overview of SYSTEM GO
- Quick start guide
- Installation & setup
- Basic usage examples
- Troubleshooting section

### 2. **QUICK_REFERENCE.txt** - Fast Commands
- One-page quick reference
- Fast debugging commands
- Common fixes
- Workflow summary

---

## 📋 Planning & Process

### 3. **TESTING_EXECUTION_PLAN.md** - The Complete Process
- Full commitment to investigation & repair
- Phase-by-phase breakdown
- Timeline expectations
- Deliverables
- Example workflows

### 4. **WORKFLOW_CONFIRMATION.md** - Detailed Confirmation
- What the workflow means
- Step-by-step process
- Expected timeline (5-8 hours)
- All deliverables listed
- Example failure → fix → verify cycle

### 5. **INVESTIGATION_WORKFLOW.md** - Quick Process Guide
- Investigation checklist
- Common fixes
- Fast iteration commands
- Philosophy & approach

---

## 🔧 Investigation & Repair

### 6. **TEST_FAILURE_GUIDE.md** - Complete Troubleshooting (★ PRIMARY GUIDE)
- **8 comprehensive sections**
- Automatic failure detection
- Complete investigation workflow
- **6 common failure scenarios** with fixes:
  1. Backend not available
  2. Model not found
  3. Performance threshold exceeded
  4. RAG accuracy too low
  5. Frontend E2E failures
  6. PII detection issues
- Debugging tools reference
- Fix-verify cycle
- Success criteria

---

## 🤖 Model Testing

### 7. **MODEL_TESTING_GUIDE.md** - Model Configurations & Testing
- All 5 available models detailed
- Primary: Qwen 4B, Secondary: Llama 3.2 3B
- Performance expectations
- Testing scenarios
- Model comparison strategies
- Expected RAG accuracy scores

### 8. **model_configs.json** - Model Configuration File
- Qwen 4B (primary test model)
- Llama 3.2 3B (secondary test model)
- Phi-3 Mini, Qwen2.5 Coder, Ministral (additional)
- Correct file paths
- Context windows
- Backend settings

---

## 📊 Implementation Details

### 9. **IMPLEMENTATION_SUMMARY.md** - What Was Built
- All phases completed
- Key features
- Test categories
- Investigation & repair workflow section
- How to run
- Success criteria

### 10. **RAGAS_AND_INTERACTIVE_VALIDATION.md** - ragas Integration & Interactive Testing
- ragas 0.4.x integration with local LLMs
- Custom metrics fallback (always works)
- InteractiveValidator framework
- 5 interactive test scenarios
- Hallucination detection
- Chart validation
- Prompt comparison
- Golden dataset builder
- Complete implementation details

### 11. **PACKAGE_VERSIONS.md** - Tool Versions
- Python packages (latest versions)
- Playwright browsers (latest)
- Before/after version tracking

### 12. **REALISTIC_USECASE_IMPLEMENTATION.md** - Real-World Use Case Testing (★ NEW)
- **Sales Data Analysis Use Case** (5-year data, 4 complex tests)
- **Auditor Multi-Document Use Case** (mixed files, 3 cross-document tests)
- Kaggle dataset integration with quality validation
- Refinement tracking with issue checklists
- Export quality verification
- Complete implementation guide
- Run command: `./run_realistic_usecase_tests.sh`

---

## 📂 Test Files

### Backend Tests
- `rangerio_tests/backend/test_data_ingestion.py`
  - Import tests (small, large, bulk)
  - PII detection
  - Data quality
  - PandasAI queries
  - Memory management

### Frontend Tests
- `rangerio_tests/frontend/test_e2e_prepare_wizard.py`
  - Prepare Wizard UI tests
  - Chat panel
  - Enum normalization
  - Preview/review toggle
  - Download export
  - Chart rendering

### Integration Tests
- `rangerio_tests/integration/test_rag_accuracy.py`
  - RAG evaluation with ragas
  - Faithfulness, relevancy, precision
  - Multi-query testing
- `rangerio_tests/integration/test_interactive_rag.py`
  - Interactive RAG answer validation
  - Hallucination detection tests
  - Chart validation tests
  - Prompt comparison tests
  - Golden dataset builder
- `rangerio_tests/integration/test_sales_analysis_usecase.py` **[NEW - REALISTIC]**
  - 5-year sales data analysis
  - Regional profit margin decline
  - Sales team performance segmentation
  - Reseller profitability correlation
  - Data cleanup and export validation
- `rangerio_tests/integration/test_auditor_usecase.py` **[NEW - REALISTIC]**
  - Cross-document reasoning (Excel, PDF, DOCX, TXT)
  - CapEx discrepancy detection
  - Approval authority validation
  - Revenue reconciliation

### Load Tests
- `rangerio_tests/load/locustfile.py`
  - API load testing
  - Concurrent users
  - Performance under load

---

## 🛠️ Utilities

### Test Data Generation
- `rangerio_tests/utils/data_generators.py`
  - CSV, Excel, JSON, Parquet generation
  - PII data generation
  - Messy category data
  - Large datasets (50K rows)
- `rangerio_tests/utils/kaggle_dataset_downloader.py` **[NEW]**
  - Download real datasets from Kaggle (with validation)
  - 5-year sales dataset generator (10K transactions, multi-tab Excel)
  - Auditor scenario file generator (Excel, PDF, DOCX, TXT with cross-refs)
  - Quality validation (min rows, date range, columns, value ranges)
  - Graceful fallback to synthetic data

### RAG Evaluation
- `rangerio_tests/utils/rag_evaluator.py`
  - RangerIOLLM wrapper for ragas 0.4.x
  - Custom metrics fallback (faithfulness, relevancy, precision)
  - Local LLM integration
  - Automatic scoring with backend health check

### Interactive Validation
- `rangerio_tests/utils/interactive_validator.py`
  - Human-in-the-loop validation framework
  - Display RAG answers, charts, prompt comparisons
  - Auto-validation mode with heuristics
  - Golden dataset saving

### Benchmark Persistence **[NEW]**
- `rangerio_tests/utils/benchmark_db.py`
  - Saves benchmark results to JSON database
  - Tracks performance trends over time
  - Enables model comparison
  - Generates comparison reports

---

## 🎯 Configuration Files

### Test Configuration
- `rangerio_tests/config.py`
  - RangerIO workspace path
  - Backend/frontend URLs
  - Test data paths
  - Performance thresholds
  - DEFAULT_MODEL: qwen3-4b-q4-k-m
  - SECONDARY_MODEL: llama-3-2-3b-instruct-q4-k-m

### Pytest Configuration
- `pytest.ini`
  - Test discovery
  - Markers (unit, integration, e2e, load, interactive)
  - HTML reporting

### Dependencies
- `requirements.txt`
  - All Python packages (latest versions)
  - pytest, playwright, locust, ragas, etc.

---

## 📈 Running Tests

### Quick Commands

```bash
# Full suite
PYTHONPATH=. pytest rangerio_tests/ -v

# Backend only
PYTHONPATH=. pytest rangerio_tests/backend/ -v

# Frontend only
PYTHONPATH=. pytest rangerio_tests/frontend/ -v

# Single test with debug
PYTHONPATH=. pytest path/to/test.py::test_name -vv -s

# Model comparison
python run_comparative_tests.py \
  --models qwen3-4b-q4-k-m llama-3-2-3b-instruct-q4-k-m \
  --compare
```

---

## 🎯 The Workflow (Confirmed)

**When you run tests, this ENTIRE process applies:**

1. ✅ **Run** - Execute full test suite
2. 🔍 **Investigate** - Root cause analysis for every failure
3. 🛠️ **Fix** - Apply appropriate fixes (code, config, data)
4. ✅ **Verify** - Re-run to confirm fixes work
5. 📊 **Document** - Update TEST_FINDINGS.md
6. 🔄 **Iterate** - Repeat until 95-100% pass rate
7. 📈 **Report** - Generate comprehensive final report

---

## 📚 Documentation Summary

| Document | Purpose | Size | Use When |
|----------|---------|------|----------|
| **README.md** | Getting started | Medium | First time setup |
| **QUICK_REFERENCE.txt** | Fast commands | 1 page | Daily use |
| **TEST_FAILURE_GUIDE.md** | Troubleshooting | Large | Test fails |
| **RAGAS_AND_INTERACTIVE_VALIDATION.md** | ragas & Interactive Tests | Large | RAG validation, hallucination detection |
| **BENCHMARK_SYSTEM.md** | Benchmark & Comparison | Large | Track performance, compare models |
| **TESTING_EXECUTION_PLAN.md** | Process commitment | Large | Understanding workflow |
| **WORKFLOW_CONFIRMATION.md** | Detailed confirmation | Large | Need full clarity |
| **INVESTIGATION_WORKFLOW.md** | Quick process | Small | Fast reference |
| **MODEL_TESTING_GUIDE.md** | Model configurations | Large | Model setup/comparison |
| **IMPLEMENTATION_SUMMARY.md** | What was built | Medium | Overview |
| **PACKAGE_VERSIONS.md** | Tool versions | Small | Version tracking |

---

## 🎯 Where to Start

### For First-Time Use
1. Read **README.md** - Setup and basic usage
2. Check **MODEL_TESTING_GUIDE.md** - Verify model configuration
3. Review **QUICK_REFERENCE.txt** - Bookmark for fast access

### When Tests Fail
1. Check **QUICK_REFERENCE.txt** - Fast debugging
2. Consult **TEST_FAILURE_GUIDE.md** - Detailed investigation
3. Follow **INVESTIGATION_WORKFLOW.md** - Process checklist

### For Understanding the Process
1. Read **TESTING_EXECUTION_PLAN.md** - Complete commitment
2. Review **WORKFLOW_CONFIRMATION.md** - Detailed examples
3. Check **IMPLEMENTATION_SUMMARY.md** - What was built

---

## ✅ All Documentation Ready!

- 📘 **11 comprehensive guides** created (added ragas & interactive validation guide)
- 🔧 **Complete investigation & repair workflow** documented
- 🤖 **Model configurations** for Qwen 4B & Llama 3.2 3B
- 📊 **Test suite** ready with 50+ tests (including 5 interactive tests)
- 🚀 **All tools** installed and verified (latest versions)
- 🎯 **ragas 0.4.x integration** with custom metrics fallback
- 🧪 **Interactive validation** framework for hallucination detection

**SYSTEM GO is ready for comprehensive testing with full investigation & repair! 🎉**

---

## 🚀 Next Step

```bash
cd "/Users/vadim/.cursor/worktrees/Validator/SYSTEM GO"
source venv/bin/activate
PYTHONPATH=. pytest rangerio_tests/ -v
```

Then the investigation & repair workflow begins! 🔧

