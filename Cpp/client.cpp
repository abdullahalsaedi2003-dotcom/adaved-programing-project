// client.cpp - Smart Student Management & Attendance System (Console Client, C++)
// CS516 - Advanced Programming Language
//
// Build (Windows, MinGW-w64):
//   g++ -std=c++17 -O2 -static -o client.exe client.cpp -lws2_32

#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#include "common.h"

#include <iomanip>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

#pragma comment(lib, "ws2_32.lib")

using netproto::Request;
using netproto::Response;
using std::cout;
using std::cin;
using std::endl;
using std::string;
using std::vector;

constexpr const char* HOST = "127.0.0.1";
constexpr int PORT = 5066;

class Net {
public:
    Net() {
        WSADATA wsa;
        WSAStartup(MAKEWORD(2, 2), &wsa);
        sock_ = INVALID_SOCKET;
    }
    ~Net() {
        if (sock_ != INVALID_SOCKET) closesocket(sock_);
        WSACleanup();
    }
    bool connectServer() {
        sock_ = socket(AF_INET, SOCK_STREAM, 0);
        if (sock_ == INVALID_SOCKET) return false;
        sockaddr_in a{};
        a.sin_family = AF_INET;
        a.sin_port = htons(PORT);
        inet_pton(AF_INET, HOST, &a.sin_addr);
        if (connect(sock_, (sockaddr*)&a, sizeof(a)) == SOCKET_ERROR) {
            closesocket(sock_); sock_ = INVALID_SOCKET; return false;
        }
        return true;
    }
    Response send(const Request& q) {
        string s = q.encode();
        ::send(sock_, s.c_str(), (int)s.size(), 0);
        string buf;
        char tmp[4096];
        while (buf.find('\n') == string::npos) {
            int n = recv(sock_, tmp, sizeof(tmp), 0);
            if (n <= 0) break;
            buf.append(tmp, n);
        }
        auto nl = buf.find('\n');
        return Response::decode(buf.substr(0, nl));
    }
private:
    SOCKET sock_;
};

// -------------------- UI helpers --------------------
static string readLine(const string& prompt) {
    cout << prompt;
    string s;
    std::getline(cin, s);
    return s;
}
static int readInt(const string& prompt, int lo = INT_MIN, int hi = INT_MAX) {
    while (true) {
        string s = readLine(prompt);
        try {
            int v = std::stoi(s);
            if (v < lo || v > hi) {
                cout << "  > please enter a number between " << lo << " and " << hi << "\n";
                continue;
            }
            return v;
        } catch (...) {
            cout << "  > not a valid number, try again\n";
        }
    }
}

static void pause_() { readLine("\n  [press Enter to continue]"); }

static void printTable(const vector<vector<string>>& rows, const vector<string>& header) {
    if (rows.empty()) {
        cout << "  (no records)\n"; return;
    }
    vector<size_t> w(header.size(), 0);
    for (size_t i = 0; i < header.size(); ++i) w[i] = header[i].size();
    for (auto& r : rows)
        for (size_t i = 0; i < r.size() && i < w.size(); ++i)
            if (r[i].size() > w[i]) w[i] = r[i].size();
    auto bar = [&]() {
        cout << "  +";
        for (size_t i = 0; i < w.size(); ++i) cout << string(w[i] + 2, '-') << "+";
        cout << "\n";
    };
    bar();
    cout << "  |";
    for (size_t i = 0; i < header.size(); ++i)
        cout << " " << std::left << std::setw((int)w[i]) << header[i] << " |";
    cout << "\n";
    bar();
    for (auto& r : rows) {
        cout << "  |";
        for (size_t i = 0; i < w.size(); ++i) {
            string v = (i < r.size()) ? r[i] : "";
            cout << " " << std::left << std::setw((int)w[i]) << v << " |";
        }
        cout << "\n";
    }
    bar();
}

static vector<vector<string>> rowsToVec(const Response& r, const vector<string>& fields) {
    vector<vector<string>> out;
    for (auto& row : r.rows) {
        vector<string> v;
        for (auto& f : fields) {
            auto it = row.find(f);
            v.push_back(it == row.end() ? "" : it->second);
        }
        out.push_back(v);
    }
    return out;
}

// -------------------- screens --------------------
static string g_role;

static bool isAdmin() { return g_role == "admin"; }

