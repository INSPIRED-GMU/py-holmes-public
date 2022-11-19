"""Classes and functions to aid with removing leftover files etc."""


import os

from ph_variable_sharing import shared_variables

shared_variables.initialize()
ROOT_DIR = shared_variables.ROOT_DIR


#
# HELPER FUNCTIONS
#
def cleanup() -> None:
    """Remove key files that, if left over, may interfere with the flow of py-holmes."""
    for root, dirs, files in os.walk(ROOT_DIR):
        for this_file in ["test_outputs_fuzzed.py", "pylint_result.txt"]:
            if this_file in files:
                os.remove(os.path.join(root, this_file))
