# Tri9T AI - CardioTrack CT-200 Document Management System

## Overview

A backend system for the CardioTrack CT-200 Home Blood Pressure Monitor manual that:

- Parses PDF documents into a browsable hierarchical tree
- Tracks document versions with content hashing
- Generates QA test cases using LLM
- Detects stale test cases when documents change

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, Groq LLM, pdfplumber

---

## Features

| Feature | Description |
|---------|-------------|
| ✅ **PDF Parsing** | Extracts headings, subheadings, and hierarchy with parent-child relationships |
| ✅ **Document Versioning** | Maintains multiple versions with change detection |
| ✅ **Browse API** | List sections, get node details, search, and diff across versions |
| ✅ **Selection API** | Create version-pinned selections of document nodes |
| ✅ **LLM Generation** | Generate 3-5 QA test cases from selected sections using Groq |
| ✅ **Staleness Detection** | Identify when generated tests are outdated |
| ✅ **22 Unit Tests** | All passing |

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/saniyakousar12/tri9t-ai-internship.git
cd tri9t-ai-internship
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the root directory:

```env
# LLM Configuration (Get free key from https://console.groq.com)
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here

# Database
DATABASE_URL=sqlite:///./ct200.db

# LLM Settings
LLM_MODEL=llama-3.1-8b-instant
MAX_LLM_RETRIES=3
LLM_TEMPERATURE=0.3

# Versioning
VERSION_MATCH_THRESHOLD=85
```

### 5. Initialize Database

```bash
python create_db.py
```

**Expected Output:**
```
🔄 Creating database tables...
✅ Database created successfully!
📁 Database: sqlite:///./ct200.db
```

### 6. Place PDF Files

Place the CT-200 manual PDFs in the `data/` folder:
- `data/ct200_manual.pdf` (Version 1)
- `data/ct200_manual_v2.pdf` (Version 2)

### 7. Run the Server

```bash
uvicorn app.main:app --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Application startup complete.
```

### 8. Access API Documentation

Open your browser: **http://localhost:8000/docs**

---

## API Endpoints

### Browse API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/sections?version=1` | List top-level sections |
| `GET` | `/api/v1/sections?parent_id=2&version=1` | List children of a section |
| `GET` | `/api/v1/node/{node_id}?version=1` | Get node details with children |
| `GET` | `/api/v1/search?q=pressure&version=1` | Search headings and body text |
| `GET` | `/api/v1/node/{node_id}/diff?from_version=1&to_version=2` | Get diff summary across versions |

### Selection API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/selection` | Create a version-pinned selection |
| `GET` | `/api/v1/selection/{selection_id}` | Get selection details |
| `GET` | `/api/v1/selections` | List all selections |
| `DELETE` | `/api/v1/selection/{selection_id}` | Delete a selection |

### Generation API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/generate` | Generate test cases from a selection |
| `GET` | `/api/v1/generations/selection/{selection_id}?include_staleness=true` | Get generated tests with staleness status |

### Version API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/versions` | List all document versions |
| `GET` | `/api/v1/versions/latest` | Get latest version |
| `GET` | `/api/v1/versions/{version}/stats` | Get version statistics |

---

## Demo Commands

### 1. Ingest Version 1

```bash
curl -X POST "http://localhost:8000/api/v1/ingest?version=1" \
  -F "file=@data/ct200_manual.pdf"
```

**Expected Response:**
```json
{"status":"success","document_id":1,"version":1,"nodes_created":12,"filename":"ct200_manual.pdf"}
```

### 2. Ingest Version 2

```bash
curl -X POST "http://localhost:8000/api/v1/ingest?version=2" \
  -F "file=@data/ct200_manual_v2.pdf"
```

### 3. List Sections

```bash
curl "http://localhost:8000/api/v1/sections?version=1"
```

**Expected Response:**
```json
[
  {"id":1,"heading":"Device Overview","level":1,"child_count":2},
  {"id":2,"heading":"Physical and Electrical Specifications","level":1,"child_count":2},
  {"id":3,"heading":"Device Operation","level":1,"child_count":4}
]
```

### 4. Search

```bash
curl "http://localhost:8000/api/v1/search?q=pressure&version=1"
```

### 5. Create Selection

```bash
curl -X POST "http://localhost:8000/api/v1/selection" \
  -H "Content-Type: application/json" \
  -d '{"name":"Safety Tests","node_ids":[1,2,3],"version":1}'
```

**Expected Response:**
```json
{"id":1,"name":"Safety Tests","version":1,"node_ids":[1,2,3],"created_at":"2026-07-17T13:00:04"}
```

### 6. Generate Test Cases

```bash
curl -X POST "http://localhost:8000/api/v1/generate" \
  -H "Content-Type: application/json" \
  -d '{"selection_id":1,"force":false}'
```

