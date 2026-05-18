// common.h - shared types and helpers for the C++ client/server
// CS516 - Advanced Programming Language
#ifndef COMMON_H
#define COMMON_H

#include <string>
#include <vector>
#include <sstream>
#include <iostream>
#include <fstream>
#include <map>
#include <cctype>

// We avoid third-party libs. Protocol is line-based, fields are pipe-separated.
// Request:  ACTION|key1=val1|key2=val2|...\n
// Response: OK|count|row1_field1=...|...||row2_...   (rows split by '||')
//           ERR|message

namespace netproto {

inline std::string trim(const std::string& s) {
    size_t a = 0, b = s.size();
    while (a < b && std::isspace((unsigned char)s[a])) ++a;
    while (b > a && std::isspace((unsigned char)s[b - 1])) --b;
    return s.substr(a, b - a);
}

inline std::vector<std::string> split(const std::string& s, char d) {
    std::vector<std::string> out;
    std::string cur;
    for (char c : s) {
        if (c == d) { out.push_back(cur); cur.clear(); }
        else cur.push_back(c);
    }
    out.push_back(cur);
    return out;
}

// escape '|' and '=' and '\n' inside values
inline std::string esc(const std::string& v) {
    std::string out;
    for (char c : v) {
        if (c == '|') out += "\\p";
        else if (c == '=') out += "\\e";
        else if (c == '\n') out += "\\n";
        else if (c == '\\') out += "\\\\";
        else out.push_back(c);
    }
    return out;
}

inline std::string unesc(const std::string& v) {
    std::string out;
    for (size_t i = 0; i < v.size(); ++i) {
        if (v[i] == '\\' && i + 1 < v.size()) {
            char n = v[i + 1];
            if (n == 'p') out.push_back('|');
            else if (n == 'e') out.push_back('=');
            else if (n == 'n') out.push_back('\n');
            else if (n == '\\') out.push_back('\\');
            else out.push_back(n);
            ++i;
        } else out.push_back(v[i]);
    }
    return out;
}

struct Request {
    std::string action;
    std::map<std::string, std::string> params;
    std::string get(const std::string& k, const std::string& def = "") const {
        auto it = params.find(k);
        return it == params.end() ? def : it->second;
    }
    std::string encode() const {
        std::ostringstream os;
        os << action;
        for (auto& kv : params) os << "|" << kv.first << "=" << esc(kv.second);
        os << "\n";
        return os.str();
    }
    static Request decode(const std::string& line) {
        Request r;
        auto parts = split(line, '|');
        if (parts.empty()) return r;
        r.action = trim(parts[0]);
        for (size_t i = 1; i < parts.size(); ++i) {
            auto kv = parts[i];
            auto eq = kv.find('=');
            if (eq == std::string::npos) continue;
            r.params[trim(kv.substr(0, eq))] = unesc(kv.substr(eq + 1));
        }
        return r;
    }
};

struct Response {
    bool ok = true;
    std::string error;
    // each row is a map of fields
    std::vector<std::map<std::string, std::string>> rows;

    std::string encode() const {
        std::ostringstream os;
        if (!ok) { os << "ERR|" << esc(error) << "\n"; return os.str(); }
        os << "OK|" << rows.size();
        bool firstRow = true;
        for (auto& row : rows) {
            os << "||";
            (void)firstRow;
            bool first = true;
            for (auto& kv : row) {
                if (!first) os << "|";
                os << kv.first << "=" << esc(kv.second);
                first = false;
            }
        }
        os << "\n";
        return os.str();
    }
    static Response decode(const std::string& line) {
        Response r;
        auto firstPipe = line.find('|');
        std::string head = firstPipe == std::string::npos ? line : line.substr(0, firstPipe);
        std::string rest = firstPipe == std::string::npos ? "" : line.substr(firstPipe + 1);
        if (trim(head) == "ERR") { r.ok = false; r.error = unesc(rest); return r; }
        r.ok = true;
        // rest = "<count>||row1||row2..."  (rows separated by ||)
        // pull off count
        auto firstDouble = rest.find("||");
        if (firstDouble == std::string::npos) return r; // just count, no rows
        std::string rowsStr = rest.substr(firstDouble + 2);
        // split by '||'
        std::vector<std::string> rowParts;
        std::string cur;
        for (size_t i = 0; i < rowsStr.size(); ++i) {
            if (i + 1 < rowsStr.size() && rowsStr[i] == '|' && rowsStr[i + 1] == '|') {
                rowParts.push_back(cur); cur.clear(); ++i;
            } else cur.push_back(rowsStr[i]);
        }
        rowParts.push_back(cur);
        for (auto& rp : rowParts) {
            if (rp.empty()) continue;
            std::map<std::string, std::string> row;
            for (auto& kv : split(rp, '|')) {
                auto eq = kv.find('=');
                if (eq == std::string::npos) continue;
                row[trim(kv.substr(0, eq))] = unesc(kv.substr(eq + 1));
            }
            r.rows.push_back(row);
        }
        return r;
    }
};

}  // namespace netproto

#endif
