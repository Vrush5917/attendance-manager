import os
import csv
import calendar
from datetime import date
from fpdf import FPDF
from flask import jsonify

# Configure absolute paths here
EMPLOYEE_FILE = "/full/path/to/employees.txt"
LIVE_DATA_DIR = "/full/path/to/live/attendance"
ARCHIVE_DIR = "/full/path/to/archive/attendance"
DATA_DIR = LIVE_DATA_DIR  # For daily report, use live data dir


def load_employees(employee_file=EMPLOYEE_FILE):
    if not os.path.exists(employee_file):
        print(f"[ERROR] Employee file not found: {employee_file}")
        return []
    with open(employee_file, "r", encoding="utf-8") as f:
        employees = [line.strip() for line in f if line.strip()]
    print(f"[DEBUG] Loaded employees ({len(employees)}): {employees}")
    return employees


def today_list():
    employees = load_employees()
    today = date.today().strftime("%Y-%m-%d")
    fname = f"attendance_{today}.csv"
    path = os.path.join(DATA_DIR, fname)

    print(f"[DEBUG] Looking for today's attendance file: {path}")

    present_names = set()
    if os.path.exists(path):
        with open(path, 'r', encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(',', 1)
                if len(parts) == 2:
                    present_names.add(parts[0])
        print(f"[DEBUG] Present employees today: {present_names}")
    else:
        print(f"[WARNING] Attendance file not found for today: {path}")

    attendance_status = []
    for emp in employees:
        status = "Present" if emp in present_names else "Absent"
        attendance_status.append({"name": emp, "status": status})

    return jsonify({"attendance": attendance_status})


def csv_to_pdf(csv_path, pdf_path, title="Attendance Report", employee_file=EMPLOYEE_FILE):
    employees = load_employees(employee_file)
    if not employees:
        raise RuntimeError("Employee list not found or empty")

    attendance = set()
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 1:
                    attendance.add(row[0])
    else:
        print(f"[WARNING] CSV file for report not found: {csv_path}")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(90, 10, "Employee Name", 1, align='C')
    pdf.cell(90, 10, "Status", 1, align='C')
    pdf.ln()

    pdf.set_font("Arial", '', 12)
    for emp in employees:
        status = "Present" if emp in attendance else "Absent"
        pdf.cell(90, 10, emp, 1)
        pdf.cell(90, 10, status, 1, align='C')
        pdf.ln()

    pdf.output(pdf_path)
    print(f"[INFO] Daily PDF report generated at: {pdf_path}")


def monthly_report_pdf(month_str, archive_dir=ARCHIVE_DIR, pdf_path="monthly_report.pdf",
                       employee_file=EMPLOYEE_FILE, live_data_dir=LIVE_DATA_DIR):
    employees = load_employees(employee_file)
    if not employees:
        raise RuntimeError("Employee list not found or empty")

    year, month = map(int, month_str.split('-'))
    num_days = calendar.monthrange(year, month)[1]

    counts = {emp: {"Present": 0, "Absent": 0} for emp in employees}

    for day in range(1, num_days + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        csv_name = f"attendance_{date_str}.csv"

        csv_path = os.path.join(archive_dir, csv_name)
        if not os.path.exists(csv_path) and live_data_dir:
            live_csv_path = os.path.join(live_data_dir, csv_name)
            if os.path.exists(live_csv_path):
                csv_path = live_csv_path

        if not os.path.exists(csv_path):
            for emp in employees:
                counts[emp]["Absent"] += 1
            continue

        present_names = set()
        with open(csv_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(',', 1)
                if len(parts) == 2:
                    present_names.add(parts[0])

        for emp in employees:
            if emp in present_names:
                counts[emp]["Present"] += 1
            else:
                counts[emp]["Absent"] += 1

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Monthly Attendance Report: {month_str}", ln=True, align='C')

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(80, 10, "Employee Name", border=1, align='C')
    pdf.cell(40, 10, "Present Days", border=1, align='C')
    pdf.cell(40, 10, "Absent Days", border=1, align='C')
    pdf.ln()

    pdf.set_font("Arial", '', 12)
    for emp in employees:
        pdf.cell(80, 10, emp, border=1)
        pdf.cell(40, 10, str(counts[emp]["Present"]), border=1, align='C')
        pdf.cell(40, 10, str(counts[emp]["Absent"]), border=1, align='C')
        pdf.ln()

    pdf.output(pdf_path)
    print(f"[INFO] Monthly PDF report generated at: {pdf_path}")

