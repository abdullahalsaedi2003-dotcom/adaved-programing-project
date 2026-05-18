// server.cpp - Smart Student Management & Attendance System (Server, C++)
// CS516 - Advanced Programming Language
//
// Build (Windows, MinGW-w64):
//   g++ -std=c++17 -O2 -static -o server.exe server.cpp -lws2_32
//
// Run: server.exe (listens on 127.0.0.1:5066)
//
// Uses OOP design: a Repository class per entity wraps the data store
// (CSV-style files in ./data/), and Server dispatches actions.

#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>

#include "common.h"

#include <algorithm>
#include <cstring>
#include <ctime>
#include <filesystem>
#include <mutex>
#include <thread>

#pragma comment(lib, "ws2_32.lib")

namespace fs = std::filesystem;
using netproto::Request;
using netproto::Response;
using std::string;
using std::vector;
using std::map;

constexpr const char* HOST = "127.0.0.1";
constexpr int PORT = 5066;
const string DATA_DIR = "data";

// -------------------- helpers --------------------
static std::mutex g_mtx;

static bool isDigits(const string& s) {
    if (s.empty()) return false;
    for (char c : s) if (!std::isdigit((unsigned char)c)) return false;
    return true;
}
static bool validEmail(const string& s) {
    auto at = s.find('@');
    if (at == string::npos) return false;
    auto dot = s.find('.', at);
    return dot != string::npos && s.size() >= 5;
}
static bool validPhone(const string& s) { return isDigits(s) && s.size() >= 8 && s.size() <= 15; }
static bool validId(const string& s) { return isDigits(s) && s.size() == 10; }
static bool validDate(const string& s) {
    if (s.size() != 10 || s[4] != '-' || s[7] != '-') return false;
    return isDigits(s.substr(0, 4)) && isDigits(s.substr(5, 2)) && isDigits(s.substr(8, 2));
}
static string toUpper(string s) { for (auto& c : s) c = std::toupper((unsigned char)c); return s; }
static string trimCopy(const string& s) { return netproto::trim(s); }

// CSV-style storage: each line = field1\tfield2\t...
// We use TAB as separator (safer than | which collides with protocol).
class FileStore {
public:
    explicit FileStore(string path) : path_(std::move(path)) { fs::create_directories(fs::path(path_).parent_path()); }

    vector<vector<string>> readAll() const {
        vector<vector<string>> rows;
        std::ifstream f(path_);
        string line;
        while (std::getline(f, line)) {
            if (line.empty()) continue;
            rows.push_back(netproto::split(line, '\t'));
        }
        return rows;
    }
    void writeAll(const vector<vector<string>>& rows) const {
        std::ofstream f(path_, std::ios::trunc);
        for (auto& r : rows) {
            for (size_t i = 0; i < r.size(); ++i) {
                if (i) f << '\t';
                f << r[i];
            }
            f << '\n';
        }
    }
    void append(const vector<string>& row) const {
        std::ofstream f(path_, std::ios::app);
        for (size_t i = 0; i < row.size(); ++i) {
            if (i) f << '\t';
            f << row[i];
        }
        f << '\n';
    }
private:
    string path_;
};

// -------------------- entity stores --------------------
// users: username \t password \t role
// students: student_id \t name \t email \t phone \t major \t level
// courses: code \t title \t credits \t instructor
// enrollments: student_id \t course_code \t semester
// attendance: student_id \t course_code \t date \t status

class UsersRepo {
public:
    UsersRepo() : store_(DATA_DIR + "/users.txt") {}
    void seedIfEmpty() {
        auto rows = store_.readAll();
        if (!rows.empty()) return;
        store_.append({"admin", "admin123", "admin"});
        store_.append({"ahmed", "ahmed123", "instructor"});
        store_.append({"abdullah", "abdullah123", "instructor"});
    }
    string findRole(const string& u, const string& p) {
        for (auto& r : store_.readAll())
            if (r.size() >= 3 && r[0] == u && r[1] == p) return r[2];
        return "";
    }
private:
    FileStore store_;
};

