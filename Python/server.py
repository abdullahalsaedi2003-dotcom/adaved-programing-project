"""
Smart Student Management & Attendance System - Server
CS516 - Advanced Programming Language
"""
import socket
import threading
import sqlite3
import json
import os
from datetime import datetime

HOST = "127.0.0.1"
PORT = 5055
DB_FILE = os.path.join(os.path.dirname(__file__), "smartsms.db")


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','instructor'))
        );
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            major TEXT NOT NULL,
            level INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            credits INTEGER NOT NULL,
            instructor TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            course_code TEXT NOT NULL,
            semester TEXT NOT NULL,
            UNIQUE(student_id, course_code, semester)
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            course_code TEXT NOT NULL,
            adate TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present','Absent'))
        );
        """
    )

    # seed default users if empty
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO users(username,password,role) VALUES(?,?,?)",
            [
                ("admin", "admin123", "admin"),
                ("ahmed", "ahmed123", "instructor"),
                ("abdullah", "abdullah123", "instructor"),
            ],
        )

    cur.execute("SELECT COUNT(*) FROM students")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO students(student_id,name,email,phone,major,level) VALUES(?,?,?,?,?,?)",
            [
                ("2220007240", "Ahmed Al-Awlaqi", "ahmed@iau.edu.sa", "0551234567", "CS", 4),
                ("2220003178", "Abdulaziz Alghamdi", "aziz@iau.edu.sa", "0559876543", "CS", 4),
                ("2220002306", "Abdullah Alsaedi", "abdullah@iau.edu.sa", "0556677889", "CS", 4),
            ],
        )

    cur.execute("SELECT COUNT(*) FROM courses")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO courses(code,title,credits,instructor) VALUES(?,?,?,?)",
            [
                ("CS516", "Advanced Programming Language", 3, "Mrs. Sarah Alissa"),
                ("CS411", "Software Engineering", 3, "Dr. Fatimah"),
                ("CS324", "Operating Systems", 4, "Dr. Khalid"),
            ],
        )

    conn.commit()
    conn.close()


def is_valid_email(s):
    return "@" in s and "." in s.split("@")[-1] and len(s) >= 5


def is_valid_phone(s):
    return s.isdigit() and 8 <= len(s) <= 15


def is_valid_id(s):
    return s.isdigit() and len(s) == 10


def is_valid_date(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# ----------- request handlers -----------
def handle_login(p):
    conn = get_conn()
    row = conn.execute(
        "SELECT role FROM users WHERE username=? AND password=?",
        (p.get("username", ""), p.get("password", "")),
    ).fetchone()
    conn.close()
    if row:
        return {"ok": True, "role": row["role"]}
    return {"ok": False, "error": "Invalid credentials"}


def handle_list_students(p):
    conn = get_conn()
    rows = conn.execute(
        "SELECT student_id,name,email,phone,major,level FROM students ORDER BY student_id"
    ).fetchall()
    conn.close()
    return {"ok": True, "data": [dict(r) for r in rows]}


def handle_add_student(p):
    if not is_valid_id(p.get("student_id", "")):
        return {"ok": False, "error": "Student ID must be 10 digits"}
    if not p.get("name", "").strip():
        return {"ok": False, "error": "Name is required"}
    if not is_valid_email(p.get("email", "")):
        return {"ok": False, "error": "Invalid email"}
    if not is_valid_phone(p.get("phone", "")):
        return {"ok": False, "error": "Phone must be 8 to 15 digits"}
    if not p.get("major", "").strip():
        return {"ok": False, "error": "Major is required"}
    try:
        level = int(p.get("level"))
        if level < 1 or level > 10:
            raise ValueError
    except (TypeError, ValueError):
        return {"ok": False, "error": "Level must be a number from 1 to 10"}

    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO students(student_id,name,email,phone,major,level) VALUES(?,?,?,?,?,?)",
            (p["student_id"], p["name"].strip(), p["email"], p["phone"], p["major"].strip(), level),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return {"ok": False, "error": "Student ID already exists"}
    conn.close()
    return {"ok": True}


def handle_update_student(p):
    if not is_valid_id(p.get("student_id", "")):
        return {"ok": False, "error": "Student ID must be 10 digits"}
    if not is_valid_email(p.get("email", "")):
        return {"ok": False, "error": "Invalid email"}
    if not is_valid_phone(p.get("phone", "")):
        return {"ok": False, "error": "Phone must be 8 to 15 digits"}
    try:
        level = int(p.get("level"))
    except (TypeError, ValueError):
        return {"ok": False, "error": "Level must be a number"}

    conn = get_conn()
    cur = conn.execute(
        "UPDATE students SET name=?,email=?,phone=?,major=?,level=? WHERE student_id=?",
        (p["name"].strip(), p["email"], p["phone"], p["major"].strip(), level, p["student_id"]),
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected == 0:
        return {"ok": False, "error": "Student not found"}
    return {"ok": True}


def handle_delete_student(p):
    sid = p.get("student_id", "")
    conn = get_conn()
    cur = conn.execute("DELETE FROM students WHERE student_id=?", (sid,))
    conn.execute("DELETE FROM enrollments WHERE student_id=?", (sid,))
    conn.execute("DELETE FROM attendance WHERE student_id=?", (sid,))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected == 0:
        return {"ok": False, "error": "Student not found"}
    return {"ok": True}


def handle_search_students(p):
    kw = "%" + p.get("keyword", "") + "%"
    conn = get_conn()
    rows = conn.execute(
        "SELECT student_id,name,email,phone,major,level FROM students "
        "WHERE student_id LIKE ? OR name LIKE ? OR major LIKE ? ORDER BY student_id",
        (kw, kw, kw),
    ).fetchall()
    conn.close()
    return {"ok": True, "data": [dict(r) for r in rows]}


def handle_list_courses(p):
    conn = get_conn()
    rows = conn.execute(
        "SELECT code,title,credits,instructor FROM courses ORDER BY code"
    ).fetchall()
    conn.close()
    return {"ok": True, "data": [dict(r) for r in rows]}


def handle_add_course(p):
    if not p.get("code", "").strip():
        return {"ok": False, "error": "Course code is required"}
    if not p.get("title", "").strip():
        return {"ok": False, "error": "Title is required"}
    try:
        credits = int(p.get("credits"))
        if credits < 1 or credits > 6:
            raise ValueError
    except (TypeError, ValueError):
        return {"ok": False, "error": "Credits must be a number from 1 to 6"}
    if not p.get("instructor", "").strip():
        return {"ok": False, "error": "Instructor is required"}

    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO courses(code,title,credits,instructor) VALUES(?,?,?,?)",
            (p["code"].strip().upper(), p["title"].strip(), credits, p["instructor"].strip()),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return {"ok": False, "error": "Course code already exists"}
    conn.close()
    return {"ok": True}


def handle_update_course(p):
    try:
        credits = int(p.get("credits"))
    except (TypeError, ValueError):
        return {"ok": False, "error": "Credits must be a number"}
    conn = get_conn()
    cur = conn.execute(
        "UPDATE courses SET title=?,credits=?,instructor=? WHERE code=?",
        (p["title"].strip(), credits, p["instructor"].strip(), p["code"].strip().upper()),
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected == 0:
        return {"ok": False, "error": "Course not found"}
    return {"ok": True}


def handle_delete_course(p):
    code = p.get("code", "").strip().upper()
    conn = get_conn()
    cur = conn.execute("DELETE FROM courses WHERE code=?", (code,))
    conn.execute("DELETE FROM enrollments WHERE course_code=?", (code,))
    conn.execute("DELETE FROM attendance WHERE course_code=?", (code,))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected == 0:
        return {"ok": False, "error": "Course not found"}
    return {"ok": True}


def handle_search_courses(p):
    kw = "%" + p.get("keyword", "") + "%"
    conn = get_conn()
    rows = conn.execute(
        "SELECT code,title,credits,instructor FROM courses "
        "WHERE code LIKE ? OR title LIKE ? OR instructor LIKE ? ORDER BY code",
        (kw, kw, kw),
    ).fetchall()
    conn.close()
    return {"ok": True, "data": [dict(r) for r in rows]}


def handle_enroll(p):
    sid = p.get("student_id", "")
    code = p.get("course_code", "").strip().upper()
    sem = p.get("semester", "").strip()
    if not sid or not code or not sem:
        return {"ok": False, "error": "All fields are required"}
    conn = get_conn()
    s = conn.execute("SELECT 1 FROM students WHERE student_id=?", (sid,)).fetchone()
    c = conn.execute("SELECT 1 FROM courses WHERE code=?", (code,)).fetchone()
    if not s:
        conn.close()
        return {"ok": False, "error": "Student not found"}
    if not c:
        conn.close()
        return {"ok": False, "error": "Course not found"}
    try:
        conn.execute(
            "INSERT INTO enrollments(student_id,course_code,semester) VALUES(?,?,?)",
            (sid, code, sem),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return {"ok": False, "error": "Student is already enrolled in this course this semester"}
    conn.close()
    return {"ok": True}


def handle_list_enrollments(p):
    conn = get_conn()
    rows = conn.execute(
        "SELECT e.student_id, s.name, e.course_code, c.title, e.semester "
        "FROM enrollments e "
        "LEFT JOIN students s ON s.student_id = e.student_id "
        "LEFT JOIN courses c ON c.code = e.course_code "
        "ORDER BY e.semester DESC, e.course_code"
    ).fetchall()
    conn.close()
    return {"ok": True, "data": [dict(r) for r in rows]}


def handle_unenroll(p):
    conn = get_conn()
    cur = conn.execute(
        "DELETE FROM enrollments WHERE student_id=? AND course_code=? AND semester=?",
        (p["student_id"], p["course_code"].upper(), p["semester"]),
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected == 0:
        return {"ok": False, "error": "Enrollment not found"}
    return {"ok": True}


def handle_mark_attendance(p):
    sid = p.get("student_id", "")
    code = p.get("course_code", "").strip().upper()
    adate = p.get("date", "")
    status = p.get("status", "")
    if not is_valid_date(adate):
        return {"ok": False, "error": "Date must be in YYYY-MM-DD format"}
    if status not in ("Present", "Absent"):
        return {"ok": False, "error": "Status must be Present or Absent"}
    conn = get_conn()
    ok = conn.execute(
        "SELECT 1 FROM enrollments WHERE student_id=? AND course_code=?",
        (sid, code),
    ).fetchone()
    if not ok:
        conn.close()
        return {"ok": False, "error": "Student is not enrolled in this course"}
    conn.execute(
        "INSERT INTO attendance(student_id,course_code,adate,status) VALUES(?,?,?,?)",
        (sid, code, adate, status),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


def handle_attendance_report(p):
    code = p.get("course_code", "").strip().upper()
    conn = get_conn()
    if code:
        rows = conn.execute(
            "SELECT a.student_id, s.name, a.course_code, a.adate, a.status "
            "FROM attendance a LEFT JOIN students s ON s.student_id=a.student_id "
            "WHERE a.course_code=? ORDER BY a.adate DESC",
            (code,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT a.student_id, s.name, a.course_code, a.adate, a.status "
            "FROM attendance a LEFT JOIN students s ON s.student_id=a.student_id "
            "ORDER BY a.adate DESC"
        ).fetchall()
    conn.close()
    return {"ok": True, "data": [dict(r) for r in rows]}


def handle_attendance_summary(p):
    code = p.get("course_code", "").strip().upper()
    conn = get_conn()
    if code:
        rows = conn.execute(
            "SELECT a.student_id, s.name, "
            "SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present_count, "
            "SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) AS absent_count "
            "FROM attendance a LEFT JOIN students s ON s.student_id=a.student_id "
            "WHERE a.course_code=? GROUP BY a.student_id ORDER BY s.name",
            (code,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT a.student_id, s.name, "
            "SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present_count, "
            "SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) AS absent_count "
            "FROM attendance a LEFT JOIN students s ON s.student_id=a.student_id "
            "GROUP BY a.student_id ORDER BY s.name"
        ).fetchall()
    conn.close()
    return {"ok": True, "data": [dict(r) for r in rows]}


HANDLERS = {
    "login": handle_login,
    "list_students": handle_list_students,
    "add_student": handle_add_student,
    "update_student": handle_update_student,
    "delete_student": handle_delete_student,
    "search_students": handle_search_students,
    "list_courses": handle_list_courses,
    "add_course": handle_add_course,
    "update_course": handle_update_course,
    "delete_course": handle_delete_course,
    "search_courses": handle_search_courses,
    "enroll": handle_enroll,
    "list_enrollments": handle_list_enrollments,
    "unenroll": handle_unenroll,
    "mark_attendance": handle_mark_attendance,
    "attendance_report": handle_attendance_report,
    "attendance_summary": handle_attendance_summary,
}


def recv_line(sock):
    buf = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            return None
        buf += chunk
        if b"\n" in buf:
            line, _ = buf.split(b"\n", 1)
            return line.decode("utf-8")


def client_handler(conn, addr):
    print(f"[+] Connected: {addr}")
    try:
        while True:
            raw = recv_line(conn)
            if raw is None:
                break
            try:
                req = json.loads(raw)
                action = req.get("action")
                payload = req.get("payload", {})
                handler = HANDLERS.get(action)
                if not handler:
                    resp = {"ok": False, "error": f"Unknown action: {action}"}
                else:
                    resp = handler(payload)
            except json.JSONDecodeError:
                resp = {"ok": False, "error": "Bad JSON"}
            except Exception as ex:
                resp = {"ok": False, "error": f"Server error: {ex}"}
            conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
    finally:
        conn.close()
        print(f"[-] Disconnected: {addr}")


def main():
    init_db()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)
    print(f"Smart SMS server listening on {HOST}:{PORT}")
    try:
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=client_handler, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        s.close()


if __name__ == "__main__":
    main()
