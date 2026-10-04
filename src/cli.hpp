#pragma once

#include <cstdint>
#include <string>

#include "cache_config.hpp"

namespace cachelab {

struct Options {
    CacheConfig config;
    std::string trace_path;
    std::uint32_t window = 100;  // CL-011: --window N
    bool json = false;           // CL-010: --json
};

// Parses the command line into `options`, which starts from its defaults.
// Only checks the command line itself (unknown flag, missing or non-numeric
// value, no trace file); config values are checked by CacheConfig::validate.
// On failure fills `error` and returns false.
bool parse_args(int argc, char* argv[], Options& options, std::string& error);

}  // namespace cachelab
