# ScamCheck Backend

FastAPI backend foundation for the ScamCheck opportunity-risk assessment platform.

## Architecture Status
 
 - [x] Backend directory structure & modular separation
 - [x] Normalized `OpportunityInput` schema (`SourceType.TEXT`, `SourceType.IMAGE`, `SourceType.PDF`)
 - [x] Input Processing Layer & `InputService` orchestration
 - [x] `TextProcessor` (Part 2: **Fully Implemented & Verified** with conservative normalization & evidence preservation)
 - [x] `ImageProcessor` (Structure & Validation Implemented, OCR Extraction Planned)
 - [x] `PdfProcessor` (Structure & Validation Implemented, PDF Text Extraction Planned)
 - [x] Future ML Component boundary (`app/analysis/ml/`)
 - [x] Future Risk Engine boundary (`app/analysis/risk/`)
 - [x] FastAPI REST API foundation (`/api/analyze/text`, `/api/analyze/file`, `/health`)
 - [x] Automated test suite (`51/51` test cases passing across foundation and text pipeline)

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

Execute the pytest suite:

```bash
python -m pytest backend/tests/test_foundation.py -v
```
