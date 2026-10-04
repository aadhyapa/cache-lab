#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "cli.hpp"
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

    // Next: run Cache over the trace, print the report.
    return 0;
}