static void studentsMenu(Net& net) {
    while (true) {
        cout << "\n===== Students Menu =====\n";
        cout << "  1) View all\n  2) Search\n";
        if (isAdmin()) cout << "  3) Add\n  4) Update\n  5) Delete\n";
        cout << "  0) Back\n";
        int c = readInt("  choice: ", 0, 5);
        if (c == 0) return;
        if (c == 1) {
            Request q; q.action = "list_students";
            auto r = net.send(q);
            if (!r.ok) { cout << "  ! " << r.error << "\n"; pause_(); continue; }
            auto data = rowsToVec(r, {"student_id","name","email","phone","major","level"});
            printTable(data, {"Student ID","Name","Email","Phone","Major","Lvl"});
            pause_();
        } else if (c == 2) {
            string kw = readLine("  keyword (id / name / major): ");
            Request q; q.action = "search_students"; q.params["keyword"] = kw;
            auto r = net.send(q);
            if (!r.ok) { cout << "  ! " << r.error << "\n"; pause_(); continue; }
            auto data = rowsToVec(r, {"student_id","name","email","phone","major","level"});
            printTable(data, {"Student ID","Name","Email","Phone","Major","Lvl"});
            pause_();
        } else if (c == 3 && isAdmin()) {
            Request q; q.action = "add_student";
            q.params["student_id"] = readLine("  Student ID (10 digits): ");
            q.params["name"]       = readLine("  Name: ");
            q.params["email"]      = readLine("  Email: ");
            q.params["phone"]      = readLine("  Phone: ");
            q.params["major"]      = readLine("  Major: ");
            q.params["level"]      = readLine("  Level (1-10): ");
            auto r = net.send(q);
            cout << (r.ok ? "  ok: student added\n" : "  ! " + r.error + "\n");
            pause_();
        } else if (c == 4 && isAdmin()) {
            Request q; q.action = "update_student";
            q.params["student_id"] = readLine("  Student ID to update: ");
            q.params["name"]       = readLine("  New Name: ");
            q.params["email"]      = readLine("  New Email: ");
            q.params["phone"]      = readLine("  New Phone: ");
            q.params["major"]      = readLine("  New Major: ");
            q.params["level"]      = readLine("  New Level: ");
            auto r = net.send(q);
            cout << (r.ok ? "  ok: student updated\n" : "  ! " + r.error + "\n");
            pause_();
        } else if (c == 5 && isAdmin()) {
            Request q; q.action = "delete_student";
            q.params["student_id"] = readLine("  Student ID to delete: ");
            auto r = net.send(q);
            cout << (r.ok ? "  ok: student deleted\n" : "  ! " + r.error + "\n");
            pause_();
        }
    }
}

static void coursesMenu(Net& net) {
    while (true) {
        cout << "\n===== Courses Menu =====\n";
        cout << "  1) View all\n  2) Search\n";
        if (isAdmin()) cout << "  3) Add\n  4) Update\n  5) Delete\n";
        cout << "  0) Back\n";
        int c = readInt("  choice: ", 0, 5);
        if (c == 0) return;
        if (c == 1) {
            Request q; q.action = "list_courses";
            auto r = net.send(q);
            auto data = rowsToVec(r, {"code","title","credits","instructor"});
            printTable(data, {"Code","Title","Cr","Instructor"});
            pause_();
        } else if (c == 2) {
            string kw = readLine("  keyword (code / title / instructor): ");
            Request q; q.action = "search_courses"; q.params["keyword"] = kw;
            auto r = net.send(q);
            auto data = rowsToVec(r, {"code","title","credits","instructor"});
            printTable(data, {"Code","Title","Cr","Instructor"});
            pause_();
        } else if (c == 3 && isAdmin()) {
            Request q; q.action = "add_course";
            q.params["code"]       = readLine("  Code: ");
            q.params["title"]      = readLine("  Title: ");
            q.params["credits"]    = readLine("  Credits (1-6): ");
            q.params["instructor"] = readLine("  Instructor: ");
            auto r = net.send(q);
            cout << (r.ok ? "  ok: course added\n" : "  ! " + r.error + "\n");
            pause_();
        } else if (c == 4 && isAdmin()) {
            Request q; q.action = "update_course";
            q.params["code"]       = readLine("  Code to update: ");
            q.params["title"]      = readLine("  New Title: ");
            q.params["credits"]    = readLine("  New Credits: ");
            q.params["instructor"] = readLine("  New Instructor: ");
            auto r = net.send(q);
            cout << (r.ok ? "  ok: course updated\n" : "  ! " + r.error + "\n");
            pause_();
        } else if (c == 5 && isAdmin()) {
            Request q; q.action = "delete_course";
            q.params["code"] = readLine("  Code to delete: ");
            auto r = net.send(q);
            cout << (r.ok ? "  ok: course deleted\n" : "  ! " + r.error + "\n");
            pause_();
        }
    }
}