class StudentsRepo {
public:
    StudentsRepo() : store_(DATA_DIR + "/students.txt") {}
    void seedIfEmpty() {
        auto rows = store_.readAll();
        if (!rows.empty()) return;
        store_.append({"2220007240", "Ahmed Al-Awlaqi", "ahmed@iau.edu.sa", "0551234567", "CS", "4"});
        store_.append({"2220003178", "Abdulaziz Alghamdi", "aziz@iau.edu.sa", "0559876543", "CS", "4"});
        store_.append({"2220002306", "Abdullah Alsaedi", "abdullah@iau.edu.sa", "0556677889", "CS", "4"});
    }
    vector<vector<string>> all() { return store_.readAll(); }
    bool exists(const string& sid) {
        for (auto& r : store_.readAll()) if (!r.empty() && r[0] == sid) return true;
        return false;
    }
    string add(const vector<string>& r) {
        if (exists(r[0])) return "Student ID already exists";
        store_.append(r); return "";
    }
    string update(const vector<string>& r) {
        auto rows = store_.readAll();
        bool found = false;
        for (auto& row : rows) {
            if (!row.empty() && row[0] == r[0]) { row = r; found = true; break; }
        }
        if (!found) return "Student not found";
        store_.writeAll(rows); return "";
    }
    string remove(const string& sid) {
        auto rows = store_.readAll();
        size_t before = rows.size();
        rows.erase(std::remove_if(rows.begin(), rows.end(),
            [&](const vector<string>& r) { return !r.empty() && r[0] == sid; }), rows.end());
        if (rows.size() == before) return "Student not found";
        store_.writeAll(rows); return "";
    }
private:
    FileStore store_;
};

class CoursesRepo {
public:
    CoursesRepo() : store_(DATA_DIR + "/courses.txt") {}
    void seedIfEmpty() {
        auto rows = store_.readAll();
        if (!rows.empty()) return;
        store_.append({"CS516", "Advanced Programming Language", "3", "Mrs. Sarah Alissa"});
        store_.append({"CS411", "Software Engineering", "3", "Dr. Fatimah"});
        store_.append({"CS324", "Operating Systems", "4", "Dr. Khalid"});
    }
    vector<vector<string>> all() { return store_.readAll(); }
    bool exists(const string& code) {
        for (auto& r : store_.readAll()) if (!r.empty() && r[0] == code) return true;
        return false;
    }
    string add(const vector<string>& r) {
        if (exists(r[0])) return "Course code already exists";
        store_.append(r); return "";
    }
    string update(const vector<string>& r) {
        auto rows = store_.readAll();
        bool found = false;
        for (auto& row : rows) if (!row.empty() && row[0] == r[0]) { row = r; found = true; break; }
        if (!found) return "Course not found";
        store_.writeAll(rows); return "";
    }
    string remove(const string& code) {
        auto rows = store_.readAll();
        size_t before = rows.size();
        rows.erase(std::remove_if(rows.begin(), rows.end(),
            [&](const vector<string>& r) { return !r.empty() && r[0] == code; }), rows.end());
        if (rows.size() == before) return "Course not found";
        store_.writeAll(rows); return "";
    }
private:
    FileStore store_;
};

class EnrollmentsRepo {
public:
    EnrollmentsRepo() : store_(DATA_DIR + "/enrollments.txt") {}
    vector<vector<string>> all() { return store_.readAll(); }
    bool isEnrolled(const string& sid, const string& code) {
        for (auto& r : store_.readAll())
            if (r.size() >= 2 && r[0] == sid && r[1] == code) return true;
        return false;
    }
    string add(const string& sid, const string& code, const string& sem) {
        for (auto& r : store_.readAll())
            if (r.size() >= 3 && r[0] == sid && r[1] == code && r[2] == sem)
                return "Student is already enrolled in this course this semester";
        store_.append({sid, code, sem}); return "";
    }
    string remove(const string& sid, const string& code, const string& sem) {
        auto rows = store_.readAll();
        size_t before = rows.size();
        rows.erase(std::remove_if(rows.begin(), rows.end(),
            [&](const vector<string>& r) {
                return r.size() >= 3 && r[0] == sid && r[1] == code && r[2] == sem;
            }), rows.end());
        if (rows.size() == before) return "Enrollment not found";
        store_.writeAll(rows); return "";
    }
    void removeAllForStudent(const string& sid) {
        auto rows = store_.readAll();
        rows.erase(std::remove_if(rows.begin(), rows.end(),
            [&](const vector<string>& r) { return !r.empty() && r[0] == sid; }), rows.end());
        store_.writeAll(rows);
    }
    void removeAllForCourse(const string& code) {
        auto rows = store_.readAll();
        rows.erase(std::remove_if(rows.begin(), rows.end(),
            [&](const vector<string>& r) { return r.size() >= 2 && r[1] == code; }), rows.end());
        store_.writeAll(rows);
    }
private:
    FileStore store_;
};

