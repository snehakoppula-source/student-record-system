# Campus Registry - Student Records Management System

Flask + MongoDB web app for managing student records.

## Features
- Overview: totals, average CGPA, department and year breakdown, top students, recent admissions
- Students: add, view profile, edit, delete
- Search by name / roll number / email, department and status filters, pagination
- Export the current filtered list as CSV
- Validation (email, roll number, CGPA range) and a unique index on roll number

## Run in VS Code
1. Install Python 3.10+ and MongoDB Community Server (running on `localhost:27017`).
2. Open this folder in VS Code, then open a terminal (Ctrl+`).
3. Create a virtual environment and install packages:
   ```
   python -m venv venv
   venv\Scripts\activate        (Windows)   |   source venv/bin/activate   (Mac/Linux)
   pip install -r requirements.txt
   ```
4. (Optional) load sample data: `python seed.py`
5. Start the app: `python app.py`, then open http://127.0.0.1:5001

Use MongoDB Atlas or another server by setting the `MONGO_URI` environment variable.

## Structure
```
app.py          routes, validation, aggregation queries, CSV export
seed.py         sample data loader
templates/      Jinja pages (dashboard, list, detail, form)
static/         stylesheet
```
