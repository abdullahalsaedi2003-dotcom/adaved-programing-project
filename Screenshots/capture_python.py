"""
Capture screenshots of the Python tkinter GUI for the report.
Starts the server, drives the client through scripted states,
and saves PNGs into the Screenshots folder.
"""
import os
import sys
import time
import subprocess
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY_DIR = os.path.join(ROOT, "Python")
SHOTS = os.path.dirname(os.path.abspath(__file__))

# Reset DB so screenshots are deterministic
db = os.path.join(PY_DIR, "smartsms.db")
if os.path.exists(db):
    os.remove(db)

# Start the server in a background subprocess
server = subprocess.Popen(
    [sys.executable, "server.py"],
    cwd=PY_DIR,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
time.sleep(1.0)

try:
    # Inject the Python folder so we can import client.py
    sys.path.insert(0, PY_DIR)

    import tkinter as tk
    from PIL import ImageGrab

    # Load client module
    import client as C

    def snap(win, name, delay=0.5):
        win.attributes("-topmost", True)
        win.lift()
        win.focus_force()
        win.update_idletasks()
        win.update()
        time.sleep(delay)
        win.update_idletasks()
        win.update()
        time.sleep(0.3)
        x = win.winfo_rootx()
        y = win.winfo_rooty()
        w = win.winfo_width()
        h = win.winfo_height()
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
        path = os.path.join(SHOTS, f"py_{name}.png")
        img.save(path)
        print("  saved:", path, f"({w}x{h})")

    # 1. Login window
    login = C.LoginWindow()
    login.update()
    snap(login, "01_login", delay=0.8)
    # Login as admin
    login.user_var.set("admin")
    login.pwd_var.set("admin123")
    login.do_login()  # this calls destroy on success

    # 2. Main app - Students tab (default)
    app = C.MainApp(C.net.send("login", {"username": "admin", "password": "admin123"})["role"])
    app.update()
    snap(app, "02_main_students", delay=1.0)

    # 3. Add Student dialog -> error case (bad id)
    app.students_tab.vars["student_id"].set("abc")
    app.students_tab.vars["name"].set("Sample Bad")
    app.students_tab.vars["email"].set("x@y.co")
    app.students_tab.vars["phone"].set("0500000000")
    app.students_tab.vars["major"].set("IS")
    app.students_tab.vars["level"].set("3")
    app.update()
    snap(app, "03_students_form_filled", delay=0.5)

    # 4. Add Student - good
    app.students_tab.vars["student_id"].set("2220009999")
    app.students_tab.vars["name"].set("Sara Mohammed")
    app.students_tab.vars["email"].set("sara@iau.edu.sa")
    app.students_tab.vars["phone"].set("0501234567")
    app.students_tab.vars["major"].set("IT")
    app.students_tab.vars["level"].set("3")
    app.update()
    # bypass messagebox by calling net.send directly to add the record
    C.net.send("add_student", {k: v.get() for k, v in app.students_tab.vars.items()})
    app.students_tab.view_all()
    app.students_tab.clear()
    app.update()
    snap(app, "04_students_after_add", delay=0.8)

    # 5. Search students
    app.students_tab.vars["name"].set("Sara")
    app.students_tab.search()
    app.update()
    snap(app, "05_students_search", delay=0.6)

    # 6. Courses tab
    app.children["!notebook"].select(1)
    app.update()
    app.courses_tab.view_all()
    snap(app, "06_courses_tab", delay=0.8)

    # 7. Add a course
    C.net.send("add_course", {"code": "CS401", "title": "Database Systems", "credits": "3", "instructor": "Dr. Mona"})
    app.courses_tab.view_all()
    snap(app, "07_courses_after_add", delay=0.6)

    # 8. Enrollment tab
    app.children["!notebook"].select(2)
    app.update()
    # add some enrollments via server directly
    C.net.send("enroll", {"student_id": "2220007240", "course_code": "CS516", "semester": "2025-2 (Spring)"})
    C.net.send("enroll", {"student_id": "2220003178", "course_code": "CS516", "semester": "2025-2 (Spring)"})
    C.net.send("enroll", {"student_id": "2220002306", "course_code": "CS411", "semester": "2025-2 (Spring)"})
    C.net.send("enroll", {"student_id": "2220009999", "course_code": "CS401", "semester": "2025-2 (Spring)"})
    app.enroll_tab.view_all()
    snap(app, "08_enrollment_tab", delay=0.8)

    # 9. Attendance tab - report
    app.children["!notebook"].select(3)
    app.update()
    for sid, code, d, st in [
        ("2220007240", "CS516", "2026-05-10", "Present"),
        ("2220007240", "CS516", "2026-05-12", "Present"),
        ("2220007240", "CS516", "2026-05-14", "Absent"),
        ("2220003178", "CS516", "2026-05-10", "Present"),
        ("2220003178", "CS516", "2026-05-12", "Absent"),
        ("2220002306", "CS411", "2026-05-11", "Present"),
    ]:
        C.net.send("mark_attendance", {"student_id": sid, "course_code": code, "date": d, "status": st})
    app.att_tab.full_report()
    snap(app, "09_attendance_report", delay=0.8)

    # 10. Attendance summary
    app.att_tab.code.set("CS516")
    app.att_tab.summary()
    snap(app, "10_attendance_summary", delay=0.8)

    app.destroy()
    print("Done.")
finally:
    server.terminate()
    try:
        server.wait(timeout=3)
    except Exception:
        server.kill()
