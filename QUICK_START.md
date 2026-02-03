# System GO Quick Start Guide

## For Client Testers

This guide gets you running System GO tests in under 5 minutes.

---

## Prerequisites

1. **RangerIO must be running**
   - Backend: http://127.0.0.1:9000
   - Frontend: http://localhost:5173 (for UI tests)

2. **Python 3.10+** installed

---

## Option 1: One-Command Setup (Recommended)

```bash
# Clone the repo
git clone https://github.com/D2VLabs-adm/systemGO.git
cd systemGO

# Run setup and quick tests
./setup_and_run.sh
```

That's it! The script will:
- Create virtual environment
- Install dependencies
- Run basic tests
- Generate HTML report

---

## Option 2: Manual Setup

```bash
# 1. Clone
git clone https://github.com/D2VLabs-adm/systemGO.git
cd systemGO

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run tests
PYTHONPATH=. pytest rangerio_tests/backend/ -v
```

---

## Test Commands

| What to Test | Command |
|--------------|---------|
| **Quick tests** (default) | `./setup_and_run.sh` |
| **Quality scenarios** (LLM-as-judge) | `./setup_and_run.sh --quality` |
| **UI tests** (requires frontend) | `./setup_and_run.sh --ui` |
| **All tests** | `./setup_and_run.sh --all` |

### Manual pytest commands:

```bash
# Backend API tests
PYTHONPATH=. pytest rangerio_tests/backend/ -v

# Quality scenario tests (response quality validation)
PYTHONPATH=. pytest rangerio_tests/integration/test_user_quality_scenarios.py -v -s

# UI workflow tests
PYTHONPATH=. pytest rangerio_tests/frontend/test_ui_workflows.py -v

# All integration tests
PYTHONPATH=. pytest rangerio_tests/integration/ -v
```

---

## Understanding Test Results

### HTML Reports

After running tests, open the HTML report:

```bash
open reports/html/quick_report.html  # macOS
start reports/html/quick_report.html  # Windows
```

### Quality Scores

Quality scenario tests evaluate responses on:
- **Accuracy** (1-10): Is the answer factually correct?
- **Relevance** (1-10): Does it answer the question?

Minimum passing scores: 6.0 for both.

---

## Troubleshooting

### "Backend not running"

Start RangerIO:
```bash
cd /path/to/rangerio-backend
python -m uvicorn api.server:app --port 9000
```

### "Import errors"

Make sure you're in the systemGO directory and PYTHONPATH is set:
```bash
cd systemGO
export PYTHONPATH=$(pwd)
```

### "Playwright not found"

For UI tests, install Playwright:
```bash
pip install playwright
playwright install chromium
```

---

## What Tests Validate

| Test Category | What It Checks |
|---------------|----------------|
| **Backend API** | Endpoints respond correctly |
| **Data Ingestion** | Files import successfully |
| **RAG Quality** | Search retrieves relevant content |
| **Response Quality** | LLM answers are accurate |
| **UI Workflows** | User can navigate and interact |

---

## Need Help?

- Check the full [README.md](README.md)
- See test documentation in [TESTING_EXECUTION_PLAN.md](TESTING_EXECUTION_PLAN.md)
- Report issues to the RangerIO team
