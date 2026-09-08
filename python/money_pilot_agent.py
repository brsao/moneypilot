# money_pilot_agent.py
import os
import traceback
from google import genai
from dotenv import load_dotenv
from database import get_financial_summary

load_dotenv()

# Verify credentials are loaded
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("❌ GOOGLE_API_KEY missing from .env")
if not os.getenv("CLICKHOUSE_HOST"):
    raise ValueError("❌ CLICKHOUSE_HOST missing from .env")

print(f" Google API Key: {os.getenv('GOOGLE_API_KEY')[:10]}...")
print(f"🗄️ ClickHouse Host: {os.getenv('CLICKHOUSE_HOST')}")
print(f"👤 ClickHouse User: {os.getenv('CLICKHOUSE_USER', 'default')}")
print()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL_NAME = "gemini-3.6-flash"

def query_financial_data(days: int = 30) -> dict:
    """
    Tool: Queries ClickHouse for financial analytics.
    Includes robust error handling and logging.
    """
    print(f"🔍 [TOOL] Querying ClickHouse for last {days} days...")
    try:
        data = get_financial_summary(days)
        print(f"✅ [TOOL] Successfully retrieved {len(data.get('recent_transactions', []))} recent transactions")
        return {"status": "success", "data": data}
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"❌ [TOOL] Database query failed!")
        print(f"   Error: {error_msg}")
        print(f"   Traceback:\n{traceback.format_exc()}")
        return {"status": "error", "message": error_msg}

def main():
    print(" Starting MoneyPilot AI Financial Manager...\n")
    
    chat = client.chats.create(
        model=MODEL_NAME,
        config={"tools": [query_financial_data]}
    )

    prompt = """
    You are MoneyPilot, an expert AI financial operations manager.
    
    TASK:
    1. Call `query_financial_data(days=30)` to fetch financial data.
    2. If status is "error", report the exact error message to the user and STOP. Do NOT generate a fake report.
    3. If status is "success", analyze the data and generate a Financial Health Report with these sections:
       - 💰 Cash Flow Health (Income vs Expenses, Net Savings, Savings Rate %)
       -  Spending Habits (Top 3 categories with amounts)
       - 🚩 Anomaly Detection (Flag transactions > 20% of total expenses)
       - 💡 Actionable Savings Plan (2 specific recommendations with estimated savings)
    
    Use EXACT numbers from the database. Be professional and actionable.
    """

    print(" Agent analyzing financial data...\n")
    
    try:
        response = chat.send_message(prompt)
        
        print("\n" + "="*70)
        print("💰 MONEYPILOT FINANCIAL HEALTH REPORT")
        print("="*70)
        print(response.text)
        print("="*70)
        
    except Exception as e:
        print(f"❌ Agent Error: {e}")
        traceback.print_exc()

# Add this function at the bottom of money_pilot_agent.py
def generate_report_text():
    """Returns the AI report as a string for the UI"""
    chat = client.chats.create(model=MODEL_NAME, config={"tools": [query_financial_data]})
    
    prompt = """
    You are MoneyPilot, an expert AI financial operations manager.
    
    TASK:
    1. Call `query_financial_data(days=30)` to fetch financial data.
    2. If status is "error", return ONLY the error message.
    3. If status is "success", analyze the data and generate a Financial Health Report with these sections:
       - 💰 Cash Flow Health (Income vs Expenses, Net Savings, Savings Rate %)
       - 📊 Spending Habits (Top 3 categories with amounts)
       - 🚩 Anomaly Detection (Flag transactions > 20% of total expenses)
       - 💡 Actionable Savings Plan (2 specific recommendations with estimated savings)
    
    Use EXACT numbers from the database. Be professional and actionable.
    Format everything in clean Markdown.
    """

    response = chat.send_message(prompt)
    return response.text

if __name__ == "__main__":
    main()