# Smart Student Management & Attendance System

> CS 516 — Advanced Programming Language · 2nd Semester 2025/2026
> College of Computer Science and Information Technology, Imam Abdulrahman Bin Faisal University

A client–server application for managing students, courses, enrollments, and class attendance. Built **twice** — once in **Python** and once in **C++** — to compare two languages from different paradigms working on the exact same problem.

---

## Team

| Name | Student ID | Role |
|---|---|---|
| Ahmed Mabkhot Al-Awlaqi | 2220007240 | Team Leader |
| Abdulaziz Alghamdi | 2220003178 | Member |
| Abdullah Alsaedi | 2220002306 | Member |

---

## What's in the box

```
CS516_Project/
├── Python/              # Tkinter GUI client + TCP server + SQLite
│   ├── server.py
│   └── client.py
├── Cpp/                 # OOP server + console client (Winsock, flat files)
│   ├── common.h
│   ├── server.cpp
│   ├── client.cpp
│   ├── server.exe       # pre-built (MinGW-w64 g++ 14.2, static)
│   └── client.exe
├── Screenshots/         # 21 figures used in the report
└── Report/
    └── CS516_Project_Report.docx
```

## Features

Both implementations cover the same surface area:

- **Login** with two roles (`admin`, `instructor`)
- **Students** — full CRUD + search
- **Courses** — full CRUD + search
- **Enrollment** — enroll/unenroll students per semester
- **Attendance** — mark Present/Absent per student per course per day
- **Reports** — full attendance log and per-course summary

All input validation runs on the server, so both clients get it for free.

## Default accounts

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | admin (full access) |
| `ahmed` | `ahmed123` | instructor |
| `abdullah` | `abdullah123` | instructor |

---

## How to run

You need **two terminals open at the same time** for each side — one for the server, one for the client.

### Python version

```powershell
cd Python
python server.py        # terminal 1 — listens on 127.0.0.1:5055
python client.py        # terminal 2 — opens the Tkinter GUI
```

Requires Python 3.10+. No external packages.

### C++ version

```powershell
cd Cpp
.\server.exe            # terminal 1 — listens on 127.0.0.1:5066
.\client.exe            # terminal 2 — console UI
```

To rebuild from source (Windows + MinGW-w64):

```powershell
g++ -std=c++17 -O2 -static -o server.exe server.cpp -lws2_32
g++ -std=c++17 -O2 -static -o client.exe client.cpp -lws2_32
```

---

## Architecture at a glance

```
┌─────────────┐  TCP + line protocol  ┌──────────────┐
│   Client    │ ────────────────────▶ │    Server    │
│ (GUI / TUI) │ ◀──────────────────── │ (validation) │
└─────────────┘                       └──────┬───────┘
                                             │
                              ┌──────────────┴──────────────┐
                              │                             │
                      Python: SQLite                C++: TAB-separated files
```

- **Python** uses JSON over a newline-delimited TCP socket.
- **C++** uses a custom `ACTION|key=value|...\n` line protocol (defined in `common.h`).

## Comparison summary

| | Python | C++ |
|---|---|---|
| **Paradigm** | Multi-paradigm (OOP + procedural + functional) | OOP + procedural |
| **Typing** | Dynamic | Static |
| **Storage** | SQLite | Flat TAB files |
| **Memory** | Reference counting + GC | RAII (manual but rescued) |
| **Networking** | `socket` + `threading` | Winsock2 + `std::thread` |
| **Build step** | None | `g++ … -lws2_32` |

Full comparison — including syntax, dependencies, paradigm, memory management, and four side-by-side function implementations — is in `Report/CS516_Project_Report.docx`.

---

## License

This is academic coursework, submitted to Dr. Dhiaa at CCSIT-IAU. Use it as a reference, not as a copy-paste source for your own coursework.
