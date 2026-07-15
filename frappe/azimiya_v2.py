import frappe
import json

def get_azimiya():
    # Get employees of عظیمیه
    emps = frappe.db.sql("SELECT name, employee_name FROM tabEmployee WHERE company LIKE '%عظ%'", as_dict=True)
    
    if not emps:
        return {"error": "No employees found"}
    
    result = []
    for emp in emps:
        checkins = frappe.db.sql(
            "SELECT `time`, `log_type`, `device_id` FROM `tabEmployee Checkin` WHERE employee = %s ORDER BY `time` DESC LIMIT 10",
            (emp['name'],), as_dict=True
        )
        result.append({
            'name': emp['employee_name'],
            'id': emp['name'],
            'checkin_count': len(checkins),
            'checkins': [{'time': str(c['time']), 'type': c['log_type'], 'device': c.get('device_id', '')} for c in checkins]
        })
    
    return {"employees_found": len(emps), "data": result}

print(json.dumps(get_azimiya(), ensure_ascii=False))