class AttendanceRepo {
public:
    AttendanceRepo() : store_(DATA_DIR + "/attendance.txt") {}
    vector<vector<string>> all() { return store_.readAll(); }
    void add(const string& sid, const string& code, const string& d, const string& status) {
        store_.append({sid, code, d, status});
    }
    void removeAllForStudent(const string& sid) {
        auto rows = store_.readAll();
        rows.erase(std::remove_if(rows.begin(), rows.end(),
            [&](const vector<string>& r) { return !r.empty() && r[0] == sid; }), rows.end());
        store_.writeAll(rows);
    }
    void removeAllForCourse(const string& code) {
        auto rows = store_.readAll();
        rows.erase(std::remove_if(rows.begin(), rows.end(),
            [&](const vector<string>& r) { return r.size() >= 2 && r[1] == code; }), rows.end());
        store_.writeAll(rows);
    }
private:
    FileStore store_;
};

// -------------------- service layer --------------------
class Service {
public:
    Service() { users_.seedIfEmpty(); students_.seedIfEmpty(); courses_.seedIfEmpty(); }

    Response handle(const Request& req) {
        std::lock_guard<std::mutex> lk(g_mtx);
        if (req.action == "login")            return login(req);
        if (req.action == "list_students")    return listStudents();
        if (req.action == "add_student")      return addStudent(req);
        if (req.action == "update_student")   return updateStudent(req);
        if (req.action == "delete_student")   return deleteStudent(req);
        if (req.action == "search_students")  return searchStudents(req);
        if (req.action == "list_courses")     return listCourses();
        if (req.action == "add_course")       return addCourse(req);
        if (req.action == "update_course")    return updateCourse(req);
        if (req.action == "delete_course")    return deleteCourse(req);
        if (req.action == "search_courses")   return searchCourses(req);
        if (req.action == "enroll")           return enroll(req);
        if (req.action == "list_enrollments") return listEnrollments();
        if (req.action == "unenroll")         return unenroll(req);
        if (req.action == "mark_attendance")  return markAttendance(req);
        if (req.action == "attendance_report")return attendanceReport(req);
        if (req.action == "attendance_summary") return attendanceSummary(req);
        return err("Unknown action: " + req.action);
    }
private:
    static Response err(const string& m) { Response r; r.ok = false; r.error = m; return r; }
    static Response ok() { return Response{}; }

    Response login(const Request& q) {
        Response r;
        string role = users_.findRole(q.get("username"), q.get("password"));
        if (role.empty()) return err("Invalid credentials");
        r.rows.push_back({{"role", role}});
        return r;
    }

    Response listStudents() {
        Response r;
        for (auto& row : students_.all()) {
            if (row.size() < 6) continue;
            r.rows.push_back({
                {"student_id", row[0]}, {"name", row[1]}, {"email", row[2]},
                {"phone", row[3]}, {"major", row[4]}, {"level", row[5]}
            });
        }
        return r;
    }
    Response searchStudents(const Request& q) {
        Response r;
        string kw = q.get("keyword");
        for (auto& row : students_.all()) {
            if (row.size() < 6) continue;
            if (kw.empty() || row[0].find(kw) != string::npos ||
                row[1].find(kw) != string::npos || row[4].find(kw) != string::npos) {
                r.rows.push_back({
                    {"student_id", row[0]}, {"name", row[1]}, {"email", row[2]},
                    {"phone", row[3]}, {"major", row[4]}, {"level", row[5]}
                });
            }
        }
        return r;
    }
    Response addStudent(const Request& q) {
        string sid = q.get("student_id"), name = trimCopy(q.get("name")),
               email = q.get("email"), phone = q.get("phone"),
               major = trimCopy(q.get("major")), level = q.get("level");
        if (!validId(sid))      return err("Student ID must be 10 digits");
        if (name.empty())       return err("Name is required");
        if (!validEmail(email)) return err("Invalid email");
        if (!validPhone(phone)) return err("Phone must be 8 to 15 digits");
        if (major.empty())      return err("Major is required");
        if (!isDigits(level))   return err("Level must be a number from 1 to 10");
        int lv = std::stoi(level);
        if (lv < 1 || lv > 10)  return err("Level must be a number from 1 to 10");
        auto e = students_.add({sid, name, email, phone, major, level});
        if (!e.empty()) return err(e);
        return ok();
    }
    Response updateStudent(const Request& q) {
        string sid = q.get("student_id"), name = trimCopy(q.get("name")),
               email = q.get("email"), phone = q.get("phone"),
               major = trimCopy(q.get("major")), level = q.get("level");
        if (!validId(sid))      return err("Student ID must be 10 digits");
        if (!validEmail(email)) return err("Invalid email");
        if (!validPhone(phone)) return err("Phone must be 8 to 15 digits");
        if (!isDigits(level))   return err("Level must be a number");
        auto e = students_.update({sid, name, email, phone, major, level});
        if (!e.empty()) return err(e);
        return ok();
    }
    Response deleteStudent(const Request& q) {
        string sid = q.get("student_id");
        auto e = students_.remove(sid);
        if (!e.empty()) return err(e);
        enrollments_.removeAllForStudent(sid);
        attendance_.removeAllForStudent(sid);
        return ok();
    }

