#include "cache_config.hpp"

namespace cachelab {

bool CacheConfig::validate(std::string& error) const {
    if (!is_power_of_two(sets)) {
        error = "sets must be a power of two, got " + std::to_string(sets);
        return false;
    }
    if (!is_power_of_two(line_size)) {
        error = "line size must be a power of two, got " + std::to_string(line_size);
        return false;
    }
    if (ways == 0) {
        error = "ways must be at least 1";
        return false;
    }
    return true;
}

}  // namespace cachelab
