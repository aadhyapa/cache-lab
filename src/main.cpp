#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "cache.hpp"
#include "cli.hpp"
#include "report.hpp"
#include "trace.hpp"

int main(int argc, char* argv[]) {
    cachelab::Options options;
    std::string error;

    // parse arguments
    if (!cachelab::parse_args(argc, argv, options, error) ||
        !options.config.validate(error)) {
        std::cerr << "error: " << error << '\n';
        return 2;
    }

    // CL-002: show how an address splits under this configuration.
    if (options.decode) {
        const cachelab::Cache cache(options.config);
        const cachelab::Address a = cache.decode(options.decode_addr);
        std::cout << std::hex << "tag=0x" << a.tag << " set=0x" << a.set << " offset=0x"
                  << a.offset << '\n';
        return 0;
    }

    // opening trace file and error handling
    std::ifstream trace_file(options.trace_path);
    if (!trace_file) {
        std::cerr << "error: cannot open trace file: " << options.trace_path << '\n';
        return 1;
    }
    std::vector<cachelab::TraceEntry> trace;
    if (!cachelab::read_trace(trace_file, trace, error)) {
        std::cerr << "error: " << options.trace_path << ": " << error << '\n';
        return 2;
    }

    // run the cache over the trace, recording each access's cost
    cachelab::Cache cache(options.config);
    std::vector<std::uint64_t> costs;
    costs.reserve(trace.size());
    for (const cachelab::TraceEntry& entry : trace) {
        costs.push_back(cache.access(entry.type, entry.address).cycles);
    }

    const cachelab::Summary summary = cachelab::summarize(cache, costs, options.window);
    if (options.json) cachelab::print_json(std::cout, summary);
    else cachelab::print_text(std::cout, summary);
    return 0;
}
