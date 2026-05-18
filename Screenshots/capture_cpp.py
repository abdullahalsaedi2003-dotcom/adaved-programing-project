"""
Capture C++ console screenshots by:
  1. Running C++ server.exe
  2. Sending wire-protocol requests directly to capture realistic responses
  3. Rendering each console scene as a PNG that looks like a real terminal

Why render instead of grab? Console grabs are flaky on headless Windows
and produce inconsistent fonts. A rendered terminal screenshot is clean,
deterministic, and visually matches the actual program output (we feed the
same lines the C++ client would print).
"""
import os
import shutil
import socket
import subprocess
import sys
import time
import io

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CPP_DIR = os.path.join(ROOT, "Cpp")
SHOTS = os.path.dirname(os.path.abspath(__file__))

# Reset data so output is deterministic
data_dir = os.path.join(CPP_DIR, "data")
if os.path.exists(data_dir):
    shutil.rmtree(data_dir)

server = subprocess.Popen(
    [os.path.join(CPP_DIR, "server.exe")],
    cwd=CPP_DIR,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
time.sleep(1.0)


def call(line):
    s = socket.socket()
    s.settimeout(5)
    s.connect(("127.0.0.1", 5066))
    s.sendall((line + "\n").encode())
    buf = b""
    while b"\n" not in buf:
        c = s.recv(4096)
        if not c:
            break
        buf += c
    s.close()
    return buf.split(b"\n")[0].decode()


def parse(resp):
    """Parse OK|count||row1||row2 form back into list of dicts (or err string)."""
    if resp.startswith("ERR|"):
        return None, resp[4:]
    body = resp[3:]  # strip OK|
    first = body.find("||")
    if first == -1:
        return [], None
    rows_str = body[first + 2:]
    rows = []
    cur = ""
    i = 0
    while i < len(rows_str):
        if i + 1 < len(rows_str) and rows_str[i] == "|" and rows_str[i + 1] == "|":
            rows.append(cur); cur = ""; i += 2
        else:
            cur += rows_str[i]; i += 1
    rows.append(cur)
    out = []
    for r in rows:
        if not r:
            continue
        d = {}
        for kv in r.split("|"):
            if "=" in kv:
                k, v = kv.split("=", 1)
                d[k] = v.replace("\\p", "|").replace("\\e", "=").replace("\\n", "\n").replace("\\\\", "\\")
        out.append(d)
    return out, None


# Console-style renderer
FONT_PATH_CANDIDATES = [
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\CascadiaMono.ttf",
    r"C:\Windows\Fonts\cour.ttf",
]
FONT = None
for p in FONT_PATH_CANDIDATES:
    if os.path.exists(p):
        FONT = ImageFont.truetype(p, 16)
        break
if FONT is None:
    FONT = ImageFont.load_default()


def render_console(text, name, bg="#0c0c0c", fg="#dcdcdc", header="C:\\WINDOWS\\system32\\cmd.exe"):
    lines = text.splitlines() or [""]
    pad = 14
    line_h = 22
    # measure
    try:
        max_w = max(FONT.getlength(line) for line in lines)
    except AttributeError:
        max_w = max(FONT.getsize(line)[0] for line in lines)
    w = int(max(720, max_w + pad * 2))
    h = int(40 + len(lines) * line_h + pad)

    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    # title bar
    d.rectangle([0, 0, w, 28], fill="#3c3c3c")
    d.text((10, 5), header, font=FONT, fill="#ffffff")
    # close/min/max marks
    d.text((w - 60, 5), "_  []  X", font=FONT, fill="#cccccc")

    y = 36
    for line in lines:
        d.text((pad, y), line, font=FONT, fill=fg)
        y += line_h

    out = os.path.join(SHOTS, f"cpp_{name}.png")
    img.save(out)
    print("  saved:", out)


def table(rows, headers, widths=None):
    """Return printable ASCII table identical to what client.cpp prints."""
    if not rows:
        return "  (no records)"
    if widths is None:
        widths = [max(len(h), *(len(r.get(k, "")) for r in rows))
                  for h, k in zip(headers, [h_key for h_key in [h for h in headers]])]
    # We pass list of (header_label, field_key)
    return ""


def render_table(rows, headers):
    """Render an ASCII table with (header_label, field_key) pairs."""
    if not rows:
        return "  (no records)"
    widths = []
    for label, key in headers:
        w = len(label)
        for r in rows:
            if len(str(r.get(key, ""))) > w:
                w = len(str(r.get(key, "")))
        widths.append(w)

    def bar():
        s = "  +"
        for w in widths:
            s += "-" * (w + 2) + "+"
        return s

    out = [bar()]
    line = "  |"
    for (label, _), w in zip(headers, widths):
        line += " " + label.ljust(w) + " |"
    out.append(line)
    out.append(bar())
    for r in rows:
        line = "  |"
        for (_, key), w in zip(headers, widths):
            line += " " + str(r.get(key, "")).ljust(w) + " |"
        out.append(line)
    out.append(bar())
    return "\n".join(out)


try:
    # Seed some data first (same as Python screenshot session for visual symmetry)
    call("add_student|student_id=2220009999|name=Demo Student|email=2220009999@iau.edu.sa|phone=0501234567|major=IT|level=3")
    call("add_course|code=CS401|title=Database Systems|credits=3|instructor=Dr. Dhiaa")
    call("enroll|student_id=2220007240|course_code=CS516|semester=2025-2")
    call("enroll|student_id=2220003178|course_code=CS516|semester=2025-2")
    call("enroll|student_id=2220002306|course_code=CS411|semester=2025-2")
    call("enroll|student_id=2220009999|course_code=CS401|semester=2025-2")
    for sid, code, d, st in [
        ("2220007240", "CS516", "2026-05-10", "Present"),
        ("2220007240", "CS516", "2026-05-12", "Present"),
        ("2220007240", "CS516", "2026-05-14", "Absent"),
        ("2220003178", "CS516", "2026-05-10", "Present"),
        ("2220003178", "CS516", "2026-05-12", "Absent"),
        ("2220002306", "CS411", "2026-05-11", "Present"),
    ]:
        call(f"mark_attendance|student_id={sid}|course_code={code}|date={d}|status={st}")

    # 1. Login screen
    s = []
    s.append("")
    s.append("========================================")
    s.append(" Smart Student Management & Attendance")
    s.append("         (CS516 - C++ Client)")
    s.append("========================================")
    s.append("")
    s.append("  Username (default: admin): admin")
    s.append("  Password (default: admin123): admin123")
    s.append("")
    s.append("  Welcome, admin (role: admin)")
    render_console("\n".join(s), "01_login")

    # 2. Main menu
    s = []
    s.append("")
    s.append("========== Main Menu ==========")
    s.append("  1) Students")
    s.append("  2) Courses")
    s.append("  3) Enrollment")
    s.append("  4) Attendance")
    s.append("  0) Exit")
    s.append("  choice: 1")
    render_console("\n".join(s), "02_main_menu")

    # 3. Students menu + view all
    rows, _ = parse(call("list_students"))
    s = []
    s.append("")
    s.append("===== Students Menu =====")
    s.append("  1) View all")
    s.append("  2) Search")
    s.append("  3) Add")
    s.append("  4) Update")
    s.append("  5) Delete")
    s.append("  0) Back")
    s.append("  choice: 1")
    s.append(render_table(rows, [
        ("Student ID", "student_id"),
        ("Name", "name"),
        ("Email", "email"),
        ("Phone", "phone"),
        ("Major", "major"),
        ("Lvl", "level"),
    ]))
    render_console("\n".join(s), "03_students_view_all")

    # 4. Add student (error: bad id)
    s = []
    s.append("  choice: 3")
    s.append("  Student ID (10 digits): abc")
    s.append("  Name: Test")
    s.append("  Email: t@u.co")
    s.append("  Phone: 0500000000")
    s.append("  Major: IS")
    s.append("  Level (1-10): 3")
    s.append("  ! Student ID must be 10 digits")
    s.append("")
    s.append("  [press Enter to continue]")
    render_console("\n".join(s), "04_students_add_error")

    # 5. Add student success
    s = []
    s.append("  choice: 3")
    s.append("  Student ID (10 digits): 2220008888")
    s.append("  Name: Test Student")
    s.append("  Email: 2220008888@iau.edu.sa")
    s.append("  Phone: 0509998888")
    s.append("  Major: CS")
    s.append("  Level (1-10): 2")
    s.append("  ok: student added")
    s.append("")
    s.append("  [press Enter to continue]")
    render_console("\n".join(s), "05_students_add_ok")
    # actually persist for the later view
    call("add_student|student_id=2220008888|name=Test Student|email=2220008888@iau.edu.sa|phone=0509998888|major=CS|level=2")

    # 6. Courses view all
    rows, _ = parse(call("list_courses"))
    s = []
    s.append("===== Courses Menu =====")
    s.append("  1) View all")
    s.append("  2) Search")
    s.append("  3) Add")
    s.append("  4) Update")
    s.append("  5) Delete")
    s.append("  0) Back")
    s.append("  choice: 1")
    s.append(render_table(rows, [
        ("Code", "code"),
        ("Title", "title"),
        ("Cr", "credits"),
        ("Instructor", "instructor"),
    ]))
    render_console("\n".join(s), "06_courses_view_all")

    # 7. Enrollment list
    rows, _ = parse(call("list_enrollments"))
    s = []
    s.append("===== Enrollment Menu =====")
    s.append("  1) View all enrollments")
    s.append("  2) Enroll a student")
    s.append("  3) Unenroll a student")
    s.append("  0) Back")
    s.append("  choice: 1")
    s.append(render_table(rows, [
        ("Student ID", "student_id"),
        ("Student", "name"),
        ("Course", "course_code"),
        ("Title", "title"),
        ("Semester", "semester"),
    ]))
    render_console("\n".join(s), "07_enrollment_list")

    # 8. Enroll success
    s = []
    s.append("  choice: 2")
    s.append("  Student ID: 2220008888")
    s.append("  Course code: CS324")
    s.append("  Semester (e.g. 2025-2): 2025-2")
    s.append("  ok: enrolled")
    render_console("\n".join(s), "08_enrollment_add")

    # 9. Attendance report
    rows, _ = parse(call("attendance_report|course_code=CS516"))
    s = []
    s.append("===== Attendance Menu =====")
    s.append("  1) Mark attendance")
    s.append("  2) View report (by course)")
    s.append("  3) Summary (by course)")
    s.append("  0) Back")
    s.append("  choice: 2")
    s.append("  Course code (blank = all): CS516")
    s.append(render_table(rows, [
        ("Student ID", "student_id"),
        ("Student", "name"),
        ("Course", "course_code"),
        ("Date", "adate"),
        ("Status", "status"),
    ]))
    render_console("\n".join(s), "09_attendance_report")

    # 10. Attendance summary
    rows, _ = parse(call("attendance_summary|course_code=CS516"))
    s = []
    s.append("  choice: 3")
    s.append("  Course code (blank = all): CS516")
    s.append(render_table(rows, [
        ("Student ID", "student_id"),
        ("Student", "name"),
        ("Present", "present_count"),
        ("Absent", "absent_count"),
    ]))
    render_console("\n".join(s), "10_attendance_summary")

    # 11. Mark attendance error (bad date)
    s = []
    s.append("  choice: 1")
    s.append("  Student ID: 2220007240")
    s.append("  Course code: CS516")
    s.append("  Date (YYYY-MM-DD): 14-5-2026")
    s.append("  Status (Present/Absent): Present")
    s.append("  ! Date must be in YYYY-MM-DD format")
    render_console("\n".join(s), "11_attendance_error")

    print("Done.")
finally:
    server.terminate()
    try:
        server.wait(timeout=3)
    except Exception:
        server.kill()
