import json
import frappe

def run_query():
    results = frappe.db.sql("""
        SELECT si.name as invoice, si.grand_total, sii.item_code,
               COALESCE(i.item_name, sii.item_code) as item_name,
               sii.stock_qty, sii.amount
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        LEFT JOIN `tabItem` i ON i.name = sii.item_code
        WHERE si.posting_date = '2026-06-17'
          AND si.docstatus = 1
          AND si.customer IN ('Toranj', 'Toranj - 1')
        ORDER BY si.name
    """, as_dict=True)
    print(json.dumps(results, ensure_ascii=False, default=str))
