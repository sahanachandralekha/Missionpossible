# ScamCheck System Architecture & Design Specification

> **Stage Status**: 
> - **Part 1 (Foundation)**: Complete & Verified.
> - **Part 2 (Text Pipeline)**: **COMPLETE & FULLY IMPLEMENTED**.
> - **Planned Subsequent Phases**: Image OCR, PDF extraction, Pretrained ML integration, Heuristic rules, and 0–100 Risk Engine.

---

## 1. Executive Summary & Vision

**ScamCheck** is an opportunity-risk assessment system engineered specifically to protect students and early-career jobseekers from predatory schemes, fake internships, illegitimate work-from-home gigs, task scams, and deceptive training programs.

### Why Explainable Risk (0–100) Matters
Traditional spam detectors produce naive binary verdicts ("SCAM" vs. "NOT A SCAM"). ScamCheck takes a nuanced, signal-driven approach:
- Computes an **explainable Risk Score (0–100)** calibrated across multiple validated indicators.
- Categorizes risk into actionable bands (Low, Moderate, High, Severe).
- Provides concrete, educational **reasons and evidence markers** (e.g. upfront registration fee detected, high-urgency language, off-platform Telegram/WhatsApp recruitment redirection, unregistered business entities).
- Represents detected risk signals without claiming absolute certainty.

---

## 2. Multi-Format Input Support & Text Pipeline

Students encounter opportunities across numerous communication channels (WhatsApp, LinkedIn, Telegram, Instagram DMs, email, campus bulletin boards, PDF offer letters, web pages). 

### Text Input Pipeline Flow (Part 2: Implemented)

```
USER TEXT SUBMISSION
         ↓
SCHEMA VALIDATION (Pydantic: non-empty, non-whitespace, string type check)
         ↓
INPUT SERVICE ORCHESTRATION (Route to TextProcessor)
         ↓
TEXT PROCESSOR (Conservative Normalization)
  - Reject oversized text (>100,000 chars configurable)
  - Strip dangerous non-printable control bytes (\x00-\x1f, \x7f)
  - Preserve tabs (\t), newlines (\n), emojis, and Unicode
  - Standardize line breaks (CRLF/CR -> LF)
  - Collapse excessive blank lines (3+ -> 2)
  - Strip accidental outer bounding whitespace
  - 100% PRESERVE: URLs, Emails, Phone Numbers, Currencies, Percentages, Dates, Casing, Punctuation
         ↓
NORMALIZED OpportunityInput
  - source_type = "text"
  - raw_text = Pristine original user submission
  - extracted_text = Normalized text ready for analysis
  - metadata = {char_count, word_count, line_count, ...}
  - processing_status = "normalized"
         ↓
[FUTURE ANALYSIS LAYER] (ML Classifier & Risk Scoring Engine)
```

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   Plain Text    │       │  Image / Photo  │       │  PDF Documents  │
│ (WhatsApp/Email)│       │ (Screenshots)   │       │ (Offer Letters) │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  TextProcessor  │       │ ImageProcessor  │       │  PdfProcessor   │
│  [Implemented]  │       │  [Planned OCR]  │       │ [Planned Parse] │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         └───────────────────┬─────┴─────────────────────────┘
                             ▼
                 ┌───────────────────────┐
                 │   InputService        │
                 │   (Orchestrator)      │
                 └───────────┬───────────┘
                             ▼
                 ┌───────────────────────┐
                 │   OpportunityInput    │
                 │ (Normalized Contract) │
                 └───────────────────────┘
```

1. **Text**: Direct copy-pasted messages, job descriptions, emails, and SMS alerts.
2. **Images / Screenshots / Photos**: Screenshots of messaging threads (WhatsApp, Telegram, Instagram) and job board flyers (`.png`, `.jpg`, `.jpeg`, `.webp`).
3. **PDF Documents**: Formal internship offer letters, training brochures, and contract PDFs (`.pdf`).

---

## 3. The Normalized `OpportunityInput` Contract

A core architectural principle of ScamCheck is **data normalization at the boundary**. Downstream analysis layers (Machine Learning, rule heuristics, contact extractors) must never interact directly with raw binary image streams or PDF bytes.

All inputs are converted into an immutable, unified Pydantic model:

```python
class OpportunityInput(BaseModel):
    source_type: SourceType          # 'text', 'image', or 'pdf'
    original_filename: Optional[str] # e.g. 'offer_letter.pdf' or None
    mime_type: Optional[str]         # e.g. 'application/pdf', 'image/png'
    raw_text: Optional[str]          # Original pre-normalized text (if text input)
    extracted_text: str              # Normalized textual payload for downstream ML/rules
    metadata: Dict[str, Any]         # Context: file size, platform hints, word count
    processing_status: ProcessingStatus # 'pending', 'extracted', 'normalized', 'failed'
