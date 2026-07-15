import frappe
import json

results = frappe.db.sql("""
    SELECT si.name as invoice, si.grand_total, sii.item_code,
           COALESCE(i.item_name, sii.item_code) as item_name,
           sii.stock_qty, sii.amount
    FROM `tabSales Invoice` si
    INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
    LEFT JOIN `tabItem` i ON i.name = sii.item_code
    WHERE si.posting_date = '2026-06-18'
      AND si.docstatus = 1
      AND (si.customer = %s OR si.customer = %s)
    ORDER BY si.name
""", ("ترنج", "ترنج - 1"), as_dict=True)

print(json.dumps(results, ensure_ascii=False))
