"""MoneyPilot extractor: PDF / CSV / receipt-image -> normalized transactions."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------ categories
# Ordered rules: first match wins. Business-aware so "Other" stays tiny.
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("Payroll & HR",        ["wages", "payroll", "staff salary", "employee salary", "benefits", "hr payment"]),
    ("Revenue",             ["salary deposit", "sales deposit", "card sales", "cash sales", "client payment", "invoice paid", "revenue"]),
    ("Groceries",           ["whole foods", "grocery", "groceries", "supermarket", "costco", "kroger", "safeway", "aldi"]),
    ("Rent & Facilities",   ["rent", "lease", "landlord", "mortgage", "property"]),
    ("Utilities",           ["electric", "utility", "utilities", "water bill", "gas bill", "internet", "broadband", "power"]),
    ("Transport",           ["uber", "lyft", "taxi", "gas station", "shell", "fuel", "transit", "parking", "toll"]),
    ("Entertainment",       ["netflix", "spotify", "cinema", "movie", "gaming", "concert", "hulu", "disney"]),
    ("Shopping",            ["amazon", "target", "best buy", "ikea", "walmart", "mall", "retail", "purchase"]),
    ("Food & Dining",       ["meat", "cheese", "tomato sauce", "dough", "flour", "supplier", "ingredients", "produce", "starbucks", "restaurant", "cafe", "dining", "bakery"]),
    ("Business Operations", ["delivery platform", "platform fees", "marketing", "ads", "signage", "equipment", "repair", "maintenance", "software", "insurance", "license"]),
]

INCOME_KEYWORDS = ["salary deposit", "sales deposit", "deposit", "refund", "rebate", "interest", "credit", "income"]


def categorize(description: str) -> str:
    text = (description or "").lower()
    for category, keywords in CATEGORY_RULES:
        if any(keyword in text for keyword in keywords):
            return category
    return "Other"


# ------------------------------------------------------------------ parsing helpers
_DATE_FORMATS = (
    "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d",
    "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y", "%m-%d-%Y",
)


def normalize_date(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    try:  # pandas Timestamp / datetime objects / ISO with time
        return datetime.fromisoformat(text[:10]).strftime("%Y-%m-%d")
    except Exception:
        return None


_AMOUNT_RE = re.compile(r"[+-]?[\d,]+(?:\.\d{1,2})?")


def parse_amount(raw: Any) -> float | None:
    """Returns a SIGNED float, or None when the cell is not an amount."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip().replace("$", "").replace(" ", "").replace("€", "").replace("£", "")
    if not text:
        return None
    paren = text.startswith("(") and text.endswith(")")
    if paren:
        text = text[1:-1]
    match = _AMOUNT_RE.search(text)
    if not match:
        return None
    try:
        value = float(match.group(0).replace(",", ""))
    except ValueError:
        return None
    if paren or text.startswith("-"):
        return -abs(value)
    return abs(value)


def _is_header(cells: list[str]) -> bool:
    joined = " ".join(cells).lower()
    return "date" in joined and ("amount" in joined or "description" in joined)


def make_transaction(date_iso: str, description: str, signed_amount: float) -> dict[str, Any]:
    """amount is stored as a positive magnitude; direction lives in type."""
    desc = (description or "").strip() or "Unknown"
    if signed_amount > 0:
        tx_type = "income"
    elif signed_amount < 0:
        tx_type = "expense"
    else:
        tx_type = "income" if any(k in desc.lower() for k in INCOME_KEYWORDS) else "expense"
    return {
        "date": date_iso,
        "merchant": desc,
        "description": desc,
        "amount": round(abs(signed_amount), 2),
        "category": categorize(desc),
        "type": tx_type,
        "transaction_type": tx_type,
    }


_LINE_RE = re.compile(r"^\s*(\d{4}-\d{2}-\d{2})\s+(.+?)\s+([+-]?[\d,]+\.\d{2})\s*$")


# ------------------------------------------------------------------ PDF
def extract_pdf(path: str) -> list[dict[str, Any]]:
    import pdfplumber

    transactions: list[dict[str, Any]] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []
            for table in tables:
                for row in table:
                    cells = [(c or "").strip() if isinstance(c, str) else "" for c in row]
                    if not any(cells) or _is_header(cells):
                        continue
                    date_iso = normalize_date(cells[0])
                    if not date_iso:
                        continue
                    description = cells[1] if len(cells) > 1 else ""
                    signed = None
                    for candidate in cells[2:]:
                        signed = parse_amount(candidate)
                        if signed is not None:
                            break
                    if signed is None:
                        continue
                    transactions.append(make_transaction(date_iso, description, signed))
            if not tables:  # text-only PDFs: fall back to line regex
                for line in (page.extract_text() or "").splitlines():
                    m = _LINE_RE.match(line)
                    if m:
                        signed = parse_amount(m.group(3))
                        if signed is not None:
                            transactions.append(make_transaction(m.group(1), m.group(2), signed))
    return transactions


# ------------------------------------------------------------------ CSV
def extract_csv(path: str) -> list[dict[str, Any]]:
    import pandas as pd

    df = pd.read_csv(path)
    df.columns = [str(c).strip().lower() for c in df.columns]
    date_col = next((c for c in df.columns if "date" in c), None)
    desc_col = next((c for c in df.columns if any(k in c for k in ("description", "merchant", "detail", "payee"))), None)
    amount_col = next((c for c in df.columns if "amount" in c), None)
    if date_col is None or amount_col is None:
        return []
    transactions: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        date_iso = normalize_date(row[date_col])
        if not date_iso:
            continue
        signed = parse_amount(row[amount_col])
        if signed is None:
            continue
        description = str(row[desc_col]) if desc_col is not None and pd.notna(row[desc_col]) else "Unknown"
        transactions.append(make_transaction(date_iso, description, float(signed)))
    return transactions


# ------------------------------------------------------------------ receipt images (OCR)
def extract_image(path: str) -> list[dict[str, Any]]:
    import pytesseract
    from PIL import Image

    text = pytesseract.image_to_string(Image.open(path))
    transactions: list[dict[str, Any]] = []
    for line in text.splitlines():
        m = _LINE_RE.match(line)
        if m:
            signed = parse_amount(m.group(3))
            if signed is not None:
                transactions.append(make_transaction(m.group(1), m.group(2), signed))
    return transactions


# ------------------------------------------------------------------ entry point (used by api.py)
def extract_uploaded_file(path: str, suffix: str) -> list[dict[str, Any]]:
    suffix = (suffix or Path(path).suffix).lower()
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix == ".csv":
        return extract_csv(path)
    if suffix in (".png", ".jpg", ".jpeg", ".webp"):
        return extract_image(path)
    return []