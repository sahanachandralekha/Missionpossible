# ScamCheck 🛡️

**ScamCheck** is an intelligent opportunity-risk assessment system engineered to protect students and early-career jobseekers from predatory schemes, fake internships, illegitimate work-from-home tasks, recruitment fraud, and deceptive scholarship/training offers.

> **Current Status**: **Part 7 Complete — Rule-Based Scam Signal Detection Engine Fully Implemented & Tested**  
> Plain text, Image OCR (RapidOCR), PDF extraction (`pypdf`), Common Analysis Contracts, deterministic Entity Extraction, and deterministic Rule-Based Scam Signal Detection are fully implemented and verified with **181 passing tests**. The rule engine detects suspicious indicators (upfront fees, pressure urgency, guarantees, no-interview hiring, unrealistic income, authority claims, informal contact channels) with traceable evidence while keeping `score_contribution = 0.0` (risk scoring engine explicitly reserved for upcoming phases).

---

## 🔍 Core Conceptual Architecture

ScamCheck does not return naive binary ("SCAM" / "NOT A SCAM") verdicts. Instead, it is designed to calculate an **explainable Risk Score (0–100)** with clear, educational evidence points.

```
USER
  ↓
TEXT / IMAGE / PDF
  ↓
INPUT PROCESSING (Validation & Normalization / Local RapidOCR / pypdf)
  ↓
NORMALIZED OPPORTUNITY (OpportunityInput)
  ↓
ENTITY EXTRACTION (Factual extraction of Orgs, Contacts, Payments, URLs)
  ↓
RULE-BASED SCAM SIGNAL DETECTION (Upfront fees, Urgency, Guarantees, Informal channels)
  ↓
ML + OTHER ANALYSIS (NLP Classifier, Heuristics, Pattern Cues)
  ↓
RISK ENGINE (Calibrated Multi-Signal Aggregation)
  ↓
RISK SCORE 0–100
  ↓
EXPLANATION + EVIDENCE
```

---

## 📁 Multi-Format Input Support

Students encounter offers in diverse formats. ScamCheck standardizes all inputs into a single internal contract:

| Input Format | Channels / Artifacts | Processor Status |
| :--- | :--- | :--- |
| **Plain Text** | WhatsApp, Telegram, Emails, LinkedIn messages | **Implemented** (`TextProcessor`) |
| **Images / Photos** | Screenshots of chats, flyers, Instagram DMs | **Implemented** (`ImageProcessor` + `OCRService` RapidOCR) |
| **PDF Documents** | Formal offer letters, brochures, contracts | **Implemented** (`PdfProcessor` + `PDFService` pypdf) |

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
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       └── analysis.py      # /api/analyze/text and /api/analyze/file endpoints
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
│   │       ├── models/              # AnalysisResult, RiskSignal, Evidence, ExtractedEntities
│   │       ├── extraction/          # Deterministic EntityExtractor (Implemented)
│   │       ├── rules/               # RuleBasedSignalEngine (Implemented)
│   │       ├── ml/
│   │       │   └── __init__.py      # Location for future pretrained ML model
│   │       └── risk/
│   │           └── __init__.py      # Location for future 0-100 risk engine
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_foundation.py       # Architecture contract tests (22 tests)
│   │   ├── test_text_pipeline.py    # Text normalization & evidence tests (29 tests)
│   │   ├── test_image_pipeline.py   # Image & OCR tests (23 tests)
│   │   ├── test_pdf_pipeline.py     # PDF extraction & page tests (23 tests)
│   │   ├── test_analysis_contracts.py # Analysis schema tests (20 tests)
│   │   ├── test_entity_extraction.py # Entity extraction tests (30 tests)
│   │   └── test_rule_detection.py   # Rule detection tests (34 tests)
│   ├── requirements.txt             # Core dependencies (FastAPI, Pydantic, RapidOCR, pypdf)
│   └── README.md                    # Backend documentation
├── docs/
│   └── architecture.md              # Complete system design & specification
├── .gitignore
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