    Response listCourses() {
        Response r;
        for (auto& row : courses_.all()) {
            if (row.size() < 4) continue;
            r.rows.push_back({{"code", row[0]}, {"title", row[1]},
                              {"credits", row[2]}, {"instructor", row[3]}});
        }
        return r;
    }
    Response searchCourses(const Request& q) {
        Response r;
        string kw = q.get("keyword");
        for (auto& row : courses_.all()) {
            if (row.size() < 4) continue;
            if (kw.empty() || row[0].find(kw) != string::npos ||
                row[1].find(kw) != string::npos || row[3].find(kw) != string::npos) {
                r.rows.push_back({{"code", row[0]}, {"title", row[1]},
                                  {"credits", row[2]}, {"instructor", row[3]}});
            }
        }
        return r;
    }
    Response addCourse(const Request& q) {
        string code = toUpper(trimCopy(q.get("code"))),
               title = trimCopy(q.get("title")),
               credits = q.get("credits"),
               instr = trimCopy(q.get("instructor"));
        if (code.empty())        return err("Course code is required");
        if (title.empty())       return err("Title is required");
        if (!isDigits(credits))  return err("Credits must be a number from 1 to 6");
        int c = std::stoi(credits);
        if (c < 1 || c > 6)      return err("Credits must be a number from 1 to 6");
        if (instr.empty())       return err("Instructor is required");
        auto e = courses_.add({code, title, credits, instr});
        if (!e.empty()) return err(e);
        return ok();
    }
    Response updateCourse(const Request& q) {
        string code = toUpper(trimCopy(q.get("code"))),
               title = trimCopy(q.get("title")),
               credits = q.get("credits"),
               instr = trimCopy(q.get("instructor"));
        if (!isDigits(credits)) return err("Credits must be a number");
        auto e = courses_.update({code, title, credits, instr});
        if (!e.empty()) return err(e);
        return ok();
    }
    Response deleteCourse(const Request& q) {
        string code = toUpper(trimCopy(q.get("code")));
        auto e = courses_.remove(code);
        if (!e.empty()) return err(e);
        enrollments_.removeAllForCourse(code);
        attendance_.removeAllForCourse(code);
        return ok();
    }

    Response enroll(const Request& q) {
        string sid = q.get("student_id"),
               code = toUpper(trimCopy(q.get("course_code"))),
               sem = trimCopy(q.get("semester"));
        if (sid.empty() || code.empty() || sem.empty())
            return err("All fields are required");
        if (!students_.exists(sid)) return err("Student not found");
        if (!courses_.exists(code)) return err("Course not found");
        auto e = enrollments_.add(sid, code, sem);
        if (!e.empty()) return err(e);
        return ok();
    }
    Response listEnrollments() {
        Response r;
        // build small lookup maps
        map<string, string> sname, ctitle;
        for (auto& s : students_.all()) if (s.size() >= 2) sname[s[0]] = s[1];
        for (auto& c : courses_.all())  if (c.size() >= 2) ctitle[c[0]] = c[1];
        for (auto& row : enrollments_.all()) {
            if (row.size() < 3) continue;
            r.rows.push_back({
                {"student_id", row[0]}, {"name", sname[row[0]]},
                {"course_code", row[1]}, {"title", ctitle[row[1]]},
                {"semester", row[2]}
            });
        }
        return r;
    }
    Response unenroll(const Request& q) {
        auto e = enrollments_.remove(q.get("student_id"),
                                     toUpper(trimCopy(q.get("course_code"))),
                                     trimCopy(q.get("semester")));
        if (!e.empty()) return err(e);
        return ok();
    }

