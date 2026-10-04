#pragma once

#include <cstddef>
#include <cstdint>
#include <iostream>
#include <ostream>
#include <string>
#include <vector>

#include "access.hpp"
#include "address.hpp"
#include "cache_config.hpp"

namespace cachelab {

struct AccessResult {
    bool hit = false;
    bool writeback = false; // a dirty line was evicted by this access
    std::uint64_t cycles = 0;
};

struct Stats {
    std::uint64_t accesses = 0;
    std::uint64_t hits = 0;
    std::uint64_t misses = 0;
    std::uint64_t writebacks = 0;

    double hit_rate() const;  // 0.0 when accesses == 0 (CL-012: empty trace)
};

class Cache {
public:
    explicit Cache(const CacheConfig& cfg);

    // decode address
    Address decode(std::uint32_t addr) const { return decode_address(cfg_, addr); }
    AccessResult access(AccessType type, std::uint32_t addr);

    // calculate total cycles
    std::uint64_t total_cycles() const;

    const Stats& stats() const { return stats_; }
    const CacheConfig& config() const { return cfg_; }

private:
    struct Line {
        bool valid = false;
        bool dirty = false;
        std::uint32_t tag = 0;
        std::uint64_t last_used = 0;
    };

    // storage
    Line* set_begin(std::uint32_t set) { return &lines_[std::size_t(set) * cfg_.ways]; }

    CacheConfig cfg_;
    std::vector<Line> lines_;
    // Logical clock for LRU. Counts accesses, not time, so runs are
    // byte-identical. uint64_t cannot realistically overflow.
    std::uint64_t tick_ = 0;
    Stats stats_;
};

}