```

### Downstream Invariance
Whether a student submits a 5-paragraph email, a screenshot of a WhatsApp group invitation, or a 2-page PDF agreement, the downstream ML model and risk engine evaluate `OpportunityInput.extracted_text`.

---

## 4. End-to-End Conceptual Architecture

```
                       ┌───────────────────────────────┐
                       │             USER              │
                       └───────────────┬───────────────┘
                                       │ Submits Text, Image, or PDF
                                       ▼
                       ┌───────────────────────────────┐
                       │       INPUT PROCESSING        │
                       │ (Validation, Normalization,   │
                       │        OCR / PDF Stubs)       │
                       └───────────────┬───────────────┘
                                       │ Produces
                                       ▼
                       ┌───────────────────────────────┐
                       │     NORMALIZED OPPORTUNITY    │
                       │      (OpportunityInput)       │
                       └───────────────┬───────────────┘
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
┌───────────────────────────────┐             ┌───────────────────────────────┐
│     ML ANALYSIS (PLANNED)     │             │  HEURISTIC SIGNALS (PLANNED)  │
│  - Pretrained NLP Classifier  │             │  - Upfront payment keywords   │
│  - Phishing & Fraud Weights   │             │  - Urgency & coercion cues    │
│  - Contextual Embeddings      │             │  - Unofficial contact channels│
└───────────────┬───────────────┘             └───────────────┬───────────────┘
                │                                             │
                └──────────────────────┬──────────────────────┘
                                       │ Signal Aggregation
                                       ▼
                       ┌───────────────────────────────┐
                       │      RISK ENGINE (PLANNED)    │
                       │  - Calibrated Scoring (0-100) │
                       │  - Risk Tier Assignment       │
                       │  - Evidence Aggregator        │
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │      EXPLAINABLE RESULTS      │
                       │  - Score: 78/100 (High Risk)  │
                       │  - Identified Red Flags       │
                       │  - Actionable Student Guidance│
                       └───────────────────────────────┘
```

---

## 5. Module Breakdown & Separation of Concerns

### `backend/app/schemas/`
- **`opportunity.py`**: Defines the data models (`OpportunityInput`, `SourceType`, `ProcessingStatus`, `TextSubmissionRequest`, `AnalysisResponsePlaceholder`).

### `backend/app/processors/`
- **`base.py`**: Declares `BaseInputProcessor`, the contract requiring `.validate()` and `.process()`.
- **`text_processor.py`** *(Implemented)*: Validates string lengths, strips null bytes, standardizes line breaks, collapses excess spacing, and counts characters/words.
- **`image_processor.py`** *(Foundation Implemented, OCR Planned)*: Validates image extensions (`.png`, `.jpg`, `.jpeg`, `.webp`), MIME types, and size limits (10 MB). Stubs interface for future OCR engine integration.
- **`pdf_processor.py`** *(Foundation Implemented, Extraction Planned)*: Validates PDF extensions (`.pdf`), MIME types, and size limits (15 MB). Stubs interface for digital text layer extraction and scanned OCR fallback.

### `backend/app/services/`
- **`input_service.py`** *(Implemented)*: The intake orchestrator. Detects incoming source types, routes payloads to the corresponding processor, and returns the normalized `OpportunityInput`. Does **not** contain ML or risk scoring logic.

### `backend/app/analysis/`
- **`ml/`** *(Planned)*: Architectural boundary reserved for the future pretrained ML model. Consumes `OpportunityInput.extracted_text`.
- **`risk/`** *(Planned)*: Architectural boundary reserved for the multi-signal 0–100 risk scoring engine.

### `backend/app/api/`
- **`routes/analysis.py`** *(Implemented)*: REST API endpoints (`/api/analyze/text`, `/api/analyze/file`).
- **`main.py`** *(Implemented)*: FastAPI app entrypoint, CORS configuration, `/` and `/health` endpoints.

---

## 6. File Safety & Privacy Principles

1. **Strict MIME & Extension Whitelisting**:
   - Only permitted image and PDF types are accepted.
   - Executables (`.exe`, `.sh`, `.bat`, `.dll`, `.msi`) and scripts are strictly rejected with HTTP 422.
2. **File Size Boundaries**:
   - Images capped at 10 MB.
   - PDFs capped at 15 MB.
   - Text submissions capped at 100,000 characters.
3. **Zero Permanent Storage (Privacy by Default)**:
   - Uploaded opportunity documents frequently contain student PII (names, phone numbers, addresses, account IDs).
   - ScamCheck processes inputs **ephemerally in memory**.
   - No documents are saved to disk or persistent databases.
   - Full user submissions are not logged in plain text.
