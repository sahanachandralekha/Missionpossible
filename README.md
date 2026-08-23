# ScamCheck 🛡️

**ScamCheck** is an intelligent opportunity-risk assessment system engineered to protect students and early-career jobseekers from predatory schemes, fake internships, illegitimate work-from-home tasks, recruitment fraud, and deceptive scholarship/training offers.

> **Current Status**: **Part 2 Complete — Text Input Pipeline Fully Implemented & Tested**  
> Text ingestion, schema validation, conservative normalization, and evidence preservation are complete and verified with 51 passing tests. Downstream ML models, OCR vision engines, PDF extractors, and risk scoring algorithms remain clearly separated for upcoming phases.

---

## 🔍 Core Conceptual Architecture

ScamCheck does not return naive binary ("SCAM" / "NOT A SCAM") verdicts. Instead, it is designed to calculate an **explainable Risk Score (0–100)** with clear, educational evidence points.

```
USER
  ↓
TEXT / IMAGE / PDF
  ↓
INPUT PROCESSING (Validation & Normalization)
  ↓
NORMALIZED OPPORTUNITY (OpportunityInput)
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
| **Images / Photos** | Screenshots of chats, flyers, Instagram DMs | **Foundation Implemented** (`ImageProcessor`, OCR planned) |
| **PDF Documents** | Formal offer letters, brochures, contracts | **Foundation Implemented** (`PdfProcessor`, Parsing planned) |

### The Normalized `OpportunityInput` Model
All input formats are processed into an immutable common representation:
- `source_type`: `"text"`, `"image"`, or `"pdf"`
- `original_filename`: Uploaded filename (if applicable)
- `mime_type`: Content MIME classification
- `raw_text`: Pre-normalized text or raw OCR dump
- `extracted_text`: Sanitized, normalized text string passed to ML & Risk Engine
- `metadata`: Size, word count, platform hints, confidence
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
│   │   │   └── input_service.py     # Input intake & processor orchestrator
│   │   ├── processors/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Base processor abstract class
│   │   │   ├── text_processor.py    # Text validation & normalization (Implemented)
│   │   │   ├── image_processor.py   # Image validation & OCR stub (Planned)
│   │   │   └── pdf_processor.py     # PDF validation & Extraction stub (Planned)
│   │   └── analysis/
│   │       ├── __init__.py
│   │       ├── ml/
│   │       │   └── __init__.py      # Location for future pretrained ML model
│   │       └── risk/
│   │           └── __init__.py      # Location for future 0-100 risk engine
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_foundation.py       # Pytest suite verifying foundation & contracts
│   ├── requirements.txt             # Core dependencies (FastAPI, Pydantic, Pytest, etc.)
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
