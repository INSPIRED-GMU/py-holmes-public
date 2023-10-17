"""Variables used by many programs in py-holmes are kept and managed here.
"""

#
# IMPORTS
#
import os
from os import path
from sys import executable

from ph_basic_processing.scrapers_for_holmesignore_and_holmessearchextend import parse_holmesignore, parse_holmessearchextend


#
# HELPER FUNCTIONS
#
def get_ignore_patterns():
    """Return an up-to-date list of patterns based on the current state of .holmesignore"""
    return parse_holmesignore()


def get_searchextend_patterns():
    """Return an up-to-date list of patterns based on the current state of .holmessearchextend"""
    return parse_holmessearchextend()


def get_lowest_dir_in_fragment(path_fragment: str) -> str:
    """Given some fragment of an absolute path (specifically which may be missing rightmost characters), return a crop
    of it that preserves the lowest-tier directory in it.  In other words, return the absolute path of the lowest-tier
    directory that's still legible from path_fragment.
    """
    # Handle errors
    # path_fragment not a string
    if not isinstance(path_fragment, str):
        raise TypeError("path_fragment must be a string")

    # Run
    # If the fragment points to an existing directory or file, just return the fragment; it's complete
    if path.exists(path_fragment) and (path.isdir(path_fragment) or path.exists(path_fragment)):
        return path_fragment
    # Else return the next directory up
    else:
        return path.dirname(path_fragment)


def initialize(file_in=None, lines_in=None, definition_line_in=None, tatosp_in=None, dev_only_test_mode_in=None, still_run_causal_testing_on_passing_tests_in=None, test_method_in=None, user_test_method_objects_in=None, variant_testing_time_limit_seconds_in=None, user_help_skip_in=None, num_test_variants_in=None, dl_in=None, seed_in="not_given", execution_path_suppress_in=None) -> None:
    """Set variables to be shared, or access those variables.
    For file_in, lines_in, tatosp_in, dev_only_test_mode_in, still_run_causal_testing_on_passing_tests_in, and
    test_method_in, calling initialize() without specifying an argument for that variable will leave that variable
    unchanged.
    The default value for seed_in is "not_given", rather than None, because None is a valid non-seed.
    file_in:    The name of the user's unit test file, ending with ".py".  Not an absolute filepath.
    tatosp_in:     How many spaces a tab is worth in the user's files
    definition_line_in:    The line on which the definition for the original test method appears, starting counting at 1
    user_test_method_objects_in: The set of all user-written test methods, as TestMethod objects.
    variant_testing_time_limit_seconds_in: Time limit for variant test running.
    """
    # Directory definitions, so that files in subdirectories can access files in other subdirectories
    global ROOT_DIR
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Assuming that py-holmes was installed correctly, the root project directory is the directory one level up from this one

    # Input arguments, as applicable
    if file_in is not None:
        global file
        file = file_in
        global file_absolute
        file_absolute = path.join(ROOT_DIR, file_in)
        if not file_absolute.endswith(".py"):
            raise RuntimeError("file_absolute must end with .py")
        global filename_with_file_extension
        filename_with_file_extension = path.basename(file_absolute)
        global filename_no_file_extension
        filename_no_file_extension = filename_with_file_extension[:-3]
    if lines_in is not None:
        global lines
        lines = lines_in
    if definition_line_in is not None:
        global definition_line
        definition_line = definition_line_in
    if tatosp_in is not None:
        global tatosp
        tatosp = tatosp_in
    if dev_only_test_mode_in is not None:
        global dev_only_test_mode
        dev_only_test_mode = dev_only_test_mode_in
    if still_run_causal_testing_on_passing_tests_in is not None:
        global still_run_causal_testing_on_passing_tests
        still_run_causal_testing_on_passing_tests = still_run_causal_testing_on_passing_tests_in
    if test_method_in is not None:
        global test_method
        test_method = test_method_in
    if user_test_method_objects_in is not None:
        global user_test_method_objects
        user_test_method_objects = user_test_method_objects_in
    if variant_testing_time_limit_seconds_in is not None:
        global variant_testing_time_limit_seconds
        variant_testing_time_limit_seconds = variant_testing_time_limit_seconds_in
    if user_help_skip_in is not None:
        global user_help_skip
        user_help_skip = user_help_skip_in
    if num_test_variants_in is not None:
        global num_test_variants
        num_test_variants = num_test_variants_in
    if dl_in is not None:
        global dl
        dl = dl_in
    if seed_in != "not_given":
        global seed
        seed = seed_in
    if execution_path_suppress_in is not None:
        global execution_path_suppress
        execution_path_suppress = execution_path_suppress_in

    # .pickle filename for original unit test running AND fuzzed unit test running
    global pickle_filename
    pickle_filename = "created_by_py_holmes_unittest_relevant_results.pickle"


