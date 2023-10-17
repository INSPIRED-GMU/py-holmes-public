"""Generate benchmark traces one by one.
Benchmark files are sourced from this website: https://pybenchmarks.org/
"""

# Traces for the following benchmarks must be generated with an outside venv that has the required packages:
# benchmark_mandelbrot
# benchmark_pidigits
# benchmark_templates

import os
from os import listdir
from os.path import isfile, join
import trace
import subprocess

from ph_variable_sharing import shared_variables
shared_variables.initialize()
ROOT_DIR = shared_variables.ROOT_DIR

folder = ROOT_DIR + "/ph_benchmarks/"
benchmark_dict = {  # Keys are benchmark filenames, without the .py file extension.  Values are the command line entry to run that benchmark correctly
    "benchmark_chameneos_redux": 'python -m trace --trace "' + folder + 'benchmark_chameneos_redux.py" 6000',
    "benchmark_fibonacci": 'python -m trace --trace "' + folder + 'benchmark_fibonacci.py" 1000000',
    "benchmark_pystone": 'python -m trace --trace "' + folder + 'benchmark_pystone.py" 50000',
    "benchmark_richards": 'python -m trace --trace "' + folder + 'benchmark_richards.py" 10',
    "benchmark_thread_ring": 'python -m trace --trace "' + folder + 'benchmark_thread_ring.py" 5000000',
}

# For each benchmark, run and display the trace.
for this_benchmark in benchmark_dict:
    print("-" * 64)
    print("BEGIN " + this_benchmark.upper() + ".PY")
    try:
        execution_trace = subprocess.check_output(benchmark_dict[this_benchmark])
    except:
        print("RUN FOR " + this_benchmark.upper() + " FAILED")
    else:
        print("WRITING TRACE")
        with open("benchmark_traces/" + this_benchmark + "_trace.log", "w", encoding="utf-8") as file:
            file.write(execution_trace.decode("utf-8"))
        print("TRACE WRITTEN")
