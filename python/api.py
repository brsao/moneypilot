from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import sys

# Add the current file's directory to the system path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from database import init_database, insert_transactions, get_financial_summary, get_all_transactions_for_chart
from extractor import extract_uploaded_file

app = FastAPI(title="MoneyPilot API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup() -> None:
    init_database()

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

class InsightsRequest(BaseModel):
    summary: dict[str, Any] = {}
    chart_data: list[dict[str, Any]] = []

@app.post("/insights")
def insights(payload: InsightsRequest) -> dict[str, str]:
    try:
        from google import genai
        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        prompt = f"""You are MoneyPilot, a cautious personal finance coach. Analyze only this uploaded financial data and give 3 concise, practical recommendations. Include cash-flow health, spending habits, and one anomaly or caution. Never invent facts, never recommend specific investments, and clearly say when data is insufficient. Use Markdown. DATA: {payload.model_dump_json()}"""
        response = client.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"), contents=prompt)
        return {"text": response.text or "Gemini returned no recommendations."}
    except KeyError as error:
        raise HTTPException(status_code=503, detail=f"Missing environment variable: {error.args[0]}") from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Gemini insights failed: {error}") from error

@app.post("/analyze")
async def analyze(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one file")
    allowed = {".pdf", ".csv", ".png", ".jpg", ".jpeg", ".webp"}
    all_transactions: list[dict[str, Any]] = []
    processed: list[str] = []
    try:
        for upload in files[:8]:
            suffix = Path(upload.filename or "upload").suffix.lower()
            if suffix not in allowed:
                raise HTTPException(status_code=415, detail=f"Unsupported file type: {suffix}")
            content = await upload.read()
            if len(content) > 10 * 1024 * 1024:
                raise HTTPException(status_code=413, detail=f"{upload.filename} exceeds 10 MB")
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp:
                temp.write(content)
                temp_path = temp.name
            try:
                all_transactions.extend(extract_uploaded_file(temp_path, suffix))
                processed.append(upload.filename or "upload")
            finally:
                Path(temp_path).unlink(missing_ok=True)
        if not all_transactions:
            raise HTTPException(status_code=422, detail="No transactions could be extracted from the uploaded files")
        insert_transactions(all_transactions)
        summary = get_financial_summary(days=365)
        return {"status": "ok", "processed_files": processed, "transaction_count": len(all_transactions), "summary": summary, "chart_data": get_all_transactions_for_chart()}
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

SAMPLE_PDF = Path(__file__).resolve().parent / "sample_data" / "sample_statement.pdf"


@app.get("/summary")
def summary() -> dict[str, Any]:
    """Current ClickHouse aggregates — same shape as /analyze, no upload needed."""
    data = get_financial_summary(days=365)
    recent = data.get("recent_transactions") or []
    try:
        from database import get_client
        total = int(list(get_client().query("SELECT count() AS c FROM default.transactions").named_results())[0]["c"])
    except Exception:
        total = len(recent)
    return {
        "status": "ok",
        "processed_files": ["clickhouse-session"],
        "transaction_count": total,
        "summary": data,
        "chart_data": get_all_transactions_for_chart(),
    }


@app.post("/seed")
def seed() -> dict[str, Any]:
    """First-run bootstrap: analyze the bundled sample statement once."""
    if not SAMPLE_PDF.exists():
        raise HTTPException(status_code=404, detail=f"Sample statement not found at {SAMPLE_PDF}. Copy your PDF there.")
    transactions = extract_uploaded_file(str(SAMPLE_PDF), ".pdf")
    if not transactions:
        raise HTTPException(status_code=422, detail="No transactions extracted from the sample statement")
    insert_transactions(transactions)
    return summary()

@app.post("/reset")
def reset() -> dict[str, str]:
    """Wipe all transactions (demo hygiene)."""
    from database import get_client
    get_client().command("TRUNCATE TABLE IF EXISTS default.transactions")
    return {"status": "truncated"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)

# Run from the python directory: python -m uvicorn api:app --reload --port 8000
