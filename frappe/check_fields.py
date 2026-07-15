#!/usr/bin/env python3
"""Check Sales Invoice fields"""
import frappe
frappe.init(site='dehati.ir', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()

# Get all fields for Sales Invoice
fields = frappe.get_meta("Sales Invoice").fields
print("=== All custom fields in Sales Invoice ===")
for f in fields:
    if f.fieldname and ('cash' in f.fieldname.lower() or 'sepidar' in f.fieldname.lower() or 'box' in f.fieldname.lower() or 'fund' in f.fieldname.lower()):
        print(f"  {f.fieldname} ({f.fieldtype}) - {f.label}")

print("\n=== All fields containing 'cash' or 'sepidar' ===")
for f in fields:
    if f.fieldname and ('cash' in f.fieldname.lower() or 'sepidar' in f.fieldname.lower()):
        print(f"  {f.fieldname} | type={f.fieldtype} | label={f.label}")
