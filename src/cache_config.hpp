#pragma once

#include <bit>
#include <cstdint>
#include <string>

namespace cachelab {

// Defaults: 64 sets x 4 ways x 32-byte lines = 8 KB.
struct CacheConfig {
    std::uint32_t sets = 64;
    std::uint32_t ways = 4;
    std::uint32_t line_size = 32;
    std::uint32_t hit_cycles = 1;
    std::uint32_t miss_cycles = 100;
    std::uint32_t writeback_cycles = 0;

    static bool is_power_of_two(std::uint32_t value) { return std::has_single_bit(value); }

    // CL-001: on failure, fills `error` with a message and returns false.
    bool validate(std::string& error) const;
};

}  // namespace cachelab