    Response markAttendance(const Request& q) {
        string sid = q.get("student_id"),
               code = toUpper(trimCopy(q.get("course_code"))),
               d = q.get("date"),
               status = q.get("status");
        if (!validDate(d))    return err("Date must be in YYYY-MM-DD format");
        if (status != "Present" && status != "Absent")
            return err("Status must be Present or Absent");
        if (!enrollments_.isEnrolled(sid, code))
            return err("Student is not enrolled in this course");
        attendance_.add(sid, code, d, status);
        return ok();
    }
    Response attendanceReport(const Request& q) {
        Response r;
        string code = toUpper(trimCopy(q.get("course_code")));
        map<string, string> sname;
        for (auto& s : students_.all()) if (s.size() >= 2) sname[s[0]] = s[1];
        for (auto& row : attendance_.all()) {
            if (row.size() < 4) continue;
            if (!code.empty() && row[1] != code) continue;
            r.rows.push_back({
                {"student_id", row[0]}, {"name", sname[row[0]]},
                {"course_code", row[1]}, {"adate", row[2]}, {"status", row[3]}
            });
        }
        return r;
    }
    Response attendanceSummary(const Request& q) {
        Response r;
        string code = toUpper(trimCopy(q.get("course_code")));
        map<string, std::pair<int, int>> counts;  // sid -> {present, absent}
        for (auto& row : attendance_.all()) {
            if (row.size() < 4) continue;
            if (!code.empty() && row[1] != code) continue;
            if (row[3] == "Present") counts[row[0]].first++;
            else                     counts[row[0]].second++;
        }
        map<string, string> sname;
        for (auto& s : students_.all()) if (s.size() >= 2) sname[s[0]] = s[1];
        for (auto& kv : counts) {
            r.rows.push_back({
                {"student_id", kv.first}, {"name", sname[kv.first]},
                {"present_count", std::to_string(kv.second.first)},
                {"absent_count", std::to_string(kv.second.second)}
            });
        }
        return r;
    }

    UsersRepo users_;
    StudentsRepo students_;
    CoursesRepo courses_;
    EnrollmentsRepo enrollments_;
    AttendanceRepo attendance_;
};

// -------------------- networking --------------------
static Service svc;

static void clientThread(SOCKET cs) {
    string buf;
    char tmp[4096];
    while (true) {
        int n = recv(cs, tmp, sizeof(tmp), 0);
        if (n <= 0) break;
        buf.append(tmp, n);
        size_t nl;
        while ((nl = buf.find('\n')) != string::npos) {
            string line = buf.substr(0, nl);
            buf.erase(0, nl + 1);
            Request req = Request::decode(line);
            Response resp = svc.handle(req);
            string out = resp.encode();
            send(cs, out.c_str(), (int)out.size(), 0);
        }
    }
    closesocket(cs);
}

int main() {
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        std::cerr << "WSAStartup failed\n"; return 1;
    }
    SOCKET ss = socket(AF_INET, SOCK_STREAM, 0);
    if (ss == INVALID_SOCKET) { std::cerr << "socket failed\n"; return 1; }

    int yes = 1;
    setsockopt(ss, SOL_SOCKET, SO_REUSEADDR, (const char*)&yes, sizeof(yes));

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(PORT);
    inet_pton(AF_INET, HOST, &addr.sin_addr);
    if (bind(ss, (sockaddr*)&addr, sizeof(addr)) == SOCKET_ERROR) {
        std::cerr << "bind failed: " << WSAGetLastError() << "\n"; return 1;
    }
    if (listen(ss, 8) == SOCKET_ERROR) { std::cerr << "listen failed\n"; return 1; }
    std::cout << "Smart SMS (C++) server listening on " << HOST << ":" << PORT << "\n";

    while (true) {
        sockaddr_in ca{}; int clen = sizeof(ca);
        SOCKET cs = accept(ss, (sockaddr*)&ca, &clen);
        if (cs == INVALID_SOCKET) continue;
        std::thread(clientThread, cs).detach();
    }
    closesocket(ss);
    WSACleanup();
    return 0;
}
