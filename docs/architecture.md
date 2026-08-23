# ScamCheck System Architecture & Design Specification

> **Stage Status**: 
> - **Part 1 (Foundation)**: Complete & Verified.
> - **Part 2 (Text Pipeline)**: Complete & Verified.
> - **Part 3 (Image & OCR Pipeline)**: Complete & Verified.
> - **Part 4 (PDF Extraction Pipeline)**: **COMPLETE & FULLY IMPLEMENTED**.
> - **Planned Subsequent Phases**: Pretrained ML model integration, Heuristic rules, and 0–100 Risk Engine.

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

## 2. Ingestion Pipelines & Modality Convergence

Students encounter opportunities across numerous communication channels (WhatsApp, LinkedIn, Telegram, Instagram DMs, email, campus bulletin boards, PDF offer letters, web pages).

### The Ingestion Convergence Guarantee

```
TEXT ──────────────────────┐
                           │
IMAGE → OCR ───────────────┤
                           │
PDF → TEXT EXTRACTION ─────┘
                           ↓
                   TextProcessor
                           ↓
                  OpportunityInput
                           ↓
                   FUTURE ANALYSIS
```

### A. Text Input Pipeline Flow (Implemented)

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
NORMALIZED OpportunityInput (source_type = "text")
```

### B. Image & Screenshot OCR Pipeline Flow (Implemented)

```
USER IMAGE / SCREENSHOT UPLOAD (.png, .jpg, .jpeg, .webp)
         ↓
SECURITY & FORMAT VALIDATION (MIME, size ≤ 10 MB, non-empty)
         ↓
IMAGE DECODE & PREPROCESSING (Pillow: in-memory stream, RGBA alpha composite, EXIF rotation)
         ↓
LOCAL OCR INFERENCE (RapidOCR with ONNX Runtime on CPU)
         ↓
TEXT NORMALIZATION (Via Existing TextProcessor)
         ↓
NORMALIZED OpportunityInput (source_type = "image")
```

### C. PDF Document Text Extraction Flow (Part 4: Implemented)

```
USER PDF DOCUMENT UPLOAD (.pdf)
         ↓
SECURITY & FORMAT VALIDATION
  - Whitelist check: .pdf extension & application/pdf MIME
  - Header inspection: %PDF- magic signature verification
  - Safety limits: File size ≤ 15 MB, Page count ≤ 100 pages
  - Non-empty byte verification
         ↓
IN-MEMORY INSPECTION & DECODING (pypdf via PDFService)
  - Memory-only stream processing (ephemeral, zero disk writes)
  - Encryption check: Detects password-protected PDFs without bypassing
  - Metadata inspection: Extracts document title, author, creation date (contextual only)
         ↓
PAGE-BY-PAGE EXTRACTION & BOUNDARY ASSEMBLY
  - Iterates over pages extracting embedded digital text layer
  - Assembles multi-page documents with deterministic boundary markers:
      "--- Page 1 ---\n<text>\n\n--- Page 2 ---\n<text>"
  - Handles blank / image-only PDFs with explicit 'no_extractable_text' status
         ↓
TEXT NORMALIZATION (Via Existing TextProcessor)
  - Passes extracted raw text directly through TextProcessor
  - Retains all formatting, URLs, emails, currencies, and dates
         ↓
NORMALIZED OpportunityInput
  - source_type = "pdf"
  - raw_text = Raw assembled PDF text
  - extracted_text = Normalized text
  - metadata = {
      "pdf_page_count": 3,
      "pdf_extraction_engine": "pypdf",
      "pdf_status": "success",
      "pdf_title": "...",
      "pdf_author": "...",
      "char_count": 1420,
      "word_count": 215,
      ...
    }
  - processing_status = "normalized" (or "failed" with explicit reason)
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
│  [Implemented]  │       │ [RapidOCR Live] │       │  [pypdf Live]   │
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
- **`text_processor.py`** *(Implemented & Verified)*: Validates string lengths, strips non-printable control bytes, standardizes line breaks, collapses excess blank lines, and guarantees 100% evidence preservation.
- **`image_processor.py`** *(Implemented & Verified)*: Validates image extensions (`.png`, `.jpg`, `.jpeg`, `.webp`), MIME types, and size limits (10 MB). Delegates to `OCRService` for local RapidOCR inference and feeds text to `TextProcessor`.
- **`pdf_processor.py`** *(Implemented & Verified)*: Validates PDF extensions (`.pdf`), MIME types, and size limits (15 MB). Delegates to `PDFService` for `pypdf` embedded text extraction, page assembly, and routes text to `TextProcessor`.