**Expected Response:**
```json
{
  "status":"success",
  "selection_id":1,
  "test_cases":[
    {
      "id":"TC-001",
      "title":"Verify Intended Use Compliance",
      "description":"Verify that the device is used for its intended purpose...",
      "steps":["Step 1...", "Step 2..."],
      "expected_result":"The device is used correctly...",
      "priority":"High"
    }
  ],
  "version_used":1,
  "message":"Generated 3 test cases"
}
```

### 7. Check Staleness

```bash
curl "http://localhost:8000/api/v1/generations/selection/1?include_staleness=true"
```

**Expected Response:**
```json
{
  "selection_id":1,
  "selection_name":"Safety Tests",
  "total_tests":1,
  "tests":[
    {
      "id":1,
      "output":[...],
      "version_at_generation":1,
      "staleness":{
        "is_stale":false,
        "message":"✅ Test cases are up-to-date with current document",
        "version_at_generation":1,
        "current_version":1
      }
    }
  ]
}
```

---

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run with Coverage

```bash
pytest tests/ --cov=app --cov-report=html
```

### Test Results

```
collected 22 items

tests/test_llm.py ...............                                      [ 63%]
tests/test_parser.py ....                                              [ 81%]
tests/test_versioning.py .....                                         [100%]

=========================== 22 passed in 0.25s ===========================
```

---

## Project Structure

```
tri9t-ai-internship/
├── app/
│   ├── api/                 # API endpoints (routes.py, schemas.py)
│   ├── models/              # SQLAlchemy models
│   ├── parser/              # PDF parsing (pdfplumber)
│   ├── versioning/          # Version management (matcher.py, manager.py)
│   ├── llm/                 # LLM integration (generator.py, prompt_templates.py)
│   ├── services/            # Business logic (staleness.py)
│   ├── main.py              # FastAPI app
│   ├── database.py          # Database connection
│   └── config.py            # Configuration settings
├── tests/                   # Unit tests (22 tests)
│   ├── test_llm.py
│   ├── test_parser.py
│   └── test_versioning.py
├── data/                    # PDF files (gitignored)
│   ├── ct200_manual.pdf
│   └── ct200_manual_v2.pdf
├── README.md
├── Approach.md
├── requirements.txt
├── .gitignore
├── .env                     # Environment variables (gitignored)
└── create_db.py             # Database initialization script
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key (required) | None |
| `DATABASE_URL` | SQLite database path | `sqlite:///./ct200.db` |
| `LLM_PROVIDER` | LLM provider | `groq` |
| `LLM_MODEL` | Groq model | `llama-3.1-8b-instant` |
| `VERSION_MATCH_THRESHOLD` | Fuzzy match threshold (0-100) | `85` |
| `MAX_LLM_RETRIES` | Number of retry attempts | `3` |
| `LLM_TEMPERATURE` | LLM temperature (0-1) | `0.3` |

---

## Known Limitations

| Limitation | Description | Production Fix |
|------------|-------------|----------------|
| **Nested Tables** | Extracted as text, structural information lost | Implement recursive table parser |
| **Semantic vs Syntactic Changes** | All content changes flagged the same way | Use semantic embeddings for change detection |
| **False Positives** | Formatting-only edits trigger staleness | Normalize whitespace/case before hashing |
| **Manual Review Required** | All staleness flags require human review | Add confidence scoring and auto-approve safe changes |

---

## Troubleshooting

### ModuleNotFoundError: No module named 'app'

```bash
# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:."  # Mac/Linux
set PYTHONPATH=%PYTHONPATH%;.        # Windows
```

### Database Error

```bash
# Recreate database
rm ct200.db                         # Mac/Linux
del ct200.db                        # Windows
python create_db.py
```

### Port 8000 Already in Use

```bash
# Use a different port
uvicorn app.main:app --reload --port 8001
```

### LLM API Key Not Working

```bash
# Test your Groq API key
curl -X POST "https://api.groq.com/openai/v1/chat/completions" \
  -H "Authorization: Bearer YOUR_GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":"Hello"}]}'
```

---

## Decision Log Summary

### Q1: What's the most likely silent failure?

**Answer:** Version matching. If a section is reorganized but retains a similar title, fuzzy matching can link the wrong nodes.

**Mitigation:** Confidence scores, path change tracking, and manual review for low-confidence matches.

### Q2: Where did you choose simplicity over correctness?

**Answer:** Hash-based staleness detection instead of semantic similarity.

**Production Fix:** Semantic embeddings with prioritization for safety-critical parameter changes.

### Q3: What input did you not handle?

**Answer:** Nested tables within tables.

**System Behavior:** Extracts outer table, flattens inner table to text, logs warning, does not silently drop content.

---

## Author

Saniya Kousar - AI Engineering Internship Candidate

---


## References

- [pdfplumber Documentation](https://github.com/jsvine/pdfplumber)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Groq API Documentation](https://console.groq.com/docs)
- [RapidFuzz Documentation](https://github.com/maxbachmann/RapidFuzz)
