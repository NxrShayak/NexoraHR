import os
from datetime import datetime, date, timedelta
from collections import defaultdict, OrderedDict

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

app = Flask(__name__)

MOCK_EMAIL = "nexora@gmailcom"
MOCK_PASSWORD = "nexoraindia099"


def error_response(message, code=400):
    return jsonify({"error": message}), code


def require_db():
    if supabase is None:
        return error_response("Supabase is not configured on the server.", 500)
    return None


# =====================================================================
# STATIC / HEALTH
# =====================================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200


# =====================================================================
# AUTH (MOCK)
# =====================================================================
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "")
    password = data.get("password", "")
    if email == MOCK_EMAIL and password == MOCK_PASSWORD:
        return jsonify({
            "token": "nexorahr-mock-token-" + datetime.utcnow().isoformat(),
            "user": {"name": "Admin User", "email": MOCK_EMAIL, "role": "Administrator"}
        }), 200
    return error_response("Invalid email or password", 401)


# =====================================================================
# DEPARTMENTS
# =====================================================================
@app.route("/api/departments", methods=["GET"])
def get_departments():
    if (e := require_db()): return e
    try:
        res = supabase.table("departments").select("*").order("id").execute()
        return jsonify(res.data), 200
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/departments", methods=["POST"])
def create_department():
    if (e := require_db()): return e
    data = request.get_json(silent=True) or {}
    try:
        res = supabase.table("departments").insert(data).execute()
        return jsonify(res.data[0] if res.data else {}), 201
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/departments/<int:dept_id>", methods=["PUT"])
def update_department(dept_id):
    if (e := require_db()): return e
    data = request.get_json(silent=True) or {}
    if not data:
        return error_response("No fields to update", 400)
    try:
        res = supabase.table("departments").update(data).eq("id", dept_id).execute()
        return jsonify(res.data[0] if res.data else {}), 200
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/departments/<int:dept_id>", methods=["DELETE"])
def delete_department(dept_id):
    if (e := require_db()): return e
    try:
        supabase.table("departments").delete().eq("id", dept_id).execute()
        return jsonify({"success": True}), 200
    except Exception as ex:
        return error_response(str(ex), 500)


# =====================================================================
# POSITIONS
# =====================================================================
@app.route("/api/positions", methods=["GET"])
def get_positions():
    if (e := require_db()): return e
    try:
        pos_res = supabase.table("positions").select("*, departments(name)").order("id").execute()
        positions = pos_res.data or []

        emp_res = supabase.table("employees").select("id, name, profile_pic, position_id").execute()
        employees = emp_res.data or []

        emp_by_position = defaultdict(list)
        for emp in employees:
            if emp.get("position_id"):
                emp_by_position[emp["position_id"]].append({
                    "id": emp["id"],
                    "name": emp["name"],
                    "profile_pic": emp.get("profile_pic")
                })

        for p in positions:
            p["department_name"] = (p.get("departments") or {}).get("name") if p.get("departments") else None
            p["assigned_employees"] = emp_by_position.get(p["id"], [])

        return jsonify(positions), 200
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/positions", methods=["POST"])
def create_position():
    if (e := require_db()): return e
    data = request.get_json(silent=True) or {}
    try:
        res = supabase.table("positions").insert(data).execute()
        return jsonify(res.data[0] if res.data else {}), 201
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/positions/<int:pos_id>", methods=["PUT"])
def update_position(pos_id):
    if (e := require_db()): return e
    data = request.get_json(silent=True) or {}
    if not data:
        return error_response("No fields to update", 400)
    try:
        res = supabase.table("positions").update(data).eq("id", pos_id).execute()
        return jsonify(res.data[0] if res.data else {}), 200
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/positions/<int:pos_id>", methods=["DELETE"])
def delete_position(pos_id):
    if (e := require_db()): return e
    try:
        supabase.table("positions").delete().eq("id", pos_id).execute()
        return jsonify({"success": True}), 200
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/positions/<int:pos_id>/assign", methods=["POST"])
def assign_employee_to_position(pos_id):
    if (e := require_db()): return e
    data = request.get_json(silent=True) or {}
    employee_id = data.get("employee_id")
    if not employee_id:
        return error_response("employee_id is required", 400)
    try:
        res = supabase.table("employees").update({"position_id": pos_id}).eq("id", employee_id).execute()
        return jsonify(res.data[0] if res.data else {}), 200
    except Exception as ex:
        return error_response(str(ex), 500)


# =====================================================================
# EMPLOYEES
# =====================================================================
@app.route("/api/employees", methods=["GET"])
def get_employees():
    if (e := require_db()): return e
    try:
        res = supabase.table("employees").select(
            "*, departments(name), positions(title)"
        ).order("id").execute()
        employees = res.data or []
        for emp in employees:
            emp["department_name"] = (emp.get("departments") or {}).get("name") if emp.get("departments") else None
            emp["position_title"] = (emp.get("positions") or {}).get("title") if emp.get("positions") else None
        return jsonify(employees), 200
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/employees", methods=["POST"])
def create_employee():
    if (e := require_db()): return e
    data = request.get_json(silent=True) or {}
    if not data.get("name") or not data.get("email"):
        return error_response("name and email are required", 400)
    try:
        res = supabase.table("employees").insert(data).execute()
        return jsonify(res.data[0] if res.data else {}), 201
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/employees/<int:emp_id>", methods=["PUT"])
def update_employee(emp_id):
    if (e := require_db()): return e
    data = request.get_json(silent=True) or {}
    if not data:
        return error_response("No fields to update", 400)
    try:
        res = supabase.table("employees").update(data).eq("id", emp_id).execute()
        return jsonify(res.data[0] if res.data else {}), 200
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/employees/<int:emp_id>", methods=["DELETE"])
def delete_employee(emp_id):
    if (e := require_db()): return e
    try:
        supabase.table("employees").delete().eq("id", emp_id).execute()
        return jsonify({"success": True}), 200
    except Exception as ex:
        return error_response(str(ex), 500)


# =====================================================================
# ATTENDANCE
# =====================================================================
@app.route("/api/attendance", methods=["GET"])
def get_attendance():
    if (e := require_db()): return e
    try:
        res = supabase.table("attendance").select("*, employees(name, profile_pic)").order("date", desc=True).execute()
        rows = res.data or []
        for r in rows:
            r["employee_name"] = (r.get("employees") or {}).get("name") if r.get("employees") else None
            r["employee_pic"] = (r.get("employees") or {}).get("profile_pic") if r.get("employees") else None
        return jsonify(rows), 200
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/attendance", methods=["POST"])
def create_attendance():
    if (e := require_db()): return e
    data = request.get_json(silent=True) or {}
    if not data.get("employee_id"):
        return error_response("employee_id is required", 400)
    try:
        res = supabase.table("attendance").insert(data).execute()
        return jsonify(res.data[0] if res.data else {}), 201
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/attendance/<int:att_id>", methods=["PUT"])
def update_attendance(att_id):
    if (e := require_db()): return e
    data = request.get_json(silent=True) or {}
    if not data:
        return error_response("No fields to update", 400)
    try:
        res = supabase.table("attendance").update(data).eq("id", att_id).execute()
        return jsonify(res.data[0] if res.data else {}), 200
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/attendance/<int:att_id>", methods=["DELETE"])
def delete_attendance(att_id):
    if (e := require_db()): return e
    try:
        supabase.table("attendance").delete().eq("id", att_id).execute()
        return jsonify({"success": True}), 200
    except Exception as ex:
        return error_response(str(ex), 500)


# =====================================================================
# LEAVES
# =====================================================================
@app.route("/api/leaves", methods=["GET"])
def get_leaves():
    if (e := require_db()): return e
    try:
        res = supabase.table("leaves").select("*, employees(name, profile_pic)").order("id", desc=True).execute()
        rows = res.data or []
        for r in rows:
            r["employee_name"] = (r.get("employees") or {}).get("name") if r.get("employees") else None
            r["employee_pic"] = (r.get("employees") or {}).get("profile_pic") if r.get("employees") else None
        return jsonify(rows), 200
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/leaves", methods=["POST"])
def create_leave():
    if (e := require_db()): return e
    data = request.get_json(silent=True) or {}
    if not data.get("employee_id") or not data.get("start_date") or not data.get("end_date"):
        return error_response("employee_id, start_date and end_date are required", 400)
    try:
        res = supabase.table("leaves").insert(data).execute()
        return jsonify(res.data[0] if res.data else {}), 201
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/leaves/<int:leave_id>", methods=["PUT"])
def update_leave(leave_id):
    if (e := require_db()): return e
    data = request.get_json(silent=True) or {}
    if not data:
        return error_response("No fields to update", 400)
    try:
        res = supabase.table("leaves").update(data).eq("id", leave_id).execute()
        return jsonify(res.data[0] if res.data else {}), 200
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/leaves/<int:leave_id>", methods=["DELETE"])
def delete_leave(leave_id):
    if (e := require_db()): return e
    try:
        supabase.table("leaves").delete().eq("id", leave_id).execute()
        return jsonify({"success": True}), 200
    except Exception as ex:
        return error_response(str(ex), 500)


# =====================================================================
# PAYROLL
# =====================================================================
@app.route("/api/payroll", methods=["GET"])
def get_payroll():
    if (e := require_db()): return e
    try:
        res = supabase.table("payroll").select("*, employees(name, profile_pic)").order("id", desc=True).execute()
        rows = res.data or []
        for r in rows:
            r["employee_name"] = (r.get("employees") or {}).get("name") if r.get("employees") else None
            r["employee_pic"] = (r.get("employees") or {}).get("profile_pic") if r.get("employees") else None
        return jsonify(rows), 200
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/payroll", methods=["POST"])
def create_payroll():
    if (e := require_db()): return e
    data = request.get_json(silent=True) or {}
    if not data.get("employee_id") or not data.get("month"):
        return error_response("employee_id and month are required", 400)
    try:
        basic = float(data.get("basic_salary") or 0)
        bonus = float(data.get("bonus") or 0)
        deductions = float(data.get("deductions") or 0)
        data["net_salary"] = round(basic + bonus - deductions, 2)
        res = supabase.table("payroll").insert(data).execute()
        return jsonify(res.data[0] if res.data else {}), 201
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/payroll/<int:pay_id>", methods=["PUT"])
def update_payroll(pay_id):
    if (e := require_db()): return e
    data = request.get_json(silent=True) or {}
    if not data:
        return error_response("No fields to update", 400)
    try:
        if any(k in data for k in ("basic_salary", "bonus", "deductions")):
            existing = supabase.table("payroll").select("*").eq("id", pay_id).single().execute().data or {}
            basic = float(data.get("basic_salary", existing.get("basic_salary") or 0))
            bonus = float(data.get("bonus", existing.get("bonus") or 0))
            deductions = float(data.get("deductions", existing.get("deductions") or 0))
            data["net_salary"] = round(basic + bonus - deductions, 2)
        res = supabase.table("payroll").update(data).eq("id", pay_id).execute()
        return jsonify(res.data[0] if res.data else {}), 200
    except Exception as ex:
        return error_response(str(ex), 500)


@app.route("/api/payroll/<int:pay_id>", methods=["DELETE"])
def delete_payroll(pay_id):
    if (e := require_db()): return e
    try:
        supabase.table("payroll").delete().eq("id", pay_id).execute()
        return jsonify({"success": True}), 200
    except Exception as ex:
        return error_response(str(ex), 500)


# =====================================================================
# DASHBOARD STATS
# =====================================================================
@app.route("/api/dashboard/stats", methods=["GET"])
def dashboard_stats():
    if (e := require_db()): return e
    try:
        employees = (supabase.table("employees").select("*, departments(name), positions(title)").execute().data) or []
        departments = (supabase.table("departments").select("*").execute().data) or []
        attendance = (supabase.table("attendance").select("*").execute().data) or []
        leaves = (supabase.table("leaves").select("*").execute().data) or []
        payroll = (supabase.table("payroll").select("*").execute().data) or []

        today = date.today()
        today_str = today.isoformat()
        current_month_prefix = today.strftime("%Y-%m")

        total_employees = len(employees)
        total_departments = len(departments)
        present_today = len([a for a in attendance if a.get("date") == today_str and a.get("status") == "Present"])
        pending_leaves = len([l for l in leaves if l.get("status") == "Pending"])
        monthly_payroll = sum(
            float(p.get("net_salary") or 0) for p in payroll
            if str(p.get("generated_date") or "").startswith(current_month_prefix)
        )

        # Hiring trend: last 6 months
        month_labels = []
        month_counts = OrderedDict()
        y, m = today.year, today.month
        months_sequence = []
        for i in range(5, -1, -1):
            mm = m - i
            yy = y
            while mm <= 0:
                mm += 12
                yy -= 1
            months_sequence.append((yy, mm))
        for yy, mm in months_sequence:
            key = f"{yy}-{mm:02d}"
            month_counts[key] = 0
            month_labels.append(datetime(yy, mm, 1).strftime("%b %Y"))
        for emp in employees:
            hd = emp.get("hire_date")
            if hd:
                key = str(hd)[:7]
                if key in month_counts:
                    month_counts[key] += 1

        # Department mix
        dept_name_by_id = {d["id"]: d["name"] for d in departments}
        dept_counts = defaultdict(int)
        for emp in employees:
            dname = dept_name_by_id.get(emp.get("department_id"), "Unassigned")
            dept_counts[dname] += 1

        # Employees by position (list, not chart)
        employees_by_position = []
        for emp in employees:
            employees_by_position.append({
                "id": emp["id"],
                "name": emp["name"],
                "profile_pic": emp.get("profile_pic"),
                "position_title": (emp.get("positions") or {}).get("title") if emp.get("positions") else "Unassigned"
            })

        # Attendance trend: last 7 days
        att_labels = []
        att_counts = OrderedDict()
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            key = d.isoformat()
            att_counts[key] = 0
            att_labels.append(d.strftime("%a"))
        for a in attendance:
            key = str(a.get("date"))
            if key in att_counts and a.get("status") == "Present":
                att_counts[key] += 1

        # Status breakdown
        status_counts = defaultdict(int)
        for emp in employees:
            status_counts[emp.get("status") or "Active"] += 1

        return jsonify({
            "cards": {
                "total_employees": total_employees,
                "total_departments": total_departments,
                "present_today": present_today,
                "pending_leaves": pending_leaves,
                "monthly_payroll": round(monthly_payroll, 2)
            },
            "hiring_trend": {
                "labels": month_labels,
                "data": list(month_counts.values())
            },
            "department_mix": {
                "labels": list(dept_counts.keys()),
                "data": list(dept_counts.values())
            },
            "employees_by_position": employees_by_position,
            "attendance_trend": {
                "labels": att_labels,
                "data": list(att_counts.values())
            },
            "status_breakdown": {
                "labels": list(status_counts.keys()),
                "data": list(status_counts.values())
            }
        }), 200
    except Exception as ex:
        return error_response(str(ex), 500)


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
