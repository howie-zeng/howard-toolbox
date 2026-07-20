#include "io/json_reader.h"
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <cctype>

namespace rrm::io {

namespace {

struct Parser {
    const std::string& src;
    size_t pos = 0;

    char peek() const { return pos < src.size() ? src[pos] : '\0'; }
    char next() { return pos < src.size() ? src[pos++] : '\0'; }
    void skip_ws() { while (pos < src.size() && std::isspace(static_cast<unsigned char>(src[pos]))) ++pos; }

    std::string parse_string() {
        if (next() != '"') throw std::runtime_error("expected '\"'");
        std::string out;
        while (pos < src.size()) {
            char c = next();
            if (c == '"') return out;
            if (c == '\\') {
                char esc = next();
                if (esc == '"') out += '"';
                else if (esc == '\\') out += '\\';
                else if (esc == 'n') out += '\n';
                else out += esc;
            } else {
                out += c;
            }
        }
        throw std::runtime_error("unterminated string");
    }

    rrm::LoanValue parse_value() {
        skip_ws();
        char c = peek();

        if (c == '"') {
            return rrm::LoanValue{parse_string()};
        }

        if (c == 'n') {
            pos += 4;
            return rrm::LoanValue{std::string("")};
        }

        if (c == 't') { pos += 4; return rrm::LoanValue{1}; }
        if (c == 'f') { pos += 5; return rrm::LoanValue{0}; }

        std::string num;
        bool is_float = false;
        while (pos < src.size()) {
            char ch = peek();
            if (ch == '.' || ch == 'e' || ch == 'E') is_float = true;
            if (std::isdigit(static_cast<unsigned char>(ch)) || ch == '.' ||
                ch == '-' || ch == '+' || ch == 'e' || ch == 'E') {
                num += next();
            } else break;
        }
        if (num.empty()) throw std::runtime_error("unexpected char at pos " + std::to_string(pos));

        if (is_float) return rrm::LoanValue{std::stod(num)};
        long long iv = std::stoll(num);
        if (iv >= INT_MIN && iv <= INT_MAX) return rrm::LoanValue{static_cast<int>(iv)};
        return rrm::LoanValue{static_cast<double>(iv)};
    }

    rrm::LoanDict parse_object() {
        skip_ws();
        if (next() != '{') throw std::runtime_error("expected '{'");
        rrm::LoanDict obj;
        skip_ws();
        if (peek() == '}') { ++pos; return obj; }

        while (true) {
            skip_ws();
            std::string key = parse_string();
            skip_ws();
            if (next() != ':') throw std::runtime_error("expected ':'");
            skip_ws();

            if (peek() == 'n' && pos + 3 < src.size() &&
                src.substr(pos, 4) == "null") {
                pos += 4;
            } else {
                obj[key] = parse_value();
            }

            skip_ws();
            char sep = next();
            if (sep == '}') break;
            if (sep != ',') throw std::runtime_error("expected ',' or '}'");
        }
        return obj;
    }

    std::vector<rrm::LoanDict> parse_root() {
        skip_ws();
        if (peek() == '[') {
            ++pos;
            std::vector<rrm::LoanDict> arr;
            skip_ws();
            if (peek() == ']') { ++pos; return arr; }
            while (true) {
                arr.push_back(parse_object());
                skip_ws();
                char sep = next();
                if (sep == ']') break;
                if (sep != ',') throw std::runtime_error("expected ',' or ']'");
            }
            return arr;
        }
        return {parse_object()};
    }
};

}  // namespace

std::vector<rrm::LoanDict> read_loan_json(const std::string& path) {
    // Use binary mode + explicit size to handle files > 2GB on Windows
    std::ifstream f(path, std::ios::binary | std::ios::ate);
    if (!f.is_open()) throw std::runtime_error("cannot open JSON: " + path);
    auto size = f.tellg();
    f.seekg(0, std::ios::beg);
    std::string content(static_cast<size_t>(size), '\0');
    f.read(&content[0], size);
    Parser p{content};
    return p.parse_root();
}

}  // namespace rrm::io