### `backend/app/services/`
- **`input_service.py`** *(Implemented & Verified)*: The intake orchestrator. Detects incoming source types, routes payloads to the corresponding processor, and returns the normalized `OpportunityInput`. Does **not** contain ML or risk scoring logic.
- **`ocr_service.py`** *(Implemented & Verified)*: Free, local, offline RapidOCR service with Pillow preprocessing and EXIF auto-rotation.
- **`pdf_service.py`** *(Implemented & Verified)*: Free, local, pure-Python pypdf text extraction service with safety limits, metadata parsing, and encryption detection.

### `backend/app/analysis/`
- **`analysis_service.py`** *(Implemented & Verified)*: Unified analysis orchestrator (`AnalysisService`) executing the complete analytical sequence from `OpportunityInput` to `AnalysisResult`.
- **`models/`** *(Implemented & Verified)*: Common analysis data contracts (`AnalysisResult`, `RiskSignal`, `Evidence`, `ExtractedEntities`, `AnalysisContext`, `RiskLevel`, `SignalSeverity`, `AnalysisStatus`).
- **`extraction/`** *(Implemented & Verified)*: Deterministic Entity Extractor (`EntityExtractor`) identifying organizations, job roles, emails, phones, URLs, monetary sums, percentages, dates, locations, and payment details from normalized text.
- **`rules/`** *(Implemented & Verified)*: Deterministic Rule-Based Scam Signal Engine (`RuleBasedSignalEngine`) detecting upfront fees, urgency, guarantees, no-interview claims, unrealistic compensation, authority claims, and informal contact redirection.
- **`risk/`** *(Implemented & Verified)*: Deterministic Risk Scoring Engine (`RiskScoringEngine`) calculating calibrated 0–100 risk scores, RiskLevel bands, reasons, and student guidance.
- **`ml/`** *(Planned)*: Architectural boundary reserved for the future pretrained ML model. Consumes `OpportunityInput.extracted_text`.




### `backend/app/api/`
- **`routes/analysis.py`** *(Implemented)*: REST API endpoints (`/api/analyze/text`, `/api/analyze/file`).
- **`main.py`** *(Implemented)*: FastAPI app entrypoint, CORS configuration, `/` and `/health` endpoints.


---

## 6. Analysis Data Contract

The ScamCheck analysis architecture is governed by a unified data contract connecting raw ingestion to the final explainable risk assessment.

> **Important Boundary Note**: The analysis contracts define the schemas, enums, and data relationships. Scam detection rules, ML model evaluation, heuristic keyword extraction, and risk score calculation are explicitly reserved for subsequent phases.

### Analysis Pipeline Flow

```
INPUT (Text / Image / PDF)
         ↓
OpportunityInput (Normalized Ingestion Representation)
         ↓
AnalysisContext (Standardized Execution Envelope)
         ↓
ExtractedEntities (Organizations, Contacts, Payments, URLs, Dates)
         ↓
RiskSignals (Individual Multi-Source Risk Indicators + Evidence)
         ↓
RiskScoring (Future Calibrated 0–100 Scoring Synthesis)
         ↓
AnalysisResult (Explainable Result, Risk Level Band, Reasons, Guidance)
```

### Key Contract Specifications

1. **Calibrated Risk Levels (`RiskLevel`)**:
   - `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
   - *Never* uses binary `SCAM` / `NOT_SCAM` labels.
2. **Signal Severity (`SignalSeverity`)**:
   - `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
   - Decoupled from the final opportunity risk score; individual indicators contribute weighted signal rather than hard-failing an opportunity.
3. **Traceable Evidence (`Evidence`)**:
   - Stores exact extracted values (`₹999`, `immediately`), source modality, line/page location, surrounding context, and normalized representations.
4. **Structured Entities (`ExtractedEntities`)**:
   - Type-safe schemas for extracted organizations, job titles, emails, phone numbers, URLs, monetary amounts, percentages, dates, locations, payment details, and contact aggregations.
5. **Execution Context (`AnalysisContext`)**:
   - Encapsulates `OpportunityInput`, `ExtractedEntities`, `evidence_pool`, and diagnostic metadata passed between analytical components.