def initialize_all_dirs_to_search() -> None:
    """Share all_dirs_to_search.  Initialize it too, if it hasn't already been initialized."""
    # List of all dirs to search for a file, including holmessearchextend_dirs, the list of dirs to search based on .holmessearchextend
    global all_dirs_to_search
    if "all_dirs_to_search" not in globals():    # If all_dirs_to_search hasn't been created yet, create it.
        from ph_basic_processing.parsers import string_until
        from ph_original_test_result_generation.ph_dir_and_file_finders.default_python_install_for_os_finders import get_python_path_for_platform
        holmessearchextend_dirs = []
        searchextend_patterns = get_searchextend_patterns()
        for this_searchextend_pattern in searchextend_patterns:
            # Parse
            this_searchextend_dir = string_until(this_searchextend_pattern, ["*", "?"])
            this_searchextend_dir = get_lowest_dir_in_fragment(this_searchextend_dir)
            holmessearchextend_dirs.append(this_searchextend_dir)
        all_dirs_to_search = [ROOT_DIR, path.dirname(path.dirname(executable)), get_python_path_for_platform()]
        for this_dir in holmessearchextend_dirs:
            all_dirs_to_search.append(this_dir)


def initialize_original_test_method_object(original_test_in=None) -> None:
    """Share original_test, the TestMethod object for the user's original test.
    :param original_test_in:        the object for the user's original test
    """
    if original_test_in is not None:
        global original_test
        original_test = original_test_in


def initialize_fuzzed_test_file(fuzzed_file_name_in=None, fuzzed_file_path_in=None) -> None:
    """Share the name and filepath of the file containing fuzzed tests.
    :param fuzzed_file_name_in:    the name of the file (no path), including file extension
    :param fuzzed_file_path_in:    the absolute path of the file, including file extension
    """
    if fuzzed_file_name_in is not None:
        global fuzzed_file_name
        fuzzed_file_name = fuzzed_file_name_in
    if fuzzed_file_path_in is not None:
        global fuzzed_file_path
        fuzzed_file_path = fuzzed_file_path_in


def initialize_original_call_sequence(original_call_sequence_in=None) -> None:
    """Share the sequence of calls made in the original test.
    :param original_call_sequence_in:   list of strings representing the calls made, in order
    """
    if original_call_sequence_in is not None:
        global original_call_sequence
        original_call_sequence = original_call_sequence_in


def initialize_user_response_for_oracle_checking(response_in=None) -> None:
    """Share user responses on whether certain arguments in Class 2 asserts are oracle arguments.
    Format for response_in: # Element 0 is the previous response, element 1 is the path to the Attribute object that was in question, element 2 is the argument index for which the response was given, element 3 is the name of the test
    """
    global responses
    if response_in is not None:
        try:
            responses.append(response_in)
        except NameError as err:
            responses = [response_in]
    else:
        try:
            responses   # Check if it exists
        except NameError as err:
            responses = []
