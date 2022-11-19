"""Classes and functions for gathering patterns from .holmesignore and .holmessearchextend"""


from os import path
from ph_basic_processing.parsers import strip_custom


#
# HELPER FUNCTIONS
#
def parse_holmesignore():
    """Read .holmesignore in the uppermost project directory and return a list of strings, where each string represents
    a UNIX-like pattern specified in .holmesignore.
    In the process, add all py-holmes files to .holmesignore.
    This function is called by shared_variables.py in the method get_ignore_patterns.
    """
    from ph_variable_sharing import shared_variables
    shared_variables.initialize()
    ROOT_DIR = shared_variables.ROOT_DIR

    # Check for any py-holmes files missing from .holmesignore
    py_holmes_patterns_missing_from_holmesignore = []
    if path.exists(".holmesignore"):
        with open(".holmesignore", "r", encoding="utf-8") as file:
            holmesignore_content = file.readlines()
    else:
        holmesignore_content = []
    all_py_holmes_patterns = [  # TODO: Update this list as necessary, as new files are added to the project
        #"/ph_benchmarks/*",           # Not included; this is used in development but not execution
        "/ph_basic_processing/*",
        "/ph_causal_testing/*",
        "/ph_dir_and_file_finders/*",
        "/ph_fault_assessment/*",
        "/ph_log_writing/*",
        "/ph_original_test_result_generation/*",
        #"/ph_traceback_dataset/*",    # Not included; this is used in development but not execution
        #"/circle_method*",            # Not included; these files must be treated as user files for unit testing
        #"/test_empty_unittest_file.py",    # Not included; these files must be treated as user files for unit testing
        #"/test_get_call_from_traceback.py*",  # Not included; this is used in development but not execution
        "/py_holmes.py",
        #"/test_py_holmes.py",
        "/py_holmes_built_to_fail.py",  # Generated and then deleted in testing
        "/test_outputs_fuzzed.py"   # Generated during runtime
    ]
    for this_py_holmes_pattern in all_py_holmes_patterns:
        if path.abspath(ROOT_DIR + this_py_holmes_pattern) + "\n" not in holmesignore_content:
            py_holmes_patterns_missing_from_holmesignore.append(this_py_holmes_pattern)

    # Append any missing patterns to .holmesignore
    if len(py_holmes_patterns_missing_from_holmesignore) > 0:
        for this_missing_pattern in py_holmes_patterns_missing_from_holmesignore:
            append_root_and_add_to_holmesignore(this_missing_pattern)

    # Grab ignore patterns from .holmesignore
    with open(".holmesignore", "r", encoding="utf-8") as file:
        file_content = file.readlines()
    # Build list of patterns to ignore by stripping newlines, omitting commented and blank lines, and converting to absolute paths
    output_list = []
    for this_line in file_content:
        if not this_line.startswith("#"):
            this_line_cleaned_up = strip_custom(this_line, ["\n", "\r", " "], "tail")
            if len(this_line_cleaned_up) != 0:
                if this_line_cleaned_up[-1] in ["/", "\\"]:
                    this_line_cleaned_up += "*"     # The user added a trailing slash because they wanted all subfiles/subdirectories to be implied
                this_line_cleaned_up = path.abspath(this_line_cleaned_up)
                output_list.append(this_line_cleaned_up)

    return output_list


def parse_holmessearchextend():
    """Read .holmessearchextend in the uppermost project directory and return a list of strings, where each string
    represents a UNIX-like pattern specified in .holmessearchextend.
    This function is called by py_holmes.py to create search_extend_patterns
    """
    # Grab searchextend patterns from .holmessearchextend
    if path.exists(".holmessearchextend"):
        with open(".holmessearchextend", "r", encoding="utf-8") as file:
            holmessearchextend_content = file.readlines()
    else:
        return []
    # Build list of patterns to search by stripping newlines, omitting commented and blank lines, and converting to absolute paths
    output_list = []
    for this_line in holmessearchextend_content:
        if not this_line.startswith("#"):
            this_line_cleaned_up = strip_custom(this_line, ["\n", "\r", " "], "tail")
            if len(this_line_cleaned_up) != 0:
                if this_line_cleaned_up[-1] in ["/", "\\"]:
                    this_line_cleaned_up += "*"     # The user added a trailing slash because they wanted all subfiles/subdirectories to be implied
                this_line_cleaned_up = path.abspath(this_line_cleaned_up)
                output_list.append(this_line_cleaned_up)

    return output_list


def append_root_and_add_to_holmesignore(input_path):
    """Append ROOT_DIR to input_path and add it to .holmesignore.
    Directories must be represented by /, not \\
    """
    from ph_variable_sharing import shared_variables
    shared_variables.initialize()
    ROOT_DIR = shared_variables.ROOT_DIR
    # Handle errors
    # input_path not a string
    if not isinstance(input_path, str):
        raise TypeError("input_path must be a string")
    # input_path empty
    if len(input_path) == 0:
        raise ValueError("input_path must not be empty")

    # Run
    # Add a leading "/" if there isn't one
    if input_path[0] != "/":
        input_path = "/" + input_path
    # Append
    with open(".holmesignore", "a", encoding="utf-8") as file:
        file.write("\n" + path.abspath(ROOT_DIR + input_path) + "\n")