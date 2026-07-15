#!/usr/bin/env python3
"""Attendance Report for عظیمیه - Detect shift from in_time, calculate delays"""
import json, sys
import frappe
from datetime import datetime, timedelta

COMPANY = "عظیمیه"
START_DATE = "2026-03-12"

# Shift definitions
SHIFT_A_START = 7 * 60    # 07:00 in minutes
SHIFT_A_END = 15 * 60 + 30  # 15:30 in minutes
SHIFT_B_START = 15 * 60 + 30  # 15:30 in minutes
SHIFT_B_END = 23 * 60 + 59  # 23:59 in minutes

def time_to_minutes(t):
    """Convert time string or datetime to minutes from midnight"""
    if t is None:
        return None
    if isinstance(t, str):
        try:
            dt = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
            return dt.hour * 60 + dt.minute
        except:
            return None
    if hasattr(t, 'hour'):
        return t.hour * 60 + t.minute
    return None

def detect_shift(in_minutes):
    """Detect which shift based on in_time"""
    if in_minutes is None:
        return "Unknown"
    # Shift A: 07:00 - 11:00 (allow some buffer)
    if 360 <= in_minutes <= 660:  # 06:00 - 11:00
        return "A"
    # Shift B: 14:00 - 18:00
    if 840 <= in_minutes <= 1080:  # 14:00 - 18:00
        return "B"
    # Early morning (before 6) -> probably shift B from previous day
    if in_minutes < 360:
        return "B"
    return "Unknown"

def calculate_delay(in_minutes, shift):
    """Calculate delay in minutes"""
    if in_minutes is None or shift == "Unknown":
        return 0
    if shift == "A":
        # Expected: 07:00 (420 min)
        delay = in_minutes - SHIFT_A_START
        return max(0, delay)
    if shift == "B":
        # Expected: 15:30 (930 min)
        delay = in_minutes - SHIFT_B_START
        return max(0, delay)
    return 0

def calculate_early_exit(out_minutes, shift):
    """Calculate early exit in minutes"""
    if out_minutes is None or shift == "Unknown":
        return 0
    if shift == "A":
        # Expected end: 15:30 (930 min)
        early = SHIFT_A_END - out_minutes
        return max(0, early)
    if shift == "B":
        # Expected end: 23:59 (1439 min)
        early = SHIFT_B_END - out_minutes
        return max(0, early)
    return 0

def run_report():
    # Get all attendance records for عظیمیه
    records = frappe.db.sql("""
        SELECT a.name, a.employee_name, a.attendance_date, a.in_time, a.out_time,
               a.working_hours, a.late_entry, a.early_exit, a.status
        FROM `tabAttendance` a
        INNER JOIN `tabEmployee` e ON e.name = a.employee
        WHERE e.company = %s AND a.attendance_date >= %s AND a.status = 'Present'
        ORDER BY a.employee_name, a.attendance_date
    """, (COMPANY, START_DATE), as_dict=True)

    if not records:
        return {"error": "No attendance records found"}

    # Process each record
    employee_stats = {}
    daily_details = []

    for rec in records:
        emp = rec['employee_name']
        date = str(rec['attendance_date'])
        in_min = time_to_minutes(rec['in_time'])
        out_min = time_to_minutes(rec['out_time'])
        shift = detect_shift(in_min)
        delay = calculate_delay(in_min, shift)
        early = calculate_early_exit(out_min, shift)

        in_str = f"{in_min // 60:02d}:{in_min % 60:02d}" if in_min else "-"
        out_str = f"{out_min // 60:02d}:{out_min % 60:02d}" if out_min else "-"

        daily_details.append({
            'employee': emp,
            'date': date,
            'shift': shift,
            'in_time': in_str,
            'out_time': out_str,
            'delay_min': delay,
            'early_min': early,
            'has_delay': delay > 0,
            'has_early': early > 0,
        })

        if emp not in employee_stats:
            employee_stats[emp] = {
                'total_days': 0,
                'shift_a_days': 0,
                'shift_b_days': 0,
                'total_delay_min': 0,
                'delay_count': 0,
                'total_early_min': 0,
                'early_count': 0,
                'max_delay': 0,
            }

        stats = employee_stats[emp]
        stats['total_days'] += 1
        if shift == 'A':
            stats['shift_a_days'] += 1
        elif shift == 'B':
            stats['shift_b_days'] += 1
        if delay > 0:
            stats['total_delay_min'] += delay
            stats['delay_count'] += 1
            stats['max_delay'] = max(stats['max_delay'], delay)
        if early > 0:
            stats['total_early_min'] += early
            stats['early_count'] += 1

    # Build summary
    summary = []
    for emp, stats in sorted(employee_stats.items()):
        avg_delay = round(stats['total_delay_min'] / stats['delay_count'], 1) if stats['delay_count'] > 0 else 0
        avg_early = round(stats['total_early_min'] / stats['early_count'], 1) if stats['early_count'] > 0 else 0
        summary.append({
            'employee': emp,
            'total_days': stats['total_days'],
            'shift_a': stats['shift_a_days'],
            'shift_b': stats['shift_b_days'],
            'delay_count': stats['delay_count'],
            'total_delay_min': stats['total_delay_min'],
            'avg_delay_min': avg_delay,
            'max_delay_min': stats['max_delay'],
            'early_count': stats['early_count'],
            'total_early_min': stats['total_early_min'],
            'avg_early_min': avg_early,
        })

    # Filter only those with delays
    delayed_employees = [s for s in summary if s['delay_count'] > 0]
    delayed_employees.sort(key=lambda x: x['total_delay_min'], reverse=True)

    return {
        "success": True,
        "total_records": len(records),
        "total_employees": len(employee_stats),
        "employees_with_delays": len(delayed_employees),
        "summary": summary,
        "delayed_employees": delayed_employees,
        "daily_details": daily_details,
    }

result = run_report()
print(json.dumps(result))
