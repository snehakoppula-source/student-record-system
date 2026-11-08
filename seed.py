"""Fill the database with sample students:  python seed.py"""
import random
from datetime import datetime

from app import DEPARTMENTS, init_db, students

random.seed(11)
first = ["Aarav", "Ananya", "Charan", "Divya", "Farhan", "Gayathri", "Harsha", "Isha", "Karthik", "Lakshmi",
         "Manoj", "Nandini", "Pranav", "Revathi", "Sai", "Tejaswi", "Uday", "Varun", "Yamini", "Zoya"]
last = ["Reddy", "Sharma", "Naidu", "Rao", "Khan", "Varma", "Kumar", "Chowdary", "Iyer", "Patel"]
codes = {"Computer Science": "CS", "Electronics": "EC", "Mechanical": "ME", "Civil": "CE",
         "Electrical": "EE", "Business Administration": "BA"}
docs = []
for n in range(1, 41):
    dept = random.choice(DEPARTMENTS)
    year = random.randint(1, 4)
    name = f"{random.choice(first)} {random.choice(last)}"
    docs.append({
        "roll_no": f"{22 + (4 - year)}{codes[dept]}{n:03d}", "name": name,
        "email": f"{name.lower().replace(' ', '.')}{n}@college.edu",
        "phone": f"98{random.randint(10000000, 99999999)}", "department": dept, "year": year,
        "cgpa": round(random.uniform(5.8, 9.8), 2),
        "status": random.choice(["Active"] * 8 + ["On leave", "Withdrawn"]),
        "address": "Vijayawada, Andhra Pradesh", "created_at": datetime.now(),
    })
init_db()
students.delete_many({})
students.insert_many(docs)
print(f"Inserted {len(docs)} sample students.")
