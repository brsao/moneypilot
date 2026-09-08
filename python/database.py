# database.py
import clickhouse_connect
import os
from dotenv import load_dotenv
from datetime import date

load_dotenv()

def get_client():
    """Connects to ClickHouse Cloud securely"""
    return clickhouse_connect.get_client(
        host=os.getenv("CLICKHOUSE_HOST"),
        port=int(os.getenv("CLICKHOUSE_PORT", 8443)),
        secure=True,
        username=os.getenv("CLICKHOUSE_USER", "default"),
        password=os.getenv("CLICKHOUSE_PASSWORD")
    )

def init_database():
    """Creates the transactions table"""
    client = get_client()
    client.command("""
        CREATE TABLE IF NOT EXISTS default.transactions (
            id UUID DEFAULT generateUUIDv4(),
            date Date,
            merchant String,
            amount Float64,
            category String,
            transaction_type String,
            inserted_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (date, merchant)
    """)
    print("✅ ClickHouse table initialized")

def insert_transactions(transactions: list):
    """Inserts extracted transactions into ClickHouse"""
    client = get_client()
    columns = ['date', 'merchant', 'amount', 'category', 'transaction_type']
    rows = []
    
    income_keywords = ["salary", "deposit", "refund", "rebate", "credit", "interest"]
    
    for t in transactions:
        tx_type = "income" if any(k in t['description'].lower() for k in income_keywords) else "expense"
        amount = abs(float(t['amount']))
        date_obj = t['date'] if isinstance(t['date'], date) else date.fromisoformat(str(t['date']))
        rows.append((date_obj, t['merchant'], amount, t['category'], tx_type))
    
    if rows:
        client.insert('default.transactions', rows, column_names=columns)
        result = client.query("SELECT count() as cnt FROM default.transactions")
        count = list(result.named_results())[0]['cnt']
        print(f"✅ Inserted {len(rows)} rows. Total: {count}")
        return len(rows)
    return 0

def get_financial_summary(days: int = 30) -> dict:
    """Queries ClickHouse for financial analytics"""
    client = get_client()
    
    # Summary
    summary_query = f"""
        SELECT transaction_type, sum(amount) as total, count() as count
        FROM default.transactions 
        WHERE date >= today() - {days}
        GROUP BY transaction_type
    """
    result = client.query(summary_query)
    summary = {r['transaction_type']: {'total': r['total'], 'count': r['count']} for r in result.named_results()}
    
    # Categories
    category_query = f"""
        SELECT category, sum(amount) as total_spent, count() as count
        FROM default.transactions 
        WHERE transaction_type = 'expense' AND date >= today() - {days}
        GROUP BY category ORDER BY total_spent DESC LIMIT 5
    """
    result = client.query(category_query)
    top_categories = [{"category": r['category'], "total": r['total_spent'], "count": r['count']} for r in result.named_results()]
    
    # Recent Transactions - STRICT FILTERING
    recent_query = f"""
        SELECT date, merchant, amount, category, transaction_type
        FROM default.transactions 
        WHERE transaction_type IN ('income', 'expense')
          AND date >= today() - {days}
        ORDER BY date DESC 
        LIMIT 50
    """
    result = client.query(recent_query)
    
    recent = []
    for r in result.named_results():
        try:
            recent.append({
                "date": str(r['date']),
                "merchant": str(r['merchant']),
                "amount": float(r['amount']),
                "category": str(r['category']),
                "type": str(r['transaction_type'])
            })
        except (ValueError, TypeError):
            continue
            
    return {"summary": summary, "top_categories": top_categories, "recent_transactions": recent}

def get_all_transactions_for_chart() -> list:
    """Fetches ALL transactions for multi-month chart rendering"""
    client = get_client()
    query = """
        SELECT date, merchant, amount, category, transaction_type
        FROM default.transactions 
        WHERE transaction_type IN ('income', 'expense')
        ORDER BY date DESC
    """
    result = client.query(query)
    return [
        {
            "date": str(row['date']),
            "merchant": row['merchant'],
            "amount": row['amount'],
            "category": row['category'],
            "type": row['transaction_type']
        }
        for row in result.named_results()
    ]