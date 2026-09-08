# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google import genai
from google.genai import errors as genai_errors
from dotenv import load_dotenv
import os

from database import init_database, insert_transactions, get_financial_summary, get_all_transactions_for_chart
from extractor import extract_pdf_statement

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL_NAME = "gemini-3.6-flash"

st.set_page_config(page_title="MoneyPilot", page_icon="💰", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0f1115; color: #e0e0e0; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .block-container { padding-top: 1rem !important; }
    h1, h2, h3 { color: #ffffff !important; font-family: 'Inter', sans-serif; margin-bottom: 0.5rem; }
    p, span, div { color: #a0a0a0 !important; }
    .metric-card { background-color: #1a1d24; border-radius: 12px; padding: 20px; border: 1px solid #2a2d35; height: 100%; }
    .metric-label { font-size: 14px; color: #8b949e; margin-bottom: 5px; }
    .metric-value { font-size: 28px; font-weight: 700; color: #ffffff; }
    .metric-delta { font-size: 14px; color: #2ecc71; margin-top: 5px; }
    [data-testid="stSidebar"] { background-color: #16191f; border-right: 1px solid #2a2d35; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 { color: #ffffff !important; }
    .stButton>button { background-color: transparent; color: #a0a0a0; border-radius: 8px; border: 1px solid #2a2d35; padding: 10px 20px; width: 100%; text-align: left; margin-bottom: 8px; }
    .stButton>button:hover { background-color: #2a2d35; color: white; }
    .stButton>button[kind="primary"] { background-color: #2563eb; color: white; border: none; text-align: center; }
    .js-plotly-plot { background-color: transparent !important; }
</style>
""", unsafe_allow_html=True)

init_database()

def generate_ai_report():
    """Generates the financial report using Gemini"""
    def query_financial_data(days: int = 30) -> dict:
        try:
            data = get_financial_summary(days)
            return {"status": "success", "data": data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    chat = client.chats.create(model=MODEL_NAME, config={"tools": [query_financial_data]})
    
    prompt = """You are MoneyPilot. Analyze financial data and provide:
    1. Cash Flow Health (Income vs Expenses, Net Savings %)
    2. Top 3 Spending Categories
    3. Anomaly Detection (>20% of expenses)
    4. Actionable Savings Plan (2 recommendations)
    
    CRITICAL FORMATTING RULES:
    - Use standard Markdown for headings and lists.
    - DO NOT use asterisks (*) for multiplication or math formulas. 
    - DO NOT use LaTeX or complex math formatting. 
    - Write numbers and percentages plainly.
    - Keep the text simple, clean, and highly readable.
    """
    
    response = chat.send_message(prompt)
    return response.text

# --- PRELOAD SAMPLE DATA ON FIRST RUN ---
if not st.session_state.get('data_loaded'):
    sample_path = "sample_statement.pdf"
    if os.path.exists(sample_path):
        with st.spinner("Loading sample financial data..."):
            transactions = extract_pdf_statement(sample_path)
            if transactions:
                insert_transactions(transactions)
                st.session_state['data_loaded'] = True
                st.session_state['ai_report'] = None
                st.session_state['force_refresh'] = True

with st.sidebar:
    st.markdown("<h2 style='color:white;'>💰 MoneyPilot</h2>", unsafe_allow_html=True)
    st.caption("Personal finance, clarified.")
    st.divider()
    
    if 'current_view' not in st.session_state: st.session_state['current_view'] = 'Overview'
    
    st.markdown("### WORKSPACE")
    for view, icon, label in [('Overview','📊','Overview'), ('Transactions','','Transactions'), ('Insights','💡','Insights')]:
        if st.button(f"{icon} {label}", use_container_width=True, type="primary" if st.session_state['current_view']==view else "secondary"):
            st.session_state['current_view'] = view
            st.rerun()

# --- MAIN LOGIC ---
if st.session_state.get('data_loaded'):
    
    # === OVERVIEW TAB ===
    if st.session_state['current_view'] == 'Overview':
        st.markdown("<h3 style='color:#8b949e; margin-bottom:8px;'>Upload a PDF statement to update your analysis.</h3>", unsafe_allow_html=True)
        col_up1, col_up2 = st.columns([4, 1])
        with col_up1:
            uploaded_file = st.file_uploader("Upload Statement", type=["pdf"], label_visibility="collapsed", key="persistent_uploader")
        with col_up2:
            if uploaded_file:
                if st.button("Analyze Finances", type="primary", use_container_width=True):
                    with open("temp_statement.pdf", "wb") as f: f.write(uploaded_file.getbuffer())
                    with st.spinner("Processing..."):
                        transactions = extract_pdf_statement("temp_statement.pdf")
                        if transactions:
                            insert_transactions(transactions)
                            st.session_state['data_loaded'] = True
                            st.session_state['ai_report'] = None
                            st.session_state['force_refresh'] = True
                            st.rerun()
                        else: st.error("No transactions found.")
        
        data = get_financial_summary(days=30)
        
        df_summary = pd.DataFrame([{"Type": k.capitalize(), "Amount": v['total']} for k, v in data['summary'].items()])
        income = df_summary[df_summary['Type']=='Income']['Amount'].sum() if 'Income' in df_summary['Type'].values else 0
        expense = df_summary[df_summary['Type']=='Expense']['Amount'].sum() if 'Expense' in df_summary['Type'].values else 0
        savings = income - expense
        rate = (savings / income * 100) if income > 0 else 0
        
        st.markdown("<h3 style='color:#8b949e;'>Your financial cockpit</h3>", unsafe_allow_html=True)
        st.markdown("<h1 style='margin-top:-10px;'>Cash-flow health</h1>", unsafe_allow_html=True)
        st.caption("A calm view of what is coming in, going out, and what you can do next.")
        st.divider()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Available Balance</div><div class='metric-value'>${savings:,.2f}</div><div class='metric-delta'>↑ {rate:.1f}% savings rate</div></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Projected Month-End</div><div class='metric-value'>${(savings * 1.2):,.2f}</div><div class='metric-delta'>Above safety floor</div></div>", unsafe_allow_html=True)
        with col3:
            score = min(100, max(0, int(rate + 20)))
            if score >= 80:
                sc_color, sc_bg, sc_text = "#10b981", "rgba(16,185,129,0.25)", "Excellent financial health"
            elif score >= 50:
                sc_color, sc_bg, sc_text = "#f59e0b", "rgba(245,158,11,0.25)", "Moderate financial health"
            else:
                sc_color, sc_bg, sc_text = "#ef4444", "rgba(239,68,68,0.25)", "Needs attention"
            st.markdown(f"<div class='metric-card' style='background:{sc_bg}; border-color:{sc_color}'><div class='metric-label'>MoneyPilot Score</div><div class='metric-value' style='color:{sc_color}'>{score}/100</div><div class='metric-delta' style='color:{sc_color}'>{sc_text}</div></div>", unsafe_allow_html=True)
        
        st.divider()
        
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.markdown("<h4 style='color:white;'>Cash in, cash out</h4>", unsafe_allow_html=True)
            st.caption("Last 12 months • Projected in lighter tone")
            
            all_txns = get_all_transactions_for_chart()
            df_all = pd.DataFrame(all_txns)
            
            if not df_all.empty and 'type' in df_all.columns:
                df_all['date'] = pd.to_datetime(df_all['date'])
                df_all['month_num'] = df_all['date'].dt.month
                df_all['month_label'] = df_all['date'].dt.strftime('%b')
                
                monthly_data = df_all.groupby(['month_num', 'month_label', 'type'])['amount'].sum().unstack(fill_value=0)
                if 'income' not in monthly_data.columns: monthly_data['income'] = 0
                if 'expense' not in monthly_data.columns: monthly_data['expense'] = 0
                monthly_data = monthly_data.sort_index(level=0)
                
                months = monthly_data.index.get_level_values('month_label').tolist()
                incomes = monthly_data['income'].tolist()
                expenses = monthly_data['expense'].tolist()
            else:
                months, incomes, expenses = ['Current'], [income], [expense]
            
            y_max = max(max(incomes), max(expenses)) * 1.25 if max(incomes) > 0 or max(expenses) > 0 else 100
            
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(x=months, y=incomes, name='Income', marker_color='#2ecc71', text=[f'${v:,.0f}<br>Income' for v in incomes], textposition='outside', textfont=dict(color='white', size=14, family="Inter")))
            fig_trend.add_trace(go.Bar(x=months, y=expenses, name='Expense', marker_color='#e74c3c', text=[f'${v:,.0f}<br>Expense' for v in expenses], textposition='outside', textfont=dict(color='white', size=12, family="Inter")))
            
            fig_trend.update_layout(
                barmode='group', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#a0a0a0', showlegend=False,
                xaxis=dict(showgrid=False, title_text='', tickangle=0, automargin=True),
                yaxis=dict(showgrid=False, zeroline=False, visible=False, range=[0, y_max]),
                margin=dict(l=0, r=0, t=40, b=0), height=300, bargap=0.3
            )
            st.plotly_chart(fig_trend, use_container_width=True)
            
            # NEW: BALANCE TREND LINE GRAPH
            st.markdown("<h4 style='color:white; margin-top:20px;'>Balance Trend</h4>", unsafe_allow_html=True)
            st.caption("Daily account balance movement")
            
            # Calculate running balance from all transactions sorted by date
            df_balance = df_all.sort_values('date').copy()
            # Reconstruct balance: start from 0, add income, subtract expense
            df_balance['net'] = df_balance.apply(lambda x: x['amount'] if x['type']=='income' else -x['amount'], axis=1)
            df_balance['running_balance'] = df_balance['net'].cumsum()
            
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=df_balance['date'], 
                y=df_balance['running_balance'],
                mode='lines+markers',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=6, color='#3b82f6'),
                name='Balance',
                hovertemplate='%{x|%b %d}: $%{y:,.2f}<extra></extra>'
            ))
            
            fig_line.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#a0a0a0', showlegend=False,
                xaxis=dict(showgrid=False, tickformat='%b %d', tickangle=45),
                yaxis=dict(showgrid=True, gridcolor='#2a2d35', zeroline=False),
                margin=dict(l=0, r=0, t=20, b=0), height=250
            )
            st.plotly_chart(fig_line, use_container_width=True)
            
        with c2:
            st.markdown("<h4 style='color:white;'>Spending habits</h4>", unsafe_allow_html=True)
            st.caption(f"September • ${expense:,.0f} total")
            df_cats = pd.DataFrame(data['top_categories'])
            if not df_cats.empty:
                fig_pie = px.pie(df_cats, values='total', names='category', hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_traces(textposition='inside', texttemplate='%{label}<br>$%{value:,.0f}<br>%{percent:.1%}', insidetextfont=dict(color='white', size=11))
                fig_pie.add_annotation(text=f"${expense:,.0f}<br><span style='font-size:12px'>spent</span>", showarrow=False, font=dict(size=16, color="white"))
                fig_pie.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#a0a0a0', showlegend=False, margin=dict(t=0,b=0,l=0,r=0))
                st.plotly_chart(fig_pie, use_container_width=True)

    # === INSIGHTS TAB (CLEAN - NO UPLOAD BAR) ===
    elif st.session_state['current_view'] == 'Insights':
        st.markdown("<h4 style='color:white;'>💡 AI Financial Recommendations</h4>", unsafe_allow_html=True)
        st.caption("Generated by MoneyPilot AI based on your real transaction data.")
        
        if st.session_state.get('ai_report') is None or st.session_state.get('force_refresh'):
            with st.container(border=True):
                with st.spinner("MoneyPilot is analyzing your finances..."):
                    try:
                        report_md = generate_ai_report()
                        st.session_state['ai_report'] = report_md
                        st.session_state['force_refresh'] = False
                        st.markdown(report_md)
                    except genai_errors.ServerError:
                        st.warning("️ **AI Service Temporarily Unavailable**\n\nGoogle's servers are currently experiencing high demand. Your data is safely stored in ClickHouse.")
                    except Exception as e:
                        st.error(f"❌ **Error:** {str(e)}")
        else:
            with st.container(border=True):
                st.markdown(st.session_state['ai_report'])
                
        if st.button(" Regenerate Report", type="secondary"):
            st.session_state['force_refresh'] = True
            st.rerun()
    
    # === TRANSACTIONS TAB (FIXED RENDERING) ===
    elif st.session_state['current_view'] == 'Transactions':
        st.markdown("<h4 style='color:white;'>Recent Transactions</h4>", unsafe_allow_html=True)
        
        data = get_financial_summary(days=365) 
        df_recent = pd.DataFrame(data['recent_transactions'])
        
        if not df_recent.empty and 'date' in df_recent.columns:
            df_recent['date'] = pd.to_datetime(df_recent['date'], errors='coerce')
            df_recent = df_recent.dropna(subset=['date'])
            
            df_display = df_recent[['date', 'merchant', 'amount', 'category', 'type']].copy()
            df_display['date'] = df_display['date'].dt.strftime('%Y-%m-%d')
            df_display['amount'] = df_display['amount'].apply(lambda x: f"${x:,.2f}")
            df_display.columns = ['Date', 'Merchant', 'Amount', 'Category', 'Type']
            
            st.dataframe(
                df_display, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Date": st.column_config.TextColumn("Date"),
                    "Merchant": st.column_config.TextColumn("Merchant"),
                    "Amount": st.column_config.TextColumn("Amount"),
                    "Category": st.column_config.TextColumn("Category"),
                    "Type": st.column_config.TextColumn("Type")
                }
            )
        else:
            st.info("No valid transactions found. Please upload a statement with valid dates.")

else:
    # WELCOME SCREEN (Should rarely appear now due to preload)
    st.markdown("<div style='text-align:center; padding-top:80px;'>", unsafe_allow_html=True)
    st.markdown("<h2>Welcome to MoneyPilot</h2>", unsafe_allow_html=True)
    st.caption("Loading sample data... If this persists, please upload a PDF.")
    st.markdown("</div>", unsafe_allow_html=True)