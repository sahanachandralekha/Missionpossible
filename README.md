# ScamCheck 🛡️

**ScamCheck** is an intelligent opportunity-risk assessment system engineered to protect students and early-career jobseekers from predatory schemes, fake internships, illegitimate work-from-home tasks, recruitment fraud, and deceptive scholarship/training offers.

> **Current Status**: **Part 16 Complete — Production Operational Hardening, Observability & Docker Deployment Fully Implemented & Verified**  
> Plain text, Image OCR (RapidOCR), PDF extraction (`pypdf`), Common Analysis Contracts, Entity Extraction, Rule-Based Scam Signal Detection, URL Structure Intelligence, ML/LLM Semantic Intelligence, Domain Verification, calibrated Risk Scoring, Unified Analysis Orchestration, REST API boundary, SQLite persistence, React frontend, centralized configuration, structured JSON logging, correlation request IDs, telemetry metrics, security headers, health/readiness probes, and Docker container deployment are fully implemented and verified with **379 total passing tests** (352 backend pytest + 27 frontend Vitest).

---

## 🔍 Core Conceptual Architecture

ScamCheck does not return naive binary ("SCAM" / "NOT A SCAM") verdicts. Instead, it calculates an **explainable Risk Score (0–100)** with clear, educational evidence points and student guidance.

```
                    USER
                      ↓
              React Frontend
                      ↓
              FastAPI API
                      ↓
        Request / Correlation Middleware
                      ↓
             AnalysisService
                      ↓
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
   Entity/Rules   Semantic      Domain
        │          Analysis     Verification
        └─────────────┼─────────────┘
                      ↓
              RiskScoringEngine
                      ↓
                AnalysisResult
                      ↓
             AnalysisRepository
                      ↓
                  SQLite
                      ↓
              History / API

             ┌───────────────────┐
             │ Observability     │
             │ Logging           │
             │ Timing/Metrics    │
             │ Request IDs       │
             └───────────────────┘

             ┌───────────────────┐
             │ Configuration     │
             │ Environment       │
             │ Runtime Settings  │
             └───────────────────┘
```



---

## 📁 Multi-Format Input Support

Students encounter offers in diverse formats. ScamCheck standardizes all inputs into a single internal contract:

| Input Format | Channels / Artifacts | Processor Status |
| :--- | :--- | :--- |
| **Plain Text** | WhatsApp, Telegram, Emails, LinkedIn messages | **Implemented** (`TextProcessor` & `POST /api/v1/analyze`) |
| **Images / Photos** | Screenshots of chats, flyers, Instagram DMs | **Implemented** (`ImageProcessor` + RapidOCR & `POST /api/v1/analyze/file`) |
| **PDF Documents** | Formal offer letters, brochures, contracts | **Implemented** (`PdfProcessor` + pypdf & `POST /api/v1/analyze/file`) |

### The Normalized `OpportunityInput` Model
All input formats are processed into an immutable common representation:
- `source_type`: `"text"`, `"image"`, or `"pdf"`
- `original_filename`: Uploaded filename (if applicable)
- `mime_type`: Content MIME classification
- `raw_text`: Pre-normalized text, raw OCR dump, or raw assembled PDF text
- `extracted_text`: Sanitized, normalized text string passed to ML & Risk Engine
- `metadata`: Size, word count, page count, OCR confidence, platform hints
- `processing_status`: Current lifecycle state (`"pending"`, `"extracted"`, `"normalized"`, `"failed"`)

---

## 📂 Project Structure

```
Scam-Check/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI entrypoint, health checks, & CORS
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py            # API router aggregator
│   │   │   ├── schemas.py           # AnalyzeTextRequest, AnalysisApiResponse, ApiHealthResponse
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   └── routes.py        # /api/v1/analyze, /api/v1/analyze/file, /api/v1/analyses, /api/v1/health
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       └── analysis.py      # Legacy /api/analyze endpoints (backward-compatible)
│   │   ├── persistence/
│   │   │   ├── __init__.py
│   │   │   ├── database.py          # SQLite database connection & schema manager
│   │   │   ├── models.py            # AnalysisRecord, AnalysisSummaryItem, AnalysisListResponse
│   │   │   └── repository.py        # AnalysisRepository & SQLiteAnalysisRepository
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── opportunity.py      # OpportunityInput Pydantic models & enums
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── input_service.py     # Input intake & processor orchestrator
│   │   │   ├── ocr_service.py       # RapidOCR offline local inference service
│   │   │   └── pdf_service.py       # pypdf local embedded text extraction service
│   │   ├── processors/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Base processor abstract class
│   │   │   ├── text_processor.py    # Text validation & normalization (Implemented)
│   │   │   ├── image_processor.py   # Image validation & RapidOCR (Implemented)
│   │   │   └── pdf_processor.py     # PDF validation & pypdf extraction (Implemented)
│   │   └── analysis/
│   │       ├── __init__.py
│   │       ├── analysis_service.py  # Unified Analysis Orchestrator (Implemented)
│   │       ├── models/              # AnalysisResult, RiskSignal, Evidence, ExtractedEntities
│   │       ├── extraction/          # Deterministic EntityExtractor (Implemented)
│   │       ├── rules/               # RuleBasedSignalEngine (Implemented)
│   │       ├── url/                 # UrlAnalyzer & URL Rules (Implemented)
│   │       ├── ml/                  # SemanticAnalyzer & Provider Abstraction (Implemented)
│   │       ├── domain/              # DomainVerifier & Network Provider (Implemented)
│   │       └── risk/                # RiskScoringEngine & Score Policy (Implemented)
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_foundation.py       # Architecture contract tests (22 tests)
│   │   ├── test_text_pipeline.py    # Text normalization & evidence tests (29 tests)
│   │   ├── test_image_pipeline.py   # Image & OCR tests (23 tests)
│   │   ├── test_pdf_pipeline.py     # PDF extraction & page tests (23 tests)
│   │   ├── test_analysis_contracts.py # Analysis schema tests (20 tests)
│   │   ├── test_entity_extraction.py # Entity extraction tests (30 tests)
│   │   ├── test_rule_detection.py   # Rule detection tests (34 tests)
│   │   ├── test_risk_scoring.py     # Risk scoring tests (21 tests)
│   │   ├── test_analysis_service.py # Analysis orchestration tests (18 tests)
│   │   ├── test_url_analysis.py     # URL & domain structure tests (27 tests)
│   │   ├── test_semantic_analysis.py # ML/LLM semantic tests (25 tests)
│   │   ├── test_domain_verification.py # Domain verification tests (24 tests)
│   │   ├── test_api_v1.py           # Production API boundary tests (25 tests)
│   │   └── test_persistence.py      # Database persistence & history tests (14 tests)
│   ├── requirements.txt             # Core dependencies (FastAPI, Pydantic, RapidOCR, pypdf)
│   └── README.md                    # Backend documentation
├── docs/
│   └── architecture.md              # Complete system design & specification
├── .gitignore

```
└── README.md
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- `pip`

### 2. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 3. Run the Test Suite
```bash
python -m pytest backend/tests/test_foundation.py -v
```

### 4. Start the Development Server
```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
- Interactive API Docs (Swagger): `http://127.0.0.1:8000/docs`
- Health Endpoint: `http://127.0.0.1:8000/health`

---

## 🔒 Privacy & Safety Guarantee
- **Zero Permanent Storage**: Submissions are processed ephemerally in-memory. Documents are never saved to disk or persistent databases.
- **Strict Format Whitelisting**: Executables and unsafe binary payloads are strictly rejected at the API perimeter.
- **No Unnecessary Logging**: PII contained in opportunity documents is not logged to disk.
