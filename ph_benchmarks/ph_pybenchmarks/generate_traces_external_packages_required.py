"""Generate benchmark traces one by one.
Benchmark files are sourced from this website: https://pybenchmarks.org/
This file must by run by a python virtual environment that has gmpy2 and jinja2 installed.
"""

import os
from os import listdir
from os.path import isfile, join
import trace
import subprocess

from ph_variable_sharing import shared_variables
shared_variables.initialize()
ROOT_DIR = shared_variables.ROOT_DIR

folder = os.path.abspath(ROOT_DIR + "/ph_benchmarks/")
benchmark_dict = {  # Keys are benchmark filenames, without the .py file extension.  Values are the command line entry to run that benchmark correctly
    "benchmark_pidigits": 'python -m trace --trace "' + folder + 'benchmark_pidigits.py" 10000',
    "benchmark_templates": 'python -m trace --trace "' + folder + 'benchmark_templates.py" 1',
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
