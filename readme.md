# MoneyPilot 💸
Personal finance, clear. Upload bank PDFs/CSVs → get a calm cash-flow cockpit.

## ✨ Features
- PDF/CSV statement extraction (pdfplumber) with category classification
- ClickHouse analytics: balances, top categories, monthly cash flow
- Dashboard: KPI cards, income/expense bars, spending donut, cumulative cash-flow line
- Gemini-powered recommendations grounded in your real transactions
- Privacy-first: files processed locally, never leave your machine

## 🏗️ Architecture
Next.js 16 (Turbopack, App Router) → FastAPI (Python) → pdfplumber extractor → ClickHouse
                                      └→ Gemini (gemini-3.6-flash) for insights

## 🚀 Run locally
# 1. Python backend
python -m venv .venv && .venv\Scripts\activate
pip install fastapi uvicorn python-multipart pdfplumber clickhouse-connect google-genai
python python/server.py            # starts on :8000 (auto-finds free port)

# 2. Frontend
pnpm install
pnpm dev                           # Next.js on :3000, Python concurrently

## 🔐 Environment
- `.env.local`: `PYTHON_SERVER_URL=http://127.0.0.1:8000`
- Python env: `GEMINI_API_KEY=...`, ClickHouse creds in `python/database.py`

## 🎬 Demo
See [demo video](LINK) — upload → analyze → dashboard + Gemini insights in 60s.