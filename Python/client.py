"""
Smart Student Management & Attendance System - Client (Tkinter GUI)
CS516 - Advanced Programming Language
"""
import socket
import json
import tkinter as tk
from tkinter import ttk, messagebox

HOST = "127.0.0.1"
PORT = 5055


class NetClient:
    def __init__(self):
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, PORT))

    def send(self, action, payload=None):
        if self.sock is None:
            self.connect()
        req = {"action": action, "payload": payload or {}}
        self.sock.sendall((json.dumps(req) + "\n").encode("utf-8"))
        buf = b""
        while b"\n" not in buf:
            chunk = self.sock.recv(8192)
            if not chunk:
                break
            buf += chunk
        line, _ = buf.split(b"\n", 1)
        return json.loads(line.decode("utf-8"))

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None


net = NetClient()


# ----------- Login Window -----------
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart SMS - Login")
        self.geometry("420x320")
        self.resizable(False, False)
        self.configure(bg="#f0f4f8")

        tk.Label(self, text="Smart Student Management", font=("Segoe UI", 16, "bold"),
                 bg="#f0f4f8", fg="#1f3a5f").pack(pady=(28, 4))
        tk.Label(self, text="& Attendance System", font=("Segoe UI", 12),
                 bg="#f0f4f8", fg="#1f3a5f").pack()
        tk.Label(self, text="Please sign in to continue", font=("Segoe UI", 9, "italic"),
                 bg="#f0f4f8", fg="#666").pack(pady=(6, 18))

        frm = tk.Frame(self, bg="#f0f4f8")
        frm.pack()
        tk.Label(frm, text="Username", bg="#f0f4f8").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        self.user_var = tk.StringVar(value="admin")
        tk.Entry(frm, textvariable=self.user_var, width=24).grid(row=0, column=1, pady=6)
        tk.Label(frm, text="Password", bg="#f0f4f8").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        self.pwd_var = tk.StringVar(value="admin123")
        tk.Entry(frm, textvariable=self.pwd_var, show="*", width=24).grid(row=1, column=1, pady=6)

        tk.Button(self, text="Sign In", width=18, bg="#1f6feb", fg="white",
                  font=("Segoe UI", 10, "bold"), command=self.do_login).pack(pady=18)
        tk.Label(self, text="(default: admin / admin123)", font=("Segoe UI", 8),
                 bg="#f0f4f8", fg="#888").pack()

        self.bind("<Return>", lambda e: self.do_login())
        self.role = None

    def do_login(self):
        u = self.user_var.get().strip()
        p = self.pwd_var.get()
        if not u or not p:
            messagebox.showerror("Error", "Enter username and password")
            return
        try:
            net.connect()
            r = net.send("login", {"username": u, "password": p})
        except ConnectionRefusedError:
            messagebox.showerror("Connection", "Cannot reach the server. Start server.py first.")
            return
        if r.get("ok"):
            self.role = r["role"]
            self.destroy()
        else:
            messagebox.showerror("Login failed", r.get("error", "Unknown error"))


# ----------- Main App -----------
class MainApp(tk.Tk):
    def __init__(self, role):
        super().__init__()
        self.role = role
        self.title(f"Smart SMS  -  Signed in as: {role}")
        self.geometry("1000x620")
        self.configure(bg="#ffffff")

        # Header
        header = tk.Frame(self, bg="#1f3a5f", height=56)
        header.pack(fill="x")
        tk.Label(header, text=" Smart Student Management & Attendance System",
                 bg="#1f3a5f", fg="white", font=("Segoe UI", 14, "bold")).pack(side="left", padx=14, pady=12)
        tk.Label(header, text=f"Role: {role.upper()} ",
                 bg="#1f3a5f", fg="#9bd1ff", font=("Segoe UI", 10)).pack(side="right", padx=14)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.students_tab = StudentsTab(nb, role)
        self.courses_tab = CoursesTab(nb, role)
        self.enroll_tab = EnrollmentTab(nb, role)
        self.att_tab = AttendanceTab(nb, role)
        nb.add(self.students_tab, text="  Students  ")
        nb.add(self.courses_tab, text="  Courses  ")
        nb.add(self.enroll_tab, text="  Enrollment  ")
        nb.add(self.att_tab, text="  Attendance  ")

        if role != "admin":
            # instructors only mark attendance + view; restrict add/update/delete of students & courses
            self.students_tab.set_readonly()
            self.courses_tab.set_readonly()
            self.enroll_tab.set_readonly()


