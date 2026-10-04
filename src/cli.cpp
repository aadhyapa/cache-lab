#include "cli.hpp"

#include <charconv>
#include <cstring>

namespace cachelab {

namespace {

bool parse_u32(const char* text, std::uint32_t& out) {
    const char* end = text + std::strlen(text);
    auto result = std::from_chars(text, end, out);
    return text != end && result.ec == std::errc() && result.ptr == end;
}

bool parse_hex(const char* text, std::uint32_t& out) {
    const char* begin = text;
    const char* end = text + std::strlen(text);
    if (end - begin > 2 && begin[0] == '0' && (begin[1] == 'x' || begin[1] == 'X')) begin += 2;
    if (begin == end) return false;
    auto result = std::from_chars(begin, end, out, 16);
    return result.ec == std::errc() && result.ptr == end;
}

}  // namespace

bool parse_args(int argc, char* argv[], Options& options, std::string& error) {
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];

        if (arg == "--json") {
            options.json = true;
            continue;
        }
        if (arg.rfind("--", 0) != 0) {
            if (!options.trace_path.empty()) {
                error = "unexpected extra argument: " + arg;
                return false;
            }
            options.trace_path = arg;
            continue;
        }

        if (arg == "--decode") {
            if (i + 1 >= argc) {
                error = "missing value for --decode";
                return false;
            }
            const char* value = argv[++i];
            if (!parse_hex(value, options.decode_addr)) {
                error = std::string("invalid value for --decode: ") + value;
                return false;
            }
            options.decode = true;
            continue;
        }

        std::uint32_t* target = nullptr;
        if (arg == "--sets") target = &options.config.sets;
        else if (arg == "--ways") target = &options.config.ways;
        else if (arg == "--line-size") target = &options.config.line_size;
        else if (arg == "--hit-cycles") target = &options.config.hit_cycles;
        else if (arg == "--miss-cycles") target = &options.config.miss_cycles;
        else if (arg == "--writeback-cycles") target = &options.config.writeback_cycles;
        else if (arg == "--window") target = &options.window;
        else {
            error = "unknown option: " + arg;
            return false;
        }

        if (i + 1 >= argc) {
            error = "missing value for " + arg;
            return false;
        }
        const char* value = argv[++i];
        if (!parse_u32(value, *target)) {
            error = "invalid value for " + arg + ": " + value;
            return false;
        }
    }

    if (options.window == 0) {
        error = "window must be at least 1";
        return false;
    }
    if (options.trace_path.empty() && !options.decode) {
        error = "no trace file given";
        return false;
    }
    return true;
}

}  // namespace cachelab
