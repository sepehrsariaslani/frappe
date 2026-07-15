import frappe
import json
from datetime import datetime

def analyze_employee(emp_name_filter, start_date="2026-03-12"):
    """Analyze attendance for a specific employee using raw checkin data"""
    
    # Get employee
    emps = frappe.db.sql("SELECT name, employee_name FROM tabEmployee WHERE employee_name LIKE %s", (f"%{emp_name_filter}%",), as_dict=True)
    
    if not emps:
        return {"error": f"No employee found matching {emp_name_filter}"}
    
    emp = emps[0]
    
    # Get all checkins
    checkins = frappe.db.sql(
        "SELECT `time`, log_type FROM `tabEmployee Checkin` WHERE employee = %s AND `time` >= %s ORDER BY `time`",
        (emp['name'], start_date), as_dict=True
    )
    
    if not checkins:
        return {"error": f"No checkin records found for {emp['employee_name']}"}
    
    # Group by date
    by_date = {}
    for ck in checkins:
        dt = ck['time']
        if isinstance(dt, str):
            dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        date_str = dt.strftime("%Y-%m-%d")
        
        if date_str not in by_date:
            by_date[date_str] = {"in": [], "out": []}
        
        log_type = ck.get('log_type', '')
        if log_type == 'IN':
            by_date[date_str]["in"].append(dt)
        elif log_type == 'OUT':
            by_date[date_str]["out"].append(dt)
        else:
            # Guess based on time
            if dt.hour < 12:
                by_date[date_str]["in"].append(dt)
            else:
                by_date[date_str]["out"].append(dt)
    
    # Analyze each day
    SHIFT_A_START = 7 * 60  # 7:00 in minutes
    SHIFT_A_END = 15 * 60 + 30  # 15:30
    SHIFT_B_START = 15 * 60 + 30  # 15:30
    SHIFT_B_END = 23 * 60 + 59  # 23:59
    
    daily = []
    total_delay = 0
    delay_days = 0
    total_early = 0
    early_days = 0
    shift_a_count = 0
    shift_b_count = 0
    
    for date_str in sorted(by_date.keys()):
        day = by_date[date_str]
        
        if not day["in"]:
            continue
        
        earliest_in = min(day["in"])
        latest_out = max(day["out"]) if day["out"] else None
        
        in_minutes = earliest_in.hour * 60 + earliest_in.minute
        
        # Detect shift
        if 360 <= in_minutes < 840:  # 06:00 - 14:00 -> Shift A
            shift = "A"
            shift_a_count += 1
            delay = max(0, in_minutes - SHIFT_A_START)
            if latest_out:
                out_minutes = latest_out.hour * 60 + latest_out.minute
                early = max(0, SHIFT_A_END - out_minutes)
            else:
                early = 0
        elif 840 <= in_minutes < 1440:  # 14:00 - 24:00 -> Shift B
            shift = "B"
            shift_b_count += 1
            delay = max(0, in_minutes - SHIFT_B_START)
            if latest_out:
                out_minutes = latest_out.hour * 60 + latest_out.minute
                early = max(0, SHIFT_B_END - out_minutes)
            else:
                early = 0
        else:
            shift = "?"
            delay = 0
            early = 0
        
        if delay > 0:
            total_delay += delay
            delay_days += 1
        if early > 0:
            total_early += early
            early_days += 1
        
        daily.append({
            "date": date_str,
            "shift": shift,
            "in": earliest_in.strftime("%H:%M"),
            "out": latest_out.strftime("%H:%M") if latest_out else "-",
            "delay_min": delay,
            "early_min": early
        })
    
    return {
        "employee": emp['employee_name'],
        "total_checkins": len(checkins),
        "working_days": len(daily),
        "shift_a_days": shift_a_count,
        "shift_b_days": shift_b_count,
        "total_delay_min": total_delay,
        "delay_days": delay_days,
        "avg_delay_min": round(total_delay / delay_days, 1) if delay_days else 0,
        "max_delay_min": max((d['delay_min'] for d in daily), default=0),
        "total_early_min": total_early,
        "early_days": early_days,
        "avg_early_min": round(total_early / early_days, 1) if early_days else 0,
        "daily_details": daily
    }

# Analyze دنیا شکرزاده
result = analyze_employee("شکرزاده")
print(json.dumps(result, ensure_ascii=False))