6. **Final Output (`AnalysisResult`)**:
   - Unifies `risk_score` (0–100), `risk_level`, `signals`, `reasons`, `summary`, and `extracted_entities`.
   - Distinguishes extraction/processing failures (`AnalysisStatus.FAILED`) from fraud signals (ensuring technical OCR/PDF errors are never conflated with high scam risk).

---

## 7. Entity Extraction Layer (Implemented & Verified)

The Entity Extraction layer (`backend/app/analysis/extraction/entity_extractor.py`) deterministically identifies and extracts factual elements from normalized opportunity text (`OpportunityInput.extracted_text` encapsulated in `AnalysisContext`).

> **Architectural Boundary Guarantee**:
> - **Entity Extraction = "What factual information is present?"**
> - **Risk Signal Engine = "Why might that information indicate predatory risk?"**
>
> The `EntityExtractor` **never** calculates risk scores, assigns risk levels, or classifies opportunities. Extracted entities are factual data objects passed to the future Rule Engine and ML Classifier.

### Architectural Flow

```
TEXT ──────────────────────┐
                           │
IMAGE → OCR ───────────────┤
                           │
PDF → TEXT EXTRACTION ─────┘
                           ↓
                   OpportunityInput
                           ↓
                    AnalysisContext
                           ↓
                    EntityExtractor
                           ↓
                   ExtractedEntities
                     + Evidence List
                           ↓
               FUTURE Risk Signal Engine
```

### Supported Entity Extractions
1. **Organizations (`OrganizationEntity`)**: Identifies companies and institutions via business entity suffixes (`Ltd`, `Pvt Ltd`, `LLC`, `Inc`, `Technologies`, `Solutions`, `Systems`, `Software`, `Labs`, `Services`).
2. **Job Titles (`JobTitleEntity`)**: Identifies technical, non-technical, and internship roles (`Frontend Developer`, `Data Analyst`, `Content Writer`, `Research Intern`, `Remote Internship`).
3. **Emails (`EmailEntity`)**: Standard email address extraction with automated free-provider classification (`gmail.com`, `yahoo.com`, `hotmail.com`).
4. **Phone Numbers (`PhoneEntity`)**: Extracts national and international phone numbers (`+91 9876543210`, `(800) 555-0199`) while filtering out standalone dates, years, or monetary numbers.
5. **URLs (`UrlEntity`)**: Extracts complete web hyperlinks with domain, path, and link shortener detection (`bit.ly`, `tinyurl.com`).
6. **Monetary Amounts (`MonetaryAmountEntity`)**: Parses international currency symbols (`₹`, `$`, `€`, `£`, `¥`) and ISO codes (`INR`, `USD`, `EUR`), parses numeric values, and determines context purpose (`fee`, `deposit`, `salary`, `stipend`).
7. **Percentages (`PercentageEntity`)**: Parses numeric percentages and contextual modifiers (`40% commission`, `100% guarantee`).
8. **Dates (`DateEntity`)**: Extracts deadlines and commencement dates across numerical and textual date formats (`25/10/2026`, `October 25, 2026`).
9. **Locations (`LocationEntity`)**: Matches prominent urban centers and remote work designations (`Remote`, `Work From Home`, `WFH`).
10. **Payment Details (`PaymentDetailEntity`)**: Extracts explicit payment requests, upfront fees (`registration fee`, `security deposit`, `training fee`), and UPI handles (`hr@okaxis`, `paytm`).
11. **Contact Information (`ContactInfoEntity`)**: Aggregates verified communication avenues across emails, phones, URLs, and social handles (Telegram, WhatsApp, Instagram).

---

## 8. Rule-Based Scam Signal Detection Layer (Implemented & Verified)

The Rule-Based Signal Detection layer (`backend/app/analysis/rules/rule_engine.py`) deterministically detects predatory and fraudulent opportunity patterns from normalized text and structured entity facts (`ExtractedEntities`).

> **Architectural Boundary Guarantee**:
> - **Entity Extraction** = *"What factual information exists?"*
> - **Rule-Based Signal Engine** = *"What suspicious patterns are present?"*
> - **Risk Scoring Engine** = *"How much should those signals contribute to the overall 0–100 risk score?"* (Part 8)
>
> The `RuleBasedSignalEngine` **never** calculates a final 0–100 risk score, assigns a `RiskLevel`, or classifies an opportunity as `SCAM`/`NOT_SCAM`. All generated signals carry neutral `score_contribution = 0.0`.

