import frappe
import json

def debug():
    # Check what companies exist
    companies = frappe.db.sql("SELECT DISTINCT company FROM tabEmployee WHERE company IS NOT NULL", as_dict=True)
    
    # Check a specific employee
    emp = frappe.db.sql("SELECT name, employee_name, company FROM tabEmployee LIMIT 3", as_dict=True)
    
    return {
        "companies": [c['company'] for c in companies],
        "sample_employees": emp
    }

result = debug()
print(json.dumps(result, ensure_ascii=False))
