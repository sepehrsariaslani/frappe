import frappe
import json

def get_checkins():
    result = {}
    emps = frappe.db.sql("SELECT name, employee_name FROM tabEmployee WHERE company = 'عظيميه'", as_dict=True)
    
    for emp in emps:
        checkins = frappe.db.sql(
            "SELECT time, log_type, device_id FROM tabEmployee Checkin WHERE employee = %s ORDER BY time DESC",
            (emp['name'],), as_dict=True
        )
        result[emp['employee_name']] = {
            'employee_id': emp['name'],
            'checkin_count': len(checkins),
            'recent_checkins': [
                {'time': str(c['time']), 'log_type': c['log_type'], 'device': c.get('device_id', '')}
                for c in checkins[:10]
            ]
        }
    
    with open('/tmp/checkin_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return {"success": True, "employees": len(emps), "file": "/tmp/checkin_result.json"}

result = get_checkins()
print(json.dumps(result))
