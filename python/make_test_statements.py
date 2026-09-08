# python/make_test_statements.py
"""Generates multi-month demo statements (PDF + CSV). Usage:
   pip install reportlab
   python make_test_statements.py
"""
from __future__ import annotations
import csv
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

OUT = Path(__file__).resolve().parent / "sample_data"
OUT.mkdir(parents=True, exist_ok=True)

def money(v: float) -> str:
    return f"{'+' if v >= 0 else '-'}{abs(v):,.2f}"

def build(filename: str, title: str, rows: list[tuple[str, str, float]]) -> None:
    # PDF
    data = [["Date", "Description", "Amount", "Balance"]]
    balance = 2500.00
    for date, desc, amount in rows:
        balance += amount
        data.append([date, desc, money(amount), f"{balance:,.2f}"])
    table = Table(data, colWidths=[90, 260, 90, 90], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7f7f7f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f5f5dc"), colors.white]),
        ("ALIGN", (2, 1), (3, -1), "RIGHT"),
    ]))
    SimpleDocTemplate(str(OUT / filename), pagesize=letter, title=title).build(
        [Paragraph(title, getSampleStyleSheet()["Title"]), Spacer(1, 12), table])
    # CSV twin (uploader accepts .csv too)
    with open(OUT / filename.replace(".pdf", ".csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["Date", "Description", "Amount", "Balance"])
        b = 2500.00
        for date, desc, amount in rows:
            b += amount; w.writerow([date, desc, f"{amount:.2f}", f"{b:.2f}"])
    print(f"[OK] wrote {filename} (+csv)")

# ---------- SCENARIO 1: SALARIED EMPLOYEE (steady income, two spikes) ----------
emp: list[tuple[str, str, float]] = []
groceries = [342.18, 356.40, 388.92, 481.05, 365.77, 372.64]
gas       = [45.00, 52.30, 48.75, 55.10, 44.20, 50.05]
electric  = [86.40, 92.10, 104.75, 118.30, 111.05, 96.20]
coffee    = [6.95, 8.50, 5.75, 9.99, 7.45, 6.25]
target    = [67.32, 84.10, 72.55, 91.40, 138.87, 78.15]
for i, m in enumerate(["04", "05", "06", "07", "08", "09"]):
    emp += [
        (f"2026-{m}-01", "Monthly Salary Deposit", 4200.00),
        (f"2026-{m}-03", "Rent Payment", -1480.00),
        (f"2026-{m}-05", "Whole Foods Market", -groceries[i]),
        (f"2026-{m}-08", "Shell Gas Station", -gas[i]),
        (f"2026-{m}-12", "Netflix Subscription", -15.99),
        (f"2026-{m}-14", "Electric Bill", -electric[i]),
        (f"2026-{m}-18", "Starbucks", -coffee[i]),
        (f"2026-{m}-22", "Target", -target[i]),
    ]
    if m == "06": emp.append(("2026-06-15", "Costco Bulk Groceries", -862.40))   # grocery spike
    if m == "08": emp.append(("2026-08-16", "Best Buy New Laptop", -2199.00))    # shopping spike
build("employee_statement.pdf", "MoneyPilot Bank - Statement Apr-Sep 2026 (Salaried)", emp)

# ---------- SCENARIO 2: PIZZA SHOP OWNER (variable income & costs) ----------
piz: list[tuple[str, str, float]] = []
sales    = [7600.00, 9300.00, 11200.00, 10400.00, 12600.00, 11800.00]
electric = [312.40, 348.75, 402.10, 455.60, 471.25, 398.90]
wages    = [3200.00, 3350.00, 3600.00, 3600.00, 3900.00, 3750.00]
dough    = [610.20, 705.45, 822.10, 780.35, 903.60, 861.15]
sauce    = [240.50, 288.90, 341.20, 318.75, 377.40, 355.05]
meat     = [505.60, 610.25, 722.80, 688.15, 804.90, 762.30]
fees     = [180.40, 221.15, 266.50, 247.30, 299.75, 280.60]
for i, m in enumerate(["04", "05", "06", "07", "08", "09"]):
    mid, end = round(sales[i] * 0.55, 2), round(sales[i] * 0.45, 2)
    piz += [
        (f"2026-{m}-01", "Rent Payment", -2200.00),
        (f"2026-{m}-02", "City Electricity Bill", -electric[i]),
        (f"2026-{m}-05", "Staff Wages Payroll", -wages[i]),
        (f"2026-{m}-07", "Dough & Flour Supplier", -dough[i]),
        (f"2026-{m}-10", "Tomato Sauce Supplier", -sauce[i]),
        (f"2026-{m}-12", "Meat & Cheese Supplier", -meat[i]),
        (f"2026-{m}-15", "Card Sales Deposit", mid),
        (f"2026-{m}-20", "Delivery Platform Fees", -fees[i]),
        (f"2026-{m}-28", "Cash Sales Deposit", end),
    ]
    if m == "05": piz.append(("2026-05-20", "Pizza Oven Repair", -1750.00))
    if m == "07": piz.append(("2026-07-22", "Marketing Ads Campaign", -480.00))
    if m == "09": piz.append(("2026-09-18", "New Signage Install", -640.00))
build("pizza_owner_statement.pdf", "MoneyPilot Bank - Statement Apr-Sep 2026 (Bella Pizza LLC)", piz)