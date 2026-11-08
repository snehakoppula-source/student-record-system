"""Student Records Management System - Flask + MongoDB."""
import csv
import io
import os
import re
from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, Response, abort, flash, redirect, render_template, request, url_for
from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=3000)
db = client[os.getenv("DB_NAME", "student_records")]
students = db.students

DEPARTMENTS = ["Computer Science", "Electronics", "Mechanical", "Civil", "Electrical", "Business Administration"]
YEARS = [1, 2, 3, 4]
STATUSES = ["Active", "Graduated", "On leave", "Withdrawn"]
PER_PAGE = 10


def init_db():
    students.create_index("roll_no", unique=True)
    students.create_index([("department", ASCENDING), ("year", ASCENDING)])
    students.create_index("name")


def oid(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        abort(404)


def parse_form(f):
    """Validate the student form and return (document, errors)."""
    errors = []
    roll = f.get("roll_no", "").strip().upper()
    name = f.get("name", "").strip()
    email = f.get("email", "").strip().lower()
    phone = f.get("phone", "").strip()
    if not re.fullmatch(r"[A-Z0-9-]{4,15}", roll):
        errors.append("Roll number must be 4-15 letters, digits or hyphens.")
    if len(name) < 2:
        errors.append("Enter the student's full name.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        errors.append("Enter a valid email address.")
    if phone and not re.fullmatch(r"[0-9+\- ]{7,15}", phone):
        errors.append("Phone number can only contain digits, spaces, + and -.")
    if f.get("department") not in DEPARTMENTS:
        errors.append("Choose a department.")
    if f.get("status") not in STATUSES:
        errors.append("Choose a status.")
    try:
        year = int(f.get("year", 0))
        if year not in YEARS:
            raise ValueError
    except ValueError:
        year = 1
        errors.append("Year must be between 1 and 4.")
    try:
        cgpa = float(f.get("cgpa") or 0)
        if not 0 <= cgpa <= 10:
            raise ValueError
    except ValueError:
        cgpa = 0.0
        errors.append("CGPA must be a number from 0 to 10.")
    doc = {"roll_no": roll, "name": name, "email": email, "phone": phone,
           "department": f.get("department"), "year": year, "cgpa": round(cgpa, 2),
           "status": f.get("status"), "address": f.get("address", "").strip()}
    return doc, errors


@app.context_processor
def inject_globals():
    return {"DEPARTMENTS": DEPARTMENTS, "YEARS": YEARS, "STATUSES": STATUSES}


@app.template_filter("initials")
def initials(name):
    parts = (name or "?").split()
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


@app.errorhandler(PyMongoError)
def db_error(err):
    return render_template("error.html", message=str(err)), 503


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", message="That page or student record does not exist."), 404


def build_query(args):
    query = {}
    q = args.get("q", "").strip()
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        query["$or"] = [{"name": rx}, {"roll_no": rx}, {"email": rx}]
    if args.get("department") in DEPARTMENTS:
        query["department"] = args["department"]
    if args.get("status") in STATUSES:
        query["status"] = args["status"]
    return query


@app.route("/")
def dashboard():
    agg = next(students.aggregate([{"$group": {"_id": None, "avg": {"$avg": "$cgpa"}}}]), {})
    stats = {"total": students.count_documents({}),
             "active": students.count_documents({"status": "Active"}),
             "avg": agg.get("avg") or 0,
             "honours": students.count_documents({"cgpa": {"$gte": 9}})}
    by_dept = list(students.aggregate([
        {"$group": {"_id": "$department", "n": {"$sum": 1}, "avg": {"$avg": "$cgpa"}}}, {"$sort": {"n": -1}}]))
    by_year = {r["_id"]: r["n"] for r in students.aggregate([{"$group": {"_id": "$year", "n": {"$sum": 1}}}])}
    toppers = list(students.find({"status": "Active"}).sort("cgpa", -1).limit(5))
    recent = list(students.find().sort("_id", -1).limit(5))
    return render_template("dashboard.html", stats=stats, by_dept=by_dept, by_year=by_year,
                           toppers=toppers, recent=recent)


@app.route("/students")
def student_list():
    query = build_query(request.args)
    page = max(int(request.args.get("page", 1) or 1), 1)
    total = students.count_documents(query)
    rows = students.find(query).sort("name", 1).skip((page - 1) * PER_PAGE).limit(PER_PAGE)
    pages = max((total + PER_PAGE - 1) // PER_PAGE, 1)
    return render_template("list.html", rows=list(rows), total=total, page=page, pages=pages,
                           q=request.args.get("q", ""), department=request.args.get("department", ""),
                           status=request.args.get("status", ""))


@app.route("/students/new", methods=["GET", "POST"])
def student_new():
    if request.method == "POST":
        doc, errors = parse_form(request.form)
        if not errors:
            doc["created_at"] = datetime.now()
            try:
                students.insert_one(doc)
                flash(f"{doc['name']} was added.", "ok")
                return redirect(url_for("student_list"))
            except DuplicateKeyError:
                errors.append(f"Roll number {doc['roll_no']} already exists.")
        for e in errors:
            flash(e, "err")
        return render_template("form.html", item=doc, mode="new")
    return render_template("form.html", item={"year": 1, "status": "Active", "cgpa": 0}, mode="new")


@app.route("/students/<id>")
def student_view(id):
    item = students.find_one({"_id": oid(id)}) or abort(404)
    return render_template("detail.html", s=item)


@app.route("/students/<id>/edit", methods=["GET", "POST"])
def student_edit(id):
    item = students.find_one({"_id": oid(id)}) or abort(404)
    if request.method == "POST":
        doc, errors = parse_form(request.form)
        if not errors:
            try:
                students.update_one({"_id": item["_id"]}, {"$set": doc})
                flash("Student record updated.", "ok")
                return redirect(url_for("student_view", id=id))
            except DuplicateKeyError:
                errors.append(f"Roll number {doc['roll_no']} already belongs to another student.")
        for e in errors:
            flash(e, "err")
        doc["_id"] = item["_id"]
        return render_template("form.html", item=doc, mode="edit")
    return render_template("form.html", item=item, mode="edit")


@app.post("/students/<id>/delete")
def student_delete(id):
    students.delete_one({"_id": oid(id)})
    flash("Student record deleted.", "ok")
    return redirect(url_for("student_list"))


@app.route("/export.csv")
def export_csv():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Roll no", "Name", "Email", "Phone", "Department", "Year", "CGPA", "Status"])
    for s in students.find(build_query(request.args)).sort("roll_no", 1):
        w.writerow([s["roll_no"], s["name"], s["email"], s.get("phone", ""), s["department"],
                    s["year"], s["cgpa"], s["status"]])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=students.csv"})


if __name__ == "__main__":
    try:
        init_db()
    except PyMongoError as exc:
        print(f"\n[!] Cannot reach MongoDB: {exc}\n    Start MongoDB and restart the app.\n")
    app.run(debug=True, port=5001)
