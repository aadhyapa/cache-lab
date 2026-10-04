#include "report.hpp"

#include <algorithm>
#include <iomanip>
#include <ostream>

namespace cachelab {

Summary summarize(const Cache& cache, const std::vector<std::uint64_t>& costs,
                  std::uint32_t window) {
    const Stats& stats = cache.stats();
    Summary s;
    s.accesses = stats.accesses;
    s.hits = stats.hits;
    s.misses = stats.misses;
    s.hit_rate = stats.hit_rate();
    s.writebacks = stats.writebacks;
    s.total_cycles = cache.total_cycles();
    s.window = window;

    if (costs.empty()) return s;

    std::uint64_t sum = 0;
    s.cost_min = costs.front();
    s.cost_max = costs.front();
    for (std::uint64_t c : costs) {
        sum += c;
        s.cost_min = std::min(s.cost_min, c);
        s.cost_max = std::max(s.cost_max, c);
    }
    s.cost_mean = static_cast<double>(sum) / static_cast<double>(costs.size());

    // Sliding-window maximum
    const std::size_t w = std::min<std::size_t>(window, costs.size());
    std::uint64_t current = 0;
    for (std::size_t i = 0; i < w; ++i) current += costs[i];
    s.worst_window_cycles = current;
    for (std::size_t i = w; i < costs.size(); ++i) {
        current += costs[i];
        current -= costs[i - w];
        s.worst_window_cycles = std::max(s.worst_window_cycles, current);
    }
    return s;
}

void print_text(std::ostream& out, const Summary& s) {
    out << std::fixed << std::setprecision(4);
    out << "accesses: " << s.accesses << '\n'
        << "hits: " << s.hits << '\n'
        << "misses: " << s.misses << '\n'
        << "hit_rate: " << s.hit_rate << '\n'
        << "writebacks: " << s.writebacks << '\n'
        << "total_cycles: " << s.total_cycles << '\n'
        << "cost_min: " << s.cost_min << '\n'
        << "cost_mean: " << s.cost_mean << '\n'
        << "cost_max: " << s.cost_max << '\n'
        << "window: " << s.window << '\n'
        << "worst_window_cycles: " << s.worst_window_cycles << '\n';
}

void print_json(std::ostream& out, const Summary& s) {
    out << std::fixed << std::setprecision(4);
    out << "{\n"
        << "  \"accesses\": " << s.accesses << ",\n"
        << "  \"hits\": " << s.hits << ",\n"
        << "  \"misses\": " << s.misses << ",\n"
        << "  \"hit_rate\": " << s.hit_rate << ",\n"
        << "  \"writebacks\": " << s.writebacks << ",\n"
        << "  \"total_cycles\": " << s.total_cycles << ",\n"
        << "  \"cost_min\": " << s.cost_min << ",\n"
        << "  \"cost_mean\": " << s.cost_mean << ",\n"
        << "  \"cost_max\": " << s.cost_max << ",\n"
        << "  \"window\": " << s.window << ",\n"
        << "  \"worst_window_cycles\": " << s.worst_window_cycles << "\n"
        << "}\n";
}

}  // namespace cachelab