### Architectural Pipeline Flow

```
TEXT / IMAGE (OCR) / PDF
           ↓
   OpportunityInput
           ↓
    AnalysisContext
           ↓
    EntityExtractor
           ↓
   ExtractedEntities
           ↓
 RuleBasedSignalEngine
   ├── Upfront Payment Detection (registration fees, deposits)
   ├── Urgency & Pressure Language (limited slots, act now)
   ├── Guaranteed Selection Claims (100% placement)
   ├── No Interview / Direct Hiring
   ├── Unrealistic / Effortless Earnings
   ├── Authority / Government Claims
   ├── Informal Messaging Redirection (Telegram, WhatsApp)
   ├── Personal UPI Destinations
   ├── Unsolicited Selection Notices
   └── Compound Multi-Risk Synthesis
           ↓
   List[RiskSignal] (with traceable Evidence)
           ↓
[FUTURE PART 8: RiskScoringEngine]
```

### Detected Signal Categories
1. **Upfront Payment Demands (`SIG_UPFRONT_PAYMENT`)**: Identifies registration, processing, security, or training fees with contextual negation handling (e.g. "no fee required" is safely ignored).
2. **Urgency & Coercion Language (`SIG_URGENCY_PRESSURE`)**: Detects high-pressure countdowns, artificial slot limits, and immediate payment commands while ignoring ordinary calendar deadlines.
3. **Guaranteed Placement (`SIG_GUARANTEED_SELECTION`)**: Flags unrealistic promises of 100% hiring or placement without merit review.
4. **No-Interview Direct Hiring (`SIG_NO_INTERVIEW`)**: Detects claims of instant appointment without screening.
5. **No Experience Claims (`SIG_NO_EXPERIENCE`)**: Flags entry-level claims paired with outsized promises.
6. **Unrealistic Earnings (`SIG_UNREALISTIC_EARNINGS`)**: Flags claims like "earn ₹1 lakh/week for 1 hour/day" while preserving legitimate corporate compensation structures.
7. **Government Authority Claims (`SIG_AUTHORITY_CLAIM`)**: Flags unverified claims of government/ministry endorsement.
8. **Informal Contact Redirection (`SIG_INFORMAL_CONTACT_CHANNEL`)**: Detects off-platform recruitment instructions funneling students into Telegram/WhatsApp.
9. **Personal Payment Handles (`SIG_PERSONAL_PAYMENT_DESTINATION`)**: Flags payment requests routing funds to personal UPI VPAs.
10. **Unsolicited Selection (`SIG_UNSOLICITED_SELECTION`)**: Flags notifications of selection for roles the recipient never applied for.
11. **Document Issuance Claims (`SIG_DOCUMENT_CLAIM`)**: Flags claims of pre-attached appointment letters.
12. **Compound Multi-Risk Patterns (`SIG_MULTIPLE_HIGH_RISK_PATTERNS`)**: Flags the simultaneous co-occurrence of upfront fees, urgency pressure, and guaranteed hiring.

---

## 9. Risk Scoring Engine (Implemented & Verified)

The Risk Scoring Engine (`backend/app/analysis/risk/scoring_engine.py`) synthesizes detected `RiskSignal` objects into a calibrated 0–100 numerical risk score, maps the score into a deterministic `RiskLevel` band, and generates student-friendly safety guidance and explainable reasons.

> **Architectural Boundary Guarantee**:
> - **Entity Extraction** = *"What factual information exists?"*
> - **Rule-Based Signal Detection** = *"What suspicious patterns are present?"*
> - **Risk Scoring Engine** = *"How much do those signals contribute to overall risk?"*
> - **Future ML Layer** = *"What subtle semantics might rules have missed?"*
> - **Future URL/Domain Layer** = *"Does external identity verification support or contradict the claim?"*
>
> The `RiskScoringEngine` consumes structured `RiskSignal` objects and does not perform raw text regex extraction or external network calls.

### Architectural Pipeline Flow

