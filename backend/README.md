# ScamCheck Backend

FastAPI backend foundation for the ScamCheck opportunity-risk assessment platform.

## Architecture Status
 
 - [x] Backend directory structure & modular separation
 - [x] Normalized `OpportunityInput` schema (`SourceType.TEXT`, `SourceType.IMAGE`, `SourceType.PDF`)
 - [x] Input Processing Layer & `InputService` orchestration
 - [x] `TextProcessor` (Part 2: **Fully Implemented & Verified**)
 - [x] `ImageProcessor` & `OCRService` (Part 3: **Fully Implemented & Verified** with local RapidOCR ONNX inference)
 - [x] `PdfProcessor` & `PDFService` (Part 4: **Fully Implemented & Verified** with pure-Python pypdf text extraction)
 - [x] Common Analysis Contracts & Schemas (`AnalysisContext`, `ExtractedEntities`, `RiskSignal`, `Evidence`, `AnalysisResult`)
 - [x] `EntityExtractor` (Part 6: **Fully Implemented & Verified** with deterministic entity extraction)
 - [x] `RuleBasedSignalEngine` (Part 7: **Fully Implemented & Verified** with deterministic rule-based scam signal detection)
 - [x] `RiskScoringEngine` (Part 8: **Fully Implemented & Verified** with calibrated 0-100 scoring & RiskLevel bands)
 - [x] `AnalysisService` (Part 9: **Fully Implemented & Verified** with unified end-to-end analysis orchestration)
 - [x] `UrlAnalyzer` (Part 10: **Fully Implemented & Verified** with URL & domain structure intelligence)
 - [x] `SemanticAnalyzer` (Part 11: **Fully Implemented & Verified** with ML/LLM semantic intelligence & provider abstraction)
 - [x] `DomainVerifier` (Part 12: **Fully Implemented & Verified** with external domain verification, identity intelligence, & SSRF protection)
 - [x] Production REST API Boundary (Part 13: **Fully Implemented & Verified** with `/api/v1/analyze`, `/api/v1/analyze/file`, `/api/v1/health`, request IDs, and structured errors)
 - [x] Persistent Analysis History (Part 14: **Fully Implemented & Verified** with `AnalysisRepository`, SQLite durability, `/api/v1/analyses`, and `/api/v1/analyses/{id}`)
 - [x] React Single-Page Application Frontend (Part 15: **Fully Implemented & Verified** in `/frontend` consuming `/api/v1/` endpoints)
 - [x] Operational Hardening & Diagnostics (Part 16: **Fully Implemented & Verified** with centralized configuration, structured JSON logging, correlation request IDs, telemetry metrics, security headers, `/ready` probes, and Docker container support)
 - [x] Automated test suite (`352/352` backend pytest cases passing across foundation, text, image, PDF, contracts, extraction, rules, scoring, analysis service, URL analysis, ML semantic intelligence, domain verification, API v1 boundary, SQLite persistence, and operational hardening)












## Installation & Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the API Server

Start the local development server:

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Once running, interactive API documentation is available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Running Tests

Execute the complete pytest suite:

```bash
python -m pytest -v
```
