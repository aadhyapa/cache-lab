#pragma once

#include <cstdint>
#include <istream>
#include <string>
#include <vector>

#include "access.hpp"

namespace cachelab {

struct TraceEntry {
    AccessType type = AccessType::Read;
    std::uint32_t address = 0;
};
bool read_trace(std::istream& in, std::vector<TraceEntry>& entries, std::string& error);

}  // namespace cachelab
