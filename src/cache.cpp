#include "cache.hpp"

namespace cachelab {

double Stats::hit_rate() const {
    return accesses == 0 ? 0.0 : static_cast<double>(hits) / static_cast<double>(accesses);
}

Cache::Cache(const CacheConfig& cfg)
    : cfg_(cfg), lines_(static_cast<std::size_t>(cfg.sets) * cfg.ways) {}

AccessResult Cache::access(AccessType type, std::uint32_t addr) {
    const Address parts = decode(addr);
    Line* set = set_begin(parts.set);

    ++tick_;
    ++stats_.accesses;

    for (std::uint32_t way = 0; way < cfg_.ways; ++way) {
        if (set[way].valid && set[way].tag == parts.tag) {
            set[way].last_used = tick_;
            //  write hit only sets the dirty bit
            if (type == AccessType::Write) set[way].dirty = true;
            ++stats_.hits;
            return AccessResult{true, false, cfg_.hit_cycles};
        }
    }

    Line* victim = set;
    for (std::uint32_t way = 0; way < cfg_.ways; ++way) {
        if (!set[way].valid) {
            victim = &set[way];
            break;
        }
        if (set[way].last_used < victim->last_used) victim = &set[way];
    }

    // evicting a dirty line costs one writeback
    // a clean one costs none.
    const bool writeback = victim->valid && victim->dirty;
    if (writeback) ++stats_.writebacks;

    // Write-allocate: a write miss fills the line, then dirties it.
    victim->valid = true;
    victim->dirty = (type == AccessType::Write);
    victim->tag = parts.tag;
    victim->last_used = tick_;

    ++stats_.misses;
    return AccessResult{false, writeback,
                        cfg_.miss_cycles + (writeback ? cfg_.writeback_cycles : 0u)};
}

std::uint64_t Cache::total_cycles() const {
    return stats_.hits * cfg_.hit_cycles + stats_.misses * cfg_.miss_cycles +
           stats_.writebacks * cfg_.writeback_cycles;
}

}  // namespace cachelab
