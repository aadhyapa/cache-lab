# One-command workflow:
#   make test         build the simulator (warnings are errors) and run the tests;
#                     creates .venv with pytest on first use
#   make test SAN=1   same, with AddressSanitizer + UBSan (CL-015)
#   make matrix       regenerate docs/traceability.md (also done by make test)
#   make experiments  run the workloads and write results/results.csv and results/plots/
#   make setup        also install pandas, matplotlib and notebook (for the experiments)
#   make clean

CXX      ?= c++
BUILD    ?= build$(if $(SAN),-san)
SANFLAGS := -fsanitize=address,undefined -fno-sanitize-recover=undefined
CXXFLAGS ?= -std=c++20 -Wall -Wextra -Werror -O1 -g $(if $(SAN),$(SANFLAGS))
SRCS     := $(wildcard src/*.cpp)
HDRS     := $(wildcard src/*.hpp)
BIN      := $(BUILD)/cache_lab
PY       ?= .venv/bin/python

.PHONY: all test matrix experiments setup clean

all: $(BIN)

$(BIN): $(SRCS) $(HDRS)
	@mkdir -p $(BUILD)
	$(CXX) $(CXXFLAGS) -Isrc $(SRCS) -o $@

# Python environment: rebuilt whenever a requirements file changes.
.venv/.tests-ready: requirements.txt
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	@touch $@

.venv/.analysis-ready: requirements-analysis.txt .venv/.tests-ready
	.venv/bin/pip install -r requirements-analysis.txt
	@touch $@

test: $(BIN) .venv/.tests-ready
	CACHE_LAB=$(abspath $(BIN)) $(PY) -m pytest tests -q
	$(PY) tools/trace_matrix.py

matrix:
	python3 tools/trace_matrix.py

setup: .venv/.tests-ready .venv/.analysis-ready

experiments: $(BIN) .venv/.analysis-ready
	CACHE_LAB=$(abspath $(BIN)) $(PY) tools/run_experiments.py
	$(PY) tools/plot_results.py

clean:
	rm -rf build build-san