```
TEXT / IMAGE (OCR) / PDF
           ↓
   OpportunityInput
           ↓
    AnalysisContext
           ↓
    EntityExtractor
           ↓
   ExtractedEntities
           ↓
 RuleBasedSignalEngine
           ↓
   List[RiskSignal]
           ↓
   RiskScoringEngine
   ├── Centralized Weight Lookup (score_policy.py)
   ├── Severity Multipliers (LOW: 0.50, MED: 0.75, HIGH: 1.00)
   ├── Confidence Scaling (0.0 to 1.0)
   ├── Bounded Compound Adjustment (+10 max)
   ├── Defensive Signal Deduplication
   ├── Score Normalization & Clamping (0 to 100)
   └── RiskLevel Band Assignment
           ↓
    AnalysisResult
   ├── risk_score (0–100)
   ├── risk_level (LOW, MEDIUM, HIGH, CRITICAL)
   ├── reasons (explainable bullet points)
   ├── student_guidance (educational advice)
   ├── summary (calibrated narrative)
   └── evidence & extracted_entities
           ↓
[FUTURE: ML Semantic & Domain Verification Signal Fusion]
```

### Risk Level Calibration Bands

| Score Range | Risk Level | Description | Student Safety Action |
| :--- | :--- | :--- | :--- |
| **0 – 24** | `RiskLevel.LOW` | Minimal risk indicators detected. | Review opportunity and verify employer before sharing personal info. |
| **25 – 49** | `RiskLevel.MEDIUM` | Some suspicious indicators detected. | Proceed cautiously; verify employer and contact details independently. |
| **50 – 74** | `RiskLevel.HIGH` | Multiple significant scam indicators detected. | Do not pay fees or share sensitive documents until verified. |
| **75 – 100** | `RiskLevel.CRITICAL` | Severe predatory scam patterns detected. | Do not pay or share sensitive info; verify through official website. |

---

## 10. Unified Analysis Orchestration Layer (Implemented & Verified)

The Unified Analysis Orchestration Layer (`backend/app/analysis/analysis_service.py`) coordinates the sequential execution of all deterministic analysis subcomponents through a single programmatic entry point: `AnalysisService.analyze(opportunity_input)`.

### Responsibilities
- **Input Intake & Validation**: Verifies `OpportunityInput` validity and initializes `AnalysisContext(status=PROCESSING)`.
- **Entity Extraction**: Invokes `EntityExtractor` to extract structured entities (`ExtractedEntities`) and attach initial evidence.
- **Rule Detection**: Invokes `RuleBasedSignalEngine` to detect suspicious patterns and collect `List[RiskSignal]`.
- **Risk Scoring**: Passes context and signals to `RiskScoringEngine` to synthesize the 0–100 risk score and `RiskLevel`.
- **Traceable Evidence Preservation**: Ensures `Evidence` instances retain their source modalities, offsets, and context throughout the pipeline.
- **Graceful Error Isolation**: Distinguishes upstream technical processing failures (`ProcessingStatus.FAILED`) from scam risk (guaranteeing `risk_score = 0` and `risk_level = LOW`).
- **Complete Offline / Privacy Guarantees**: Operates 100% locally with zero network queries, DNS lookups, or persistent database writes.

### Architectural Pipeline Flow

```
TEXT ───────────────────┐
                       │
IMAGE → RapidOCR ──────┤
                       │
PDF → pypdf ───────────┘
                       ↓
              OpportunityInput
                       ↓
              AnalysisContext
                       ↓
               AnalysisService
                       ↓
              EntityExtractor
                       ↓
              ExtractedEntities
                       ↓
          RuleBasedSignalEngine
                       ↓
                RiskSignals
                       ↓
             RiskScoringEngine
                       ↓
               AnalysisResult
                       ↓
          [Future Intelligence Layers]
```

---

## 11. File Safety & Privacy Principles

1. **Strict MIME & Extension Whitelisting**:
   - Only permitted image and PDF types are accepted.
   - Executables (`.exe`, `.sh`, `.bat`, `.dll`, `.msi`) and scripts are strictly rejected with HTTP 422.
2. **File Size Boundaries**:
   - Images capped at 10 MB.
   - PDFs capped at 15 MB and 100 pages maximum.
   - Text submissions capped at 100,000 characters.
3. **No Code Execution**:
   - File contents and extracted text are treated strictly as passive data streams.
   - Prompt injection attempts and URL command parameters are parsed strictly as literal data strings.
4. **Ephemeral Processing & Zero Persistence**:
   - Uploaded images, PDFs, and extracted text are processed 100% in-memory and are never stored in databases, log streams, or persistent disks.
5. **Privacy by Default**:
   - Full student opportunity text is never logged or leaked in error responses.
   - Full user submissions are not logged in plain text.



