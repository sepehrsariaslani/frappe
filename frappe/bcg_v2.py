#!/usr/bin/env python3.12
"""BCG Matrix Analysis v2 - With item names and separate sheets per category"""
import json
import sys

import frappe
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO

def run_bcg():
    start_date = "2026-03-12"  # 1 Khordad
    end_date = "2026-06-15"    # Today

    print("Step 1: Fetching sales data with item names...", file=sys.stderr)

    # Get item sales data with names
    items = frappe.db.sql("""
        SELECT 
            sii.item_code,
            COALESCE(i.item_name, sii.item_code) as item_name,
            SUM(sii.stock_qty) as total_qty,
            SUM(sii.amount) as total_amount,
            COUNT(DISTINCT sii.parent) as invoice_count
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
        LEFT JOIN `tabItem` i ON i.name = sii.item_code
        WHERE si.posting_date BETWEEN %s AND %s
            AND si.docstatus = 1
        GROUP BY sii.item_code, COALESCE(i.item_name, sii.item_code)
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

    stars, cash_cows, question_marks, dogs = [], [], [], []

    for item in items:
        high_rev = item['total_amount'] >= avg_revenue
        high_qty = item['total_qty'] >= avg_qty
        if high_rev and high_qty:
            stars.append(item)
        elif high_rev and not high_qty:
            cash_cows.append(item)
        elif not high_rev and high_qty:
            question_marks.append(item)
        else:
            dogs.append(item)

    # Styles
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    star_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    cash_cow_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    question_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    dog_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

    def write_category_sheet(ws, category_name, items_list, fill, total_revenue, total_qty):
        ws.merge_cells('A1:G1')
        ws['A1'] = category_name
        ws['A1'].font = Font(bold=True, size=14, color="2F5496")
        ws['A1'].alignment = Alignment(horizontal='center')

        headers = ["#", "کد کالا", "نام کالا", "تعداد", "مبلغ (تومان)", "% فروش", "% تعداد"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = border

        for idx, item in enumerate(items_list, 1):
            row = idx + 3
            pct_rev = (item['total_amount'] / total_revenue * 100) if total_revenue else 0
            pct_qty = (item['total_qty'] / total_qty * 100) if total_qty else 0

            ws.cell(row=row, column=1, value=idx).border = border
            ws.cell(row=row, column=1).alignment = Alignment(horizontal='center')
            ws.cell(row=row, column=1).fill = fill

            ws.cell(row=row, column=2, value=item['item_code']).border = border
            ws.cell(row=row, column=2).fill = fill

            ws.cell(row=row, column=3, value=item['item_name']).border = border
            ws.cell(row=row, column=3).fill = fill

            ws.cell(row=row, column=4, value=round(item['total_qty'], 2)).border = border
            ws.cell(row=row, column=4).alignment = Alignment(horizontal='center')
            ws.cell(row=row, column=4).fill = fill

            ws.cell(row=row, column=5, value=round(item['total_amount'], 0)).border = border
            ws.cell(row=row, column=5).number_format = '#,##0'
            ws.cell(row=row, column=5).fill = fill

            ws.cell(row=row, column=6, value=f"{pct_rev:.1f}%").border = border
            ws.cell(row=row, column=6).alignment = Alignment(horizontal='center')
            ws.cell(row=row, column=6).fill = fill

            ws.cell(row=row, column=7, value=f"{pct_qty:.1f}%").border = border
            ws.cell(row=row, column=7).alignment = Alignment(horizontal='center')
            ws.cell(row=row, column=7).fill = fill

        # Auto-width
        widths = [5, 15, 35, 12, 18, 10, 10]
        for col, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(col)].width = w

    # Create Excel
    wb = openpyxl.Workbook()

    # Sheet 1: Summary (all items)
    ws_summary = wb.active
    ws_summary.title = "خلاصه BCG"
    ws_summary.merge_cells('A1:G1')
    ws_summary['A1'] = "تحلیل ماتریس BCG - از ۱ خرداد تا ۲۵ خرداد ۱۴۰۵"
    ws_summary['A1'].font = Font(bold=True, size=14, color="2F5496")
    ws_summary['A1'].alignment = Alignment(horizontal='center')

    headers = ["دسته", "کد کالا", "نام کالا", "تعداد", "مبلغ (تومان)", "% فروش", "% تعداد"]
    for col, header in enumerate(headers, 1):
        cell = ws_summary.cell(row=3, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = border

    row = 4
    for category, items_list, fill, emoji in [
        ("ستاره ⭐", stars, star_fill, "⭐"),
        ("گاو پولی 🐄", cash_cows, cash_cow_fill, "🐄"),
        ("علامت سؤال ❓", question_marks, question_fill, "❓"),
        ("سگ 🐕", dogs, dog_fill, "🐕")
    ]:
        for item in items_list:
            pct_rev = (item['total_amount'] / total_revenue * 100) if total_revenue else 0
            pct_qty = (item['total_qty'] / total_qty * 100) if total_qty else 0

            ws_summary.cell(row=row, column=1, value=category).fill = fill
            ws_summary.cell(row=row, column=1).border = border
            ws_summary.cell(row=row, column=2, value=item['item_code']).border = border
            ws_summary.cell(row=row, column=2).fill = fill
            ws_summary.cell(row=row, column=3, value=item['item_name']).border = border
            ws_summary.cell(row=row, column=3).fill = fill
            ws_summary.cell(row=row, column=4, value=round(item['total_qty'], 2)).border = border
            ws_summary.cell(row=row, column=4).alignment = Alignment(horizontal='center')
            ws_summary.cell(row=row, column=4).fill = fill
            ws_summary.cell(row=row, column=5, value=round(item['total_amount'], 0)).border = border
            ws_summary.cell(row=row, column=5).number_format = '#,##0'
            ws_summary.cell(row=row, column=5).fill = fill
            ws_summary.cell(row=row, column=6, value=f"{pct_rev:.1f}%").border = border
            ws_summary.cell(row=row, column=6).alignment = Alignment(horizontal='center')
            ws_summary.cell(row=row, column=6).fill = fill
            ws_summary.cell(row=row, column=7, value=f"{pct_qty:.1f}%").border = border
            ws_summary.cell(row=row, column=7).alignment = Alignment(horizontal='center')
            ws_summary.cell(row=row, column=7).fill = fill
            row += 1

    widths = [15, 15, 35, 12, 18, 10, 10]
    for col, w in enumerate(widths, 1):
        ws_summary.column_dimensions[get_column_letter(col)].width = w

    # Sheet 2: Stats
    ws_stats = wb.create_sheet("آمار کلی")
    ws_stats.merge_cells('A1:C1')
    ws_stats['A1'] = "آمار کلی فروش"
    ws_stats['A1'].font = Font(bold=True, size=14, color="2F5496")

    stats = [
        ("تعداد کل کالاهای یکتا", len(items)),
        ("کل فروش (تومان)", f"{total_revenue:,.0f}"),
        ("کل تعداد", f"{total_qty:,.0f}"),
        ("میانگین فروش به ازای هر کالا", f"{avg_revenue:,.0f}"),
        ("میانگین تعداد به ازای هر کالا", f"{avg_qty:,.0f}"),
        ("", ""),
        ("⭐ ستاره‌ها (فروش بالا + حجم بالا)", len(stars)),
        ("🐄 گاوهای پولی (فروش بالا + حجم کم)", len(cash_cows)),
        ("❓ علامت سؤال (فروش کم + حجم بالا)", len(question_marks)),
        ("🐕 سگ‌ها (فروش کم + حجم کم)", len(dogs)),
    ]

    for i, (label, value) in enumerate(stats, 3):
        ws_stats.cell(row=i, column=1, value=label).font = Font(bold=True)
        ws_stats.cell(row=i, column=2, value=value)
    ws_stats.column_dimensions['A'].width = 40
    ws_stats.column_dimensions['B'].width = 25

    # Sheet 3: Stars
    if stars:
        ws_stars = wb.create_sheet("⭐ ستاره‌ها")
        write_category_sheet(ws_stars, "⭐ ستاره‌ها - فروش بالا + حجم بالا", stars, star_fill, total_revenue, total_qty)

    # Sheet 4: Cash Cows
    if cash_cows:
        ws_cc = wb.create_sheet("🐄 گاوهای پولی")
        write_category_sheet(ws_cc, "🐄 گاوهای پولی - فروش بالا + حجم کم", cash_cows, cash_cow_fill, total_revenue, total_qty)

    # Sheet 5: Question Marks
    if question_marks:
        ws_qm = wb.create_sheet("❓ علامت سؤال")
        write_category_sheet(ws_qm, "❓ علامت سؤال - فروش کم + حجم بالا", question_marks, question_fill, total_revenue, total_qty)

    # Sheet 6: Dogs
    if dogs:
        ws_dogs = wb.create_sheet("🐕 سگ‌ها")
        write_category_sheet(ws_dogs, "🐕 سگ‌ها - فروش کم + حجم کم", dogs, dog_fill, total_revenue, total_qty)

    # Save
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    file_name = f"BCG_Analysis_v2_{start_date}_to_{end_date}.xlsx"
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

    # Print top items for each category
    print("\n=== TOP STARS ===", file=sys.stderr)
    for item in stars[:5]:
        print(f"  {item['item_code']} | {item['item_name']} | Qty: {item['total_qty']:.0f} | Amount: {item['total_amount']:,.0f}", file=sys.stderr)

    print("\n=== TOP CASH COWS ===", file=sys.stderr)
    for item in cash_cows[:5]:
        print(f"  {item['item_code']} | {item['item_name']} | Qty: {item['total_qty']:.0f} | Amount: {item['total_amount']:,.0f}", file=sys.stderr)

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

result = run_bcg()
print(json.dumps(result))
