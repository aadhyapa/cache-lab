#include "trace.hpp"

#include <charconv>
#include <sstream>

namespace cachelab {

namespace {

std::string trim(const std::string& text) {
    const char* whitespace = " \t\r\n";
    const auto first = text.find_first_not_of(whitespace);
    if (first == std::string::npos) return "";
    const auto last = text.find_last_not_of(whitespace);
    return text.substr(first, last - first + 1);
}

bool parse_hex_u32(const std::string& token, std::uint32_t& out) {
    const char* begin = token.data();
    const char* end = begin + token.size();
    if (token.size() > 2 && token[0] == '0' && (token[1] == 'x' || token[1] == 'X')) begin += 2;
    if (begin == end) return false;
    const auto result = std::from_chars(begin, end, out, 16);
    return result.ec == std::errc() && result.ptr == end;
}

bool parse_trace_line(const std::string& line, TraceEntry& entry) {
    std::istringstream fields(line);
    std::string type, address, extra;
    if (!(fields >> type >> address) || (fields >> extra)) return false;
    if (type == "R") entry.type = AccessType::Read;
    else if (type == "W") entry.type = AccessType::Write;
    else return false;
    return parse_hex_u32(address, entry.address);
}

}  // namespace

bool read_trace(std::istream& in, std::vector<TraceEntry>& entries, std::string& error) {
    std::string raw;
    std::size_t line_number = 0;
    while (std::getline(in, raw)) {
        ++line_number;
        const std::string line = trim(raw);
        if (line.empty() || line[0] == '#') continue;

        TraceEntry entry;
        if (!parse_trace_line(line, entry)) {
            error = "line " + std::to_string(line_number) + ": malformed trace line: " + line;
            return false;
        }
        entries.push_back(entry);
    }
    return true;
}

}  // namespace cachelab
