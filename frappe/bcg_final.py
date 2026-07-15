#!/usr/bin/env python3.12
"""BCG Matrix Analysis - Direct DB via frappe.db.sql"""
import json
import sys

# This script runs inside Frappe context via bench execute
# It uses direct SQL to avoid API overhead

import frappe
from frappe.utils import getdate
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO
import os

def run_bcg():
    start_date = "2026-03-12"  # 1 Khordad
    end_date = "2026-06-15"    # Today
    
    # Direct SQL - much faster than API
    print("Fetching data via SQL...", file=sys.stderr)
    
    items = frappe.db.sql("""
        SELECT 
            sii.item_code,
            SUM(sii.stock_qty) as total_qty,
            SUM(sii.amount) as total_amount,
            COUNT(DISTINCT sii.parent) as invoice_count
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE si.posting_date BETWEEN %s AND %s
            AND si.docstatus = 1
        GROUP BY sii.item_code
        ORDER BY total_amount DESC
    """, (start_date, end_date), as_dict=True)
    
    print(f"Found {len(items)} unique items", file=sys.stderr)
    
    if not items:
        return {"error": "No items found"}
    
    # BCG Analysis
    total_revenue = sum(item['total_amount'] for item in items)
    total_qty = sum(item['total_qty'] for item in items)
    
    avg_revenue = total_revenue / len(items) if items else 0
    avg_qty = total_qty / len(items) if items else 0
    
    # Classify items
    stars = []
    cash_cows = []
    question_marks = []
    dogs = []
    
    for item in items:
        high_revenue = item['total_amount'] >= avg_revenue
        high_qty = item['total_qty'] >= avg_qty
        
        if high_revenue and high_qty:
            stars.append(item)
        elif high_revenue and not high_qty:
            cash_cows.append(item)
        elif not high_revenue and high_qty:
            question_marks.append(item)
        else:
            dogs.append(item)
    
    # Create Excel
    wb = openpyxl.Workbook()
    
    # Styles
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    star_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    cash_cow_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    question_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    dog_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
    
    # Sheet 1: BCG Summary
    ws1 = wb.active
    ws1.title = "BCG Matrix"
    
    ws1.merge_cells('A1:F1')
    ws1['A1'] = "BCG Matrix Analysis - 1 Khordad to 25 Khordad 1405"
    ws1['A1'].font = Font(bold=True, size=14, color="2F5496")
    ws1['A1'].alignment = Alignment(horizontal='center')
    
    headers = ["Category", "Item Code", "Total Qty", "Total Amount (Toman)", "% Revenue", "% Qty"]
    for col, header in enumerate(headers, 1):
        cell = ws1.cell(row=3, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = border
    
    row = 4
    for category, items_list, fill in [
        ("⭐ Stars", stars, star_fill),
        ("🐄 Cash Cows", cash_cows, cash_cow_fill),
        ("❓ Question Marks", question_marks, question_fill),
        ("🐕 Dogs", dogs, dog_fill)
    ]:
        for item in items_list:
            pct_revenue = (item['total_amount'] / total_revenue * 100) if total_revenue else 0
            pct_qty = (item['total_qty'] / total_qty * 100) if total_qty else 0
            
            ws1.cell(row=row, column=1, value=category).fill = fill
            ws1.cell(row=row, column=1).border = border
            ws1.cell(row=row, column=2, value=item['item_code']).border = border
            ws1.cell(row=row, column=3, value=round(item['total_qty'], 2)).border = border
            ws1.cell(row=row, column=3).alignment = Alignment(horizontal='center')
            ws1.cell(row=row, column=4, value=round(item['total_amount'], 0)).border = border
            ws1.cell(row=row, column=4).number_format = '#,##0'
            ws1.cell(row=row, column=5, value=f"{pct_revenue:.1f}%").border = border
            ws1.cell(row=row, column=5).alignment = Alignment(horizontal='center')
            ws1.cell(row=row, column=6, value=f"{pct_qty:.1f}%").border = border
            ws1.cell(row=row, column=6).alignment = Alignment(horizontal='center')
            row += 1
    
    # Auto-width
    for col in range(1, 7):
        ws1.column_dimensions[get_column_letter(col)].width = 20
    
    # Sheet 2: Summary Stats
    ws2 = wb.create_sheet("Summary")
    
    ws2.merge_cells('A1:C1')
    ws2['A1'] = "Summary Statistics"
    ws2['A1'].font = Font(bold=True, size=14, color="2F5496")
    
    stats = [
        ("Total Unique Items", len(items)),
        ("Total Revenue (Toman)", f"{total_revenue:,.0f}"),
        ("Total Quantity", f"{total_qty:,.0f}"),
        ("⭐ Stars", len(stars)),
        ("🐄 Cash Cows", len(cash_cows)),
        ("❓ Question Marks", len(question_marks)),
        ("🐕 Dogs", len(dogs)),
    ]
    
    for i, (label, value) in enumerate(stats, 3):
        ws2.cell(row=i, column=1, value=label).font = Font(bold=True)
        ws2.cell(row=i, column=2, value=value)
        ws2.column_dimensions['A'].width = 25
        ws2.column_dimensions['B'].width = 20
    
    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Save to Frappe File doctype
    file_name = f"BCG_Analysis_{start_date}_to_{end_date}.xlsx"
    
    # Check if file already exists
    existing = frappe.db.get_value("File", {"file_name": file_name}, "name")
    if existing:
        frappe.delete_doc("File", existing)
    
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "content": output.getvalue(),
        "is_private": 0
    })
    file_doc.insert(ignore_permissions=True)
    frappe.db.commit()
    
    file_url = f"https://dehati.ir{file_doc.file_url}"
    print(f"File saved: {file_url}", file=sys.stderr)
    
    return {
        "success": True,
        "file_url": file_url,
        "total_items": len(items),
        "total_revenue": total_revenue,
        "stars": len(stars),
        "cash_cows": len(cash_cows),
        "question_marks": len(question_marks),
        "dogs": len(dogs)
    }

# Run
result = run_bcg()
print(json.dumps(result))
