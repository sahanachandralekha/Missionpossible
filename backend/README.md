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
 - [x] Future ML Component boundary (`app/analysis/ml/`)
 - [x] FastAPI REST API foundation (`/api/analyze/text`, `/api/analyze/file`, `/health`)
 - [x] Automated test suite (`220/220` test cases passing across foundation, text, image, PDF, contracts, extraction, rules, scoring, and analysis service pipelines)





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
