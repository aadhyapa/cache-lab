#pragma once

#include <cstdint>
#include <iosfwd>
#include <vector>

#include "cache.hpp"

namespace cachelab {

// Everything the report prints.
struct Summary {
    std::uint64_t accesses = 0;
    std::uint64_t hits = 0;
    std::uint64_t misses = 0;
    double hit_rate = 0.0;
    std::uint64_t writebacks = 0;
    std::uint64_t total_cycles = 0;
    std::uint64_t cost_min = 0;
    double cost_mean = 0.0;
    std::uint64_t cost_max = 0;
    std::uint32_t window = 0;
    // Worst total cost over any `window` consecutive accesses. If the trace is
    // shorter than the window, this is the cost of the whole trace.
    std::uint64_t worst_window_cycles = 0;
};

Summary summarize(const Cache& cache, const std::vector<std::uint64_t>& costs,
                  std::uint32_t window);

void print_text(std::ostream& out, const Summary& summary);
void print_json(std::ostream& out, const Summary& summary);

}  // namespace cachelab
