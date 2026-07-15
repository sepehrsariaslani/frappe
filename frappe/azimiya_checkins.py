import frappe
import json

def get_azimiya():
    # Find exact company name
    companies = frappe.db.sql("SELECT DISTINCT company FROM tabEmployee WHERE company LIKE '%عظ%'", as_dict=True)
    
    # Get employees of that company
    if companies:
        company_name = companies[0]['company']
        emps = frappe.db.sql("SELECT name, employee_name FROM tabEmployee WHERE company = %s", (company_name,), as_dict=True)
        
        # Get checkins for first 3 employees
        result = []
        for emp in emps[:3]:
            checkins = frappe.db.sql(
                "SELECT time, log_type FROM tabEmployee Checkin WHERE employee = %s ORDER BY time DESC LIMIT 5",
                (emp['name'],), as_dict=True
            )
            result.append({
                'name': emp['employee_name'],
                'id': emp['name'],
                'checkins': [{'time': str(c['time']), 'type': c['log_type']} for c in checkins]
            })
        
        return {"company": company_name, "employees": emps[:5], "checkins_sample": result}
    
    return {"error": "No company found"}

print(json.dumps(get_azimiya(), ensure_ascii=False))
