# extractor.py
import pdfplumber
from datetime import datetime
import re

def extract_pdf_statement(pdf_path: str) -> list[dict]:
    """Extracts transactions from a real PDF bank statement."""
    print(f"📄 Extracting data from {pdf_path}...")
    
    transactions = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            
            for table in tables:
                for row in table:
                    if len(row) >= 3:
                        transaction = parse_transaction_row(row)
                        if transaction:
                            transactions.append(transaction)
    
    print(f"✅ Extracted {len(transactions)} transactions from PDF\n")
    return transactions

def parse_transaction_row(row: list) -> dict | None:
    """Parses a table row into a transaction dict, skipping headers."""
    try:
        # Clean inputs - handle multiline cells like "September\n2026-09-01"
        raw_date = str(row[0]).strip() if row[0] else None
        description = str(row[1]).strip() if len(row) > 1 else "Unknown"
        amount_str = str(row[2]).strip() if len(row) > 2 else "0"
        
        # FIX: Handle multiline dates by taking the last line (the actual date)
        if raw_date and "\n" in raw_date:
            raw_date = raw_date.split("\n")[-1].strip()
            
        # SKIP HEADER ROWS
        if not raw_date or "date" in raw_date.lower() or "description" in description.lower():
            return None
        
        # Validate date format strictly (YYYY-MM-DD)
        try:
            date_obj = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            return None  # Skip rows like "July 2026" or "August 2026"
        
        # Parse amount (handle commas, $, +)
        amount_str = amount_str.replace(",", "").replace("$", "").replace("+", "")
        try:
            amount = float(amount_str)
        except ValueError:
            return None
        
        category = categorize_transaction(description)
        
        return {
            "date": date_obj,
            "merchant": description,
            "amount": abs(amount),
            "category": category,
            "description": description
        }
    except Exception:
        return None

def extract_uploaded_file(file_path: str, suffix: str) -> list[dict]:
    """Extract transactions from PDF, CSV, or receipt image files."""
    if suffix == ".pdf":
        return extract_pdf_statement(file_path)
    if suffix == ".csv":
        import pandas as pd
        frame = pd.read_csv(file_path)
        columns = {str(column).strip().lower(): column for column in frame.columns}
        date_column = next((columns[name] for name in ("date", "transaction date", "posted date") if name in columns), None)
        description_column = next((columns[name] for name in ("description", "merchant", "name", "payee") if name in columns), None)
        amount_column = next((columns[name] for name in ("amount", "value", "transaction amount") if name in columns), None)
        if not date_column or not description_column or not amount_column:
            raise ValueError("CSV must include date, description/merchant, and amount columns")
        transactions = []
        for _, row in frame.iterrows():
            try:
                date_value = datetime.fromisoformat(str(row[date_column])[:10]).date()
                amount = float(str(row[amount_column]).replace(",", "").replace("$", "").strip())
                description = str(row[description_column]).strip()
                transactions.append({"date": date_value, "merchant": description, "amount": abs(amount), "category": categorize_transaction(description), "description": description})
            except (TypeError, ValueError):
                continue
        return transactions
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        try:
            import pytesseract
            from PIL import Image
            text = pytesseract.image_to_string(Image.open(file_path))
        except ImportError as error:
            raise ValueError("Receipt images require Pillow and Tesseract OCR") from error
        match = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2}).{0,120}?(\$?\s?[\d,]+\.\d{2})", text, re.S)
        if not match:
            raise ValueError("Could not find a date and total in the receipt image")
        date_value = datetime.strptime(match.group(1).replace("/", "-"), "%Y-%m-%d").date()
        amount = float(match.group(2).replace("$", "").replace(",", "").strip())
        description = next((line.strip() for line in text.splitlines() if line.strip()), "Receipt")
        return [{"date": date_value, "merchant": description, "amount": amount, "category": categorize_transaction(description), "description": description}]
    raise ValueError(f"Unsupported file type: {suffix}")

def categorize_transaction(description: str) -> str:

    """Auto-categorizes transactions based on keywords."""
    description_lower = description.lower()
    
    categories = {
        "Entertainment": ["netflix", "spotify", "hulu", "disney", "youtube"],
        "Groceries": ["whole foods", "trader joe", "safeway", "grocery", "market"],
        "Transport": ["uber", "lyft", "shell", "chevron", "gas", "parking"],
        "Shopping": ["amazon", "target", "walmart", "costco"],
        "Food & Dining": ["starbucks", "mcdonald", "restaurant", "cafe", "pizza"],
        "Utilities": ["electric", "water", "gas bill", "internet", "phone"],
        "Health": ["pharmacy", "cvs", "walgreens", "doctor", "medical"],
    }
    
    for category, keywords in categories.items():
        if any(keyword in description_lower for keyword in keywords):
            return category
    
    return "Other"

if __name__ == "__main__":
    from database import init_database, insert_transactions
    print(" Starting MoneyPilot Data Ingestion...\n")
    init_database()
    transactions = extract_pdf_statement("real_multi_month_statement.pdf")
    if transactions:
        count = insert_transactions(transactions)
        print(f"\n Success! {count} transactions inserted.")
    else:
        print("\n No transactions found.")
