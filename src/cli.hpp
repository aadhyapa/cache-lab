#pragma once

#include <cstdint>
#include <string>

#include "cache_config.hpp"

namespace cachelab {

struct Options {
    CacheConfig config;
    std::string trace_path;
    std::uint32_t window = 100;
    bool json = false;
    bool decode = false;
    std::uint32_t decode_addr = 0;
};

bool parse_args(int argc, char* argv[], Options& options, std::string& error);

}  // namespace cachelab