static void enrollmentMenu(Net& net) {
    while (true) {
        cout << "\n===== Enrollment Menu =====\n";
        cout << "  1) View all enrollments\n  2) Enroll a student\n  3) Unenroll a student\n  0) Back\n";
        int c = readInt("  choice: ", 0, 3);
        if (c == 0) return;
        if (c == 1) {
            Request q; q.action = "list_enrollments";
            auto r = net.send(q);
            auto data = rowsToVec(r, {"student_id","name","course_code","title","semester"});
            printTable(data, {"Student ID","Student","Course","Title","Semester"});
            pause_();
        } else if (c == 2) {
            Request q; q.action = "enroll";
            q.params["student_id"]  = readLine("  Student ID: ");
            q.params["course_code"] = readLine("  Course code: ");
            q.params["semester"]    = readLine("  Semester (e.g. 2025-2): ");
            auto r = net.send(q);
            cout << (r.ok ? "  ok: enrolled\n" : "  ! " + r.error + "\n");
            pause_();
        } else if (c == 3) {
            Request q; q.action = "unenroll";
            q.params["student_id"]  = readLine("  Student ID: ");
            q.params["course_code"] = readLine("  Course code: ");
            q.params["semester"]    = readLine("  Semester: ");
            auto r = net.send(q);
            cout << (r.ok ? "  ok: unenrolled\n" : "  ! " + r.error + "\n");
            pause_();
        }
    }
}

static void attendanceMenu(Net& net) {
    while (true) {
        cout << "\n===== Attendance Menu =====\n";
        cout << "  1) Mark attendance\n  2) View report (by course)\n  3) Summary (by course)\n  0) Back\n";
        int c = readInt("  choice: ", 0, 3);
        if (c == 0) return;
        if (c == 1) {
            Request q; q.action = "mark_attendance";
            q.params["student_id"]  = readLine("  Student ID: ");
            q.params["course_code"] = readLine("  Course code: ");
            q.params["date"]        = readLine("  Date (YYYY-MM-DD): ");
            q.params["status"]      = readLine("  Status (Present/Absent): ");
            auto r = net.send(q);
            cout << (r.ok ? "  ok: attendance recorded\n" : "  ! " + r.error + "\n");
            pause_();
        } else if (c == 2) {
            Request q; q.action = "attendance_report";
            q.params["course_code"] = readLine("  Course code (blank = all): ");
            auto r = net.send(q);
            auto data = rowsToVec(r, {"student_id","name","course_code","adate","status"});
            printTable(data, {"Student ID","Student","Course","Date","Status"});
            pause_();
        } else if (c == 3) {
            Request q; q.action = "attendance_summary";
            q.params["course_code"] = readLine("  Course code (blank = all): ");
            auto r = net.send(q);
            auto data = rowsToVec(r, {"student_id","name","present_count","absent_count"});
            printTable(data, {"Student ID","Student","Present","Absent"});
            pause_();
        }
    }
}

static bool loginScreen(Net& net) {
    cout << "\n========================================\n";
    cout << " Smart Student Management & Attendance\n";
    cout << "         (CS516 - C++ Client)\n";
    cout << "========================================\n\n";
    for (int attempt = 1; attempt <= 3; ++attempt) {
        string u = readLine("  Username (default: admin): ");
        string p = readLine("  Password (default: admin123): ");
        if (u.empty()) u = "admin";
        if (p.empty()) p = "admin123";
        Request q; q.action = "login";
        q.params["username"] = u; q.params["password"] = p;
        auto r = net.send(q);
        if (r.ok && !r.rows.empty()) {
            g_role = r.rows[0]["role"];
            cout << "\n  Welcome, " << u << " (role: " << g_role << ")\n";
            return true;
        }
        cout << "  ! Login failed: " << r.error << "  (attempts left: " << (3 - attempt) << ")\n";
    }
    return false;
}

int main() {
    Net net;
    if (!net.connectServer()) {
        cout << "Cannot connect to server. Start server.exe first.\n";
        return 1;
    }
    if (!loginScreen(net)) return 0;

    while (true) {
        cout << "\n========== Main Menu ==========\n";
        cout << "  1) Students\n  2) Courses\n  3) Enrollment\n  4) Attendance\n  0) Exit\n";
        int c = readInt("  choice: ", 0, 4);
        if (c == 0) { cout << "\n  Goodbye.\n"; break; }
        if (c == 1) studentsMenu(net);
        else if (c == 2) coursesMenu(net);
        else if (c == 3) enrollmentMenu(net);
        else if (c == 4) attendanceMenu(net);
    }
    return 0;
}