class StudentsTab(tk.Frame):
    COLS = ("student_id", "name", "email", "phone", "major", "level")

    def __init__(self, master, role):
        super().__init__(master, bg="#fafafa")
        self.role = role

        form = tk.LabelFrame(self, text="Student Details", bg="#fafafa", padx=10, pady=8)
        form.pack(fill="x", padx=8, pady=8)

        self.vars = {c: tk.StringVar() for c in self.COLS}
        labels = ["Student ID", "Name", "Email", "Phone", "Major", "Level"]
        for i, (key, lbl) in enumerate(zip(self.COLS, labels)):
            tk.Label(form, text=lbl, bg="#fafafa").grid(row=i // 3, column=(i % 3) * 2, sticky="e", padx=4, pady=4)
            tk.Entry(form, textvariable=self.vars[key], width=22).grid(row=i // 3, column=(i % 3) * 2 + 1, padx=4, pady=4)

        btns = tk.Frame(self, bg="#fafafa")
        btns.pack(fill="x", padx=8)
        self.btn_view = tk.Button(btns, text="View All", width=12, command=self.view_all)
        self.btn_search = tk.Button(btns, text="Search", width=12, command=self.search)
        self.btn_add = tk.Button(btns, text="Add", width=12, bg="#2ea043", fg="white", command=self.add)
        self.btn_upd = tk.Button(btns, text="Update", width=12, bg="#1f6feb", fg="white", command=self.update)
        self.btn_del = tk.Button(btns, text="Delete", width=12, bg="#cf222e", fg="white", command=self.delete)
        self.btn_clear = tk.Button(btns, text="Clear", width=12, command=self.clear)
        for b in (self.btn_view, self.btn_search, self.btn_add, self.btn_upd, self.btn_del, self.btn_clear):
            b.pack(side="left", padx=4, pady=6)

        self.tree = ttk.Treeview(self, columns=self.COLS, show="headings", height=14)
        for c, lbl in zip(self.COLS, labels):
            self.tree.heading(c, text=lbl)
            self.tree.column(c, width=140, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.view_all()

    def set_readonly(self):
        for b in (self.btn_add, self.btn_upd, self.btn_del):
            b.configure(state="disabled")

    def collect(self):
        return {k: v.get().strip() for k, v in self.vars.items()}

    def clear(self):
        for v in self.vars.values():
            v.set("")

    def populate(self, rows):
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=tuple(r.get(c, "") for c in self.COLS))

    def view_all(self):
        r = net.send("list_students")
        if r.get("ok"):
            self.populate(r["data"])
        else:
            messagebox.showerror("Error", r.get("error", "Failed"))

    def search(self):
        kw = self.vars["student_id"].get().strip() or self.vars["name"].get().strip() or self.vars["major"].get().strip()
        r = net.send("search_students", {"keyword": kw})
        if r.get("ok"):
            self.populate(r["data"])

    def add(self):
        p = self.collect()
        r = net.send("add_student", p)
        if r.get("ok"):
            messagebox.showinfo("Success", "Student added.")
            self.view_all()
            self.clear()
        else:
            messagebox.showerror("Error", r.get("error", "Failed"))

    def update(self):
        p = self.collect()
        r = net.send("update_student", p)
        if r.get("ok"):
            messagebox.showinfo("Success", "Student updated.")
            self.view_all()
        else:
            messagebox.showerror("Error", r.get("error", "Failed"))

    def delete(self):
        sid = self.vars["student_id"].get().strip()
        if not sid:
            messagebox.showwarning("Select", "Pick a student first.")
            return
        if not messagebox.askyesno("Confirm", f"Delete student {sid}?"):
            return
        r = net.send("delete_student", {"student_id": sid})
        if r.get("ok"):
            messagebox.showinfo("Deleted", "Student removed.")
            self.view_all()
            self.clear()
        else:
            messagebox.showerror("Error", r.get("error", "Failed"))

    def on_select(self, _ev):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        for c, v in zip(self.COLS, vals):
            self.vars[c].set(v)


class CoursesTab(tk.Frame):
    COLS = ("code", "title", "credits", "instructor")

    def __init__(self, master, role):
        super().__init__(master, bg="#fafafa")
        self.role = role

        form = tk.LabelFrame(self, text="Course Details", bg="#fafafa", padx=10, pady=8)
        form.pack(fill="x", padx=8, pady=8)
        self.vars = {c: tk.StringVar() for c in self.COLS}
        labels = ["Code", "Title", "Credits", "Instructor"]
        for i, (key, lbl) in enumerate(zip(self.COLS, labels)):
            tk.Label(form, text=lbl, bg="#fafafa").grid(row=i // 2, column=(i % 2) * 2, sticky="e", padx=4, pady=4)
            tk.Entry(form, textvariable=self.vars[key], width=28).grid(row=i // 2, column=(i % 2) * 2 + 1, padx=4, pady=4)

        btns = tk.Frame(self, bg="#fafafa")
        btns.pack(fill="x", padx=8)
        self.btn_view = tk.Button(btns, text="View All", width=12, command=self.view_all)
        self.btn_search = tk.Button(btns, text="Search", width=12, command=self.search)
        self.btn_add = tk.Button(btns, text="Add", width=12, bg="#2ea043", fg="white", command=self.add)
        self.btn_upd = tk.Button(btns, text="Update", width=12, bg="#1f6feb", fg="white", command=self.update)
        self.btn_del = tk.Button(btns, text="Delete", width=12, bg="#cf222e", fg="white", command=self.delete)
        self.btn_clear = tk.Button(btns, text="Clear", width=12, command=self.clear)
        for b in (self.btn_view, self.btn_search, self.btn_add, self.btn_upd, self.btn_del, self.btn_clear):
            b.pack(side="left", padx=4, pady=6)

        self.tree = ttk.Treeview(self, columns=self.COLS, show="headings", height=14)
        for c, lbl in zip(self.COLS, labels):
            self.tree.heading(c, text=lbl)
            self.tree.column(c, width=180, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.view_all()

    def set_readonly(self):
        for b in (self.btn_add, self.btn_upd, self.btn_del):
            b.configure(state="disabled")

    def collect(self):
        return {k: v.get().strip() for k, v in self.vars.items()}

    def clear(self):
        for v in self.vars.values():
            v.set("")

    def populate(self, rows):
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=tuple(r.get(c, "") for c in self.COLS))

    def view_all(self):
        r = net.send("list_courses")
        if r.get("ok"):
            self.populate(r["data"])

    def search(self):
        kw = self.vars["code"].get().strip() or self.vars["title"].get().strip() or self.vars["instructor"].get().strip()
        r = net.send("search_courses", {"keyword": kw})
        if r.get("ok"):
            self.populate(r["data"])

    def add(self):
        r = net.send("add_course", self.collect())
        if r.get("ok"):
            messagebox.showinfo("Success", "Course added.")
            self.view_all()
            self.clear()
        else:
            messagebox.showerror("Error", r.get("error", "Failed"))

    def update(self):
        r = net.send("update_course", self.collect())
        if r.get("ok"):
            messagebox.showinfo("Success", "Course updated.")
            self.view_all()
        else:
            messagebox.showerror("Error", r.get("error", "Failed"))

    def delete(self):
        code = self.vars["code"].get().strip()
        if not code:
            messagebox.showwarning("Select", "Pick a course first.")
            return
        if not messagebox.askyesno("Confirm", f"Delete course {code}?"):
            return
        r = net.send("delete_course", {"code": code})
        if r.get("ok"):
            messagebox.showinfo("Deleted", "Course removed.")
            self.view_all()
            self.clear()
        else:
            messagebox.showerror("Error", r.get("error", "Failed"))

    def on_select(self, _ev):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        for c, v in zip(self.COLS, vals):
            self.vars[c].set(v)


class EnrollmentTab(tk.Frame):
    COLS = ("student_id", "name", "course_code", "title", "semester")

    def __init__(self, master, role):
        super().__init__(master, bg="#fafafa")
        self.role = role

        form = tk.LabelFrame(self, text="Enroll a Student", bg="#fafafa", padx=10, pady=8)
        form.pack(fill="x", padx=8, pady=8)
        self.sid = tk.StringVar()
        self.code = tk.StringVar()
        self.sem = tk.StringVar(value="2025-2 (Spring)")
        tk.Label(form, text="Student ID", bg="#fafafa").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        tk.Entry(form, textvariable=self.sid, width=22).grid(row=0, column=1, padx=4, pady=4)
        tk.Label(form, text="Course Code", bg="#fafafa").grid(row=0, column=2, sticky="e", padx=4, pady=4)
        tk.Entry(form, textvariable=self.code, width=22).grid(row=0, column=3, padx=4, pady=4)
        tk.Label(form, text="Semester", bg="#fafafa").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        tk.Entry(form, textvariable=self.sem, width=22).grid(row=1, column=1, padx=4, pady=4)

        btns = tk.Frame(self, bg="#fafafa")
        btns.pack(fill="x", padx=8)
        self.btn_enroll = tk.Button(btns, text="Enroll", width=14, bg="#2ea043", fg="white", command=self.enroll)
        self.btn_unenroll = tk.Button(btns, text="Unenroll Selected", width=18, bg="#cf222e", fg="white", command=self.unenroll)
        self.btn_view = tk.Button(btns, text="Refresh", width=12, command=self.view_all)
        for b in (self.btn_enroll, self.btn_unenroll, self.btn_view):
            b.pack(side="left", padx=4, pady=6)

        self.tree = ttk.Treeview(self, columns=self.COLS, show="headings", height=14)
        for c, lbl in zip(self.COLS, ("Student ID", "Student Name", "Course Code", "Title", "Semester")):
            self.tree.heading(c, text=lbl)
            self.tree.column(c, width=170, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.view_all()

    def set_readonly(self):
        for b in (self.btn_enroll, self.btn_unenroll):
            b.configure(state="disabled")

    def populate(self, rows):
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=tuple(r.get(c, "") for c in self.COLS))

    def view_all(self):
        r = net.send("list_enrollments")
        if r.get("ok"):
            self.populate(r["data"])

    def enroll(self):
        r = net.send("enroll", {"student_id": self.sid.get().strip(),
                                "course_code": self.code.get().strip(),
                                "semester": self.sem.get().strip()})
        if r.get("ok"):
            messagebox.showinfo("Success", "Student enrolled.")
            self.view_all()
        else:
            messagebox.showerror("Error", r.get("error", "Failed"))

    def unenroll(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Pick an enrollment row first.")
            return
        v = self.tree.item(sel[0], "values")
        if not messagebox.askyesno("Confirm", f"Unenroll {v[0]} from {v[2]}?"):
            return
        r = net.send("unenroll", {"student_id": v[0], "course_code": v[2], "semester": v[4]})
        if r.get("ok"):
            messagebox.showinfo("Done", "Enrollment removed.")
            self.view_all()
        else:
            messagebox.showerror("Error", r.get("error", "Failed"))

    def on_select(self, _ev):
        sel = self.tree.selection()
        if not sel:
            return
        v = self.tree.item(sel[0], "values")
        self.sid.set(v[0])
        self.code.set(v[2])
        self.sem.set(v[4])


class AttendanceTab(tk.Frame):
    COLS = ("student_id", "name", "course_code", "adate", "status")
    SUM_COLS = ("student_id", "name", "present_count", "absent_count")

    def __init__(self, master, role):
        super().__init__(master, bg="#fafafa")
        self.role = role

        form = tk.LabelFrame(self, text="Mark Attendance", bg="#fafafa", padx=10, pady=8)
        form.pack(fill="x", padx=8, pady=8)
        self.sid = tk.StringVar()
        self.code = tk.StringVar()
        self.adate = tk.StringVar()
        self.status = tk.StringVar(value="Present")

        tk.Label(form, text="Student ID", bg="#fafafa").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        tk.Entry(form, textvariable=self.sid, width=18).grid(row=0, column=1, padx=4, pady=4)
        tk.Label(form, text="Course Code", bg="#fafafa").grid(row=0, column=2, sticky="e", padx=4, pady=4)
        tk.Entry(form, textvariable=self.code, width=14).grid(row=0, column=3, padx=4, pady=4)
        tk.Label(form, text="Date (YYYY-MM-DD)", bg="#fafafa").grid(row=0, column=4, sticky="e", padx=4, pady=4)
        tk.Entry(form, textvariable=self.adate, width=14).grid(row=0, column=5, padx=4, pady=4)
        tk.Label(form, text="Status", bg="#fafafa").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        ttk.Combobox(form, textvariable=self.status, values=["Present", "Absent"], width=15, state="readonly").grid(row=1, column=1, padx=4, pady=4)

        btns = tk.Frame(self, bg="#fafafa")
        btns.pack(fill="x", padx=8)
        tk.Button(btns, text="Mark", width=12, bg="#2ea043", fg="white", command=self.mark).pack(side="left", padx=4, pady=6)
        tk.Button(btns, text="Full Report", width=14, command=self.full_report).pack(side="left", padx=4, pady=6)
        tk.Button(btns, text="Summary by Course", width=18, command=self.summary).pack(side="left", padx=4, pady=6)

        self.tree = ttk.Treeview(self, columns=self.COLS, show="headings", height=14)
        for c, lbl in zip(self.COLS, ("Student ID", "Student Name", "Course", "Date", "Status")):
            self.tree.heading(c, text=lbl)
            self.tree.column(c, width=150, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        self.full_report()

    def set_readonly(self):
        pass  # instructors should mark attendance

    def mark(self):
        r = net.send("mark_attendance", {
            "student_id": self.sid.get().strip(),
            "course_code": self.code.get().strip(),
            "date": self.adate.get().strip(),
            "status": self.status.get(),
        })
        if r.get("ok"):
            messagebox.showinfo("Saved", "Attendance recorded.")
            self.full_report()
        else:
            messagebox.showerror("Error", r.get("error", "Failed"))

    def full_report(self):
        # switch headings back if needed
        self.tree["columns"] = self.COLS
        for c, lbl in zip(self.COLS, ("Student ID", "Student Name", "Course", "Date", "Status")):
            self.tree.heading(c, text=lbl)
            self.tree.column(c, width=150, anchor="w")
        r = net.send("attendance_report", {"course_code": self.code.get().strip()})
        if r.get("ok"):
            self.tree.delete(*self.tree.get_children())
            for row in r["data"]:
                self.tree.insert("", "end", values=tuple(row.get(c, "") for c in self.COLS))

    def summary(self):
        self.tree["columns"] = self.SUM_COLS
        for c, lbl in zip(self.SUM_COLS, ("Student ID", "Student Name", "Present", "Absent")):
            self.tree.heading(c, text=lbl)
            self.tree.column(c, width=170, anchor="w")
        r = net.send("attendance_summary", {"course_code": self.code.get().strip()})
        if r.get("ok"):
            self.tree.delete(*self.tree.get_children())
            for row in r["data"]:
                self.tree.insert("", "end", values=tuple(row.get(c, "") for c in self.SUM_COLS))


def main():
    login = LoginWindow()
    login.mainloop()
    if not login.role:
        return
    app = MainApp(login.role)
    app.mainloop()


if __name__ == "__main__":
    main()
