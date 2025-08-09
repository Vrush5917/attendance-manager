from flask import Flask, request, jsonify, send_file, send_from_directory
import ctypes
import os
from datetime import datetime, date
from pdf_generator import csv_to_pdf, monthly_report_pdf
from apscheduler.schedulers.background import BackgroundScheduler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(BASE_DIR, "libattendance.so")
DATA_DIR = os.path.join(BASE_DIR, "data")
ARCHIVE_DIR = os.path.join(BASE_DIR, "archive")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
EMPLOYEE_FILE = os.path.join(BASE_DIR, "employees.txt")

# Ensure required folders exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Load C library
lib = ctypes.CDLL(LIB_PATH)
lib.mark_attendance.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
lib.mark_attendance.restype = ctypes.c_int
lib.rotate_today_csv.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
lib.rotate_today_csv.restype = ctypes.c_int

app = Flask(__name__, static_folder="static/frontend", static_url_path="")

def load_employees():
    if not os.path.exists(EMPLOYEE_FILE):
        return []
    with open(EMPLOYEE_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

@app.route('/employees', methods=['GET'])
def get_employees():
    employees = load_employees()
    if not employees:
        return jsonify({"error": "No employees found"}), 404
    return jsonify({"employees": employees})

@app.route('/today', methods=['GET'])
def today_list():
    employees = load_employees()
    today = date.today().strftime("%Y-%m-%d")
    fname = f"attendance_{today}.csv"
    path = os.path.join(DATA_DIR, fname)

    present_names = set()
    if os.path.exists(path):
        with open(path, 'r', encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(',', 1)
                if len(parts) == 2:
                    present_names.add(parts[0])

    attendance_status = []
    for emp in employees:
        status = "Present" if emp in present_names else "Absent"
        attendance_status.append({"name": emp, "status": status})

    return jsonify({"attendance": attendance_status})

@app.route('/submit_attendance', methods=['POST'])
def submit_attendance():
    data = request.get_json()
    attendance_list = data.get('attendance', [])

    employees = load_employees()
    valid_statuses = {'Present', 'Absent'}

    # Validate all entries
    for record in attendance_list:
        name = record.get('name')
        status = record.get('status')
        if name not in employees:
            return jsonify({"error": f"Invalid employee name: {name}"}), 400
        if status not in valid_statuses:
            return jsonify({"error": f"Invalid status for {name}: {status}"}), 400

    # Write only Present employees to CSV
    lines = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for record in attendance_list:
        if record.get('status') == 'Present':
            lines.append(f"{record.get('name')},{now_str}")

    today = date.today().strftime("%Y-%m-%d")
    csv_path = os.path.join(DATA_DIR, f"attendance_{today}.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return jsonify({"msg": "Attendance updated successfully."})

@app.route('/report', methods=['GET'])
def get_report():
    date_q = request.args.get('date', date.today().strftime("%Y-%m-%d"))
    pdf_name = f"attendance_{date_q}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, pdf_name)

    csv_name = f"attendance_{date_q}.csv"
    csv_path = os.path.join(ARCHIVE_DIR, csv_name)
    if not os.path.exists(csv_path):
        csv_path_live = os.path.join(DATA_DIR, csv_name)
        if os.path.exists(csv_path_live):
            csv_path = csv_path_live
        else:
            return jsonify({"error": "No attendance data for requested date"}), 404

    try:
        # Always regenerate PDF from CSV to ensure fresh data
        csv_to_pdf(csv_path, pdf_path, title=f"Attendance for {date_q}", employee_file=EMPLOYEE_FILE)
        return send_file(pdf_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/report/monthly', methods=['GET'])
def get_monthly_report():
    month_q = request.args.get('month')  # format YYYY-MM
    if not month_q:
        return jsonify({"error": "month parameter required (YYYY-MM)"}), 400

    pdf_name = f"monthly_report_{month_q}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, pdf_name)

    try:
        # Pass both ARCHIVE_DIR and DATA_DIR for checking files
        monthly_report_pdf(month_q, ARCHIVE_DIR, pdf_path, employee_file=EMPLOYEE_FILE, live_data_dir=DATA_DIR)
        return send_file(pdf_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/reports/list', methods=['GET'])
def list_reports():
    try:
        files = [f for f in os.listdir(REPORTS_DIR) if f.endswith('.pdf')]
        files.sort(reverse=True)
        return jsonify(files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def rotate_and_archive():
    today = date.today().strftime("%Y-%m-%d")
    src = os.path.join(DATA_DIR, f"attendance_{today}.csv")
    dst = os.path.join(ARCHIVE_DIR, f"attendance_{today}.csv")

    res = lib.rotate_today_csv(ctypes.c_char_p(DATA_DIR.encode('utf-8')), ctypes.c_char_p(dst.encode('utf-8')))
    if res != 0:
        print("Rotate failed", res)
    else:
        print(f"Archived {src} -> {dst}")

    pdf_path = os.path.join(REPORTS_DIR, f"attendance_{today}.pdf")
    try:
        if os.path.exists(dst):
            csv_to_pdf(dst, pdf_path, title=f"Attendance for {today}", employee_file=EMPLOYEE_FILE)
            print("PDF created:", pdf_path)
        else:
            open(dst, 'a').close()
            csv_to_pdf(dst, pdf_path, title=f"Attendance for {today}", employee_file=EMPLOYEE_FILE)
    except Exception as e:
        print("PDF generation error:", e)

def start_scheduler():
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(rotate_and_archive, 'cron', hour=19, minute=0)
    scheduler.start()
    print("Scheduler started (daily at 19:00 Asia/Kolkata)")

# Frontend static files serving
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

if __name__ == '__main__':
    if not os.path.exists(LIB_PATH):
        raise RuntimeError("libattendance.so not found. Build it with `make` in backend/")
    start_scheduler()
    app.run(host='0.0.0.0', port=5000)
