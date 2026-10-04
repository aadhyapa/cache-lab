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

bool parse_args(int argc, char* argv[], Options& options, std::string& error);

}  // namespace cachelab
