#pragma once

#include <bit>
#include <cstdint>

#include "cache_config.hpp"

namespace cachelab {

// bit address: tag | set index | byte offset
struct Address {
    std::uint32_t tag = 0;
    std::uint32_t set = 0;
    std::uint32_t offset = 0;
};

inline Address decode_address(const CacheConfig& config, std::uint32_t addr) {
    const unsigned offset_bits = std::countr_zero(config.line_size);
    const unsigned index_bits = std::countr_zero(config.sets);
    const std::uint64_t a = addr;

    Address address;
    address.offset = static_cast<std::uint32_t>(a & (config.line_size - 1));
    address.set = static_cast<std::uint32_t>((a >> offset_bits) & (config.sets - 1));
    address.tag = static_cast<std::uint32_t>(a >> (offset_bits + index_bits));
    return address;
}

}  // namespace cachelab
