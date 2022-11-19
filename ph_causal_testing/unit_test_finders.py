"""Classes and functions for finding existing tests in the user's project."""


from ph_causal_testing.class_for_test_method import TestMethod
from ph_variable_sharing import shared_variables
from ph_basic_processing.parsers import strip_file_extension, strip_custom, remove_trailing_comment, strip_trailing_newline

from os import walk, path
from sys import executable


#
# HELPER FUNCTIONS
#
def find_tests_of_same_files_methods_and_classes(original_test, dev_only_test_mode: bool):
    """Return the set of all TestMethod objects that reference a nonempty subset of the user-written
    files/methods/classes referenced by the original test, and are not the exact same test.
    :param original_test:           TestMethod object for the user's original test
    :param dev_only_test_mode:      whether --dev_only_test_mode was set to True when py-holmes was called from the command line
    """
    # Handle errors
    # original_test not a TestMethod object
    if not isinstance(original_test, TestMethod):
        raise TypeError("original_test must be a TestMethod object")
    # dev_only_test_mode not a bool
    if not isinstance(dev_only_test_mode, bool):
        raise TypeError("dev_only_test_mode must be a bool")

    # Search the project folder (excluding the Python executable's folder) to get all_tests, a list of absolute paths to Python files in the project that begin or end with "test"
    all_tests = []
    shared_variables.initialize_all_dirs_to_search()    # TODO: Added this line for easier testing.  In the future, should remove to save time and accomplish testing some other way
    dirs_to_search = shared_variables.all_dirs_to_search.copy()
    del dirs_to_search[1:3]     # Remove default python install location and executable location; we don't want to search these.
    executable_outermost_folder = path.dirname(path.dirname(executable))
    for this_root_dir in dirs_to_search:
        for root, dirs, files in walk(this_root_dir):
            for this_dir in dirs:
                if path.join(root, this_dir) == executable_outermost_folder:    # Avoid the Python installation being used and its third-party packages
                    dirs.remove(this_dir)
            for this_file in files:
                if this_file.endswith(".py"):
                    this_file_no_extension = strip_file_extension(this_file)
                    if this_file_no_extension.startswith("test") or this_file_no_extension.endswith("test"):
                        # Add all test methods from this file to all_tests
                        try:    # We use a try-except block here because the file may not contain unittests despite its name
                            test_methods_in_this_file = find_all_test_methods_in_file(path.join(root, this_file), post_as_user_test_method_objects=True)
                            all_tests += test_methods_in_this_file.copy()
                        except ValueError as err:
                            pass

    # For each test in all_tests, if this test's files_methods_and_classes_testing is a nonempty subset of
    # original_test.files_methods_and_classes_testing, and it is not the exact same test,
    # then add this test to output_tests
    output_tests = []
    for this_test in all_tests:
        if len(this_test.files_methods_and_classes_testing) != 0 and this_test.files_methods_and_classes_testing <= original_test.files_methods_and_classes_testing:
            if not (this_test.test_filepath == original_test.test_filepath and this_test.test_name == original_test.test_name):
                output_tests.append(this_test)

    # If in dev-only test mode, print a few attributes of each TestMethod object in output_tests
    if dev_only_test_mode:
        print("BEGIN ATTRIBUTES OF FOUND TESTMETHOD OBJECTS BEFORE CUTTING")
        counter = 0
        for obj in output_tests:
            print(f"BEGIN ATTRIBUTES FOR FOUND TESTMETHOD {counter}")
            print(f"TEST FILEPATH: {obj.test_filepath}")
            print(f"TEST CLASS: {obj.test_class}")
            print(f"TEST NAME: {obj.test_name}")
            print(f"END ATTRIBUTES FOR FOUND TESTMETHOD {counter}")
            counter += 1
        print("END ATTRIBUTES OF FOUND TESTMETHOD OBJECTS BEFORE CUTTING")

    # Return!
    return set(output_tests)


def find_all_test_methods_in_file(filepath: str, post_as_user_test_method_objects=False, origin="found") -> list:
    """Return a list of all test methods within a file, as TestMethod objects.  Also save these objects using
    shared_variables.initialize() for future use.
    :param filepath:                                absolute path to the file to search
    :param post_as_user_test_method_objects:        whether to post the found test methods to shared_variables
    :param origin:                                  to be passed as origin to TestMethod (eg "found" or "fuzzed")
    """
    # Handle errors
    # filepath not a string
    if not isinstance(filepath, str):
        raise TypeError("filepath must be a string")
    # filepath empty
    if len(filepath) == 0:
        raise ValueError("filepath must not be empty")
    # filepath not an absolute filepath
    if filepath != path.abspath(filepath):
        raise ValueError("filepath must be an absolute filepath")

    # Get the contents of the file and strip ending newlines
    with open(filepath, "r", encoding="utf-8") as file:
        file_content = file.readlines()
    for ii in range(len(file_content)):
        file_content[ii] = strip_trailing_newline(file_content[ii])

    # For each line that starts with "def test" and ends with ":" (after removing whitespace and trailing comments), create a TestMethod
    # object and append to all_test_methods
    all_test_methods = []
    for ll in range(len(file_content)):
        this_line = file_content[ll]
        # Strip
        this_line_no_whitespace_or_trailing_comments = remove_trailing_comment(this_line)
        this_line_no_whitespace_or_trailing_comments = strip_custom(this_line_no_whitespace_or_trailing_comments, ["\t", " "], "head")
        this_line_no_whitespace_or_trailing_comments = strip_custom(this_line_no_whitespace_or_trailing_comments, ["\t", " "], "tail")

        # If a def line whose function starts with "test", build and append a TestMethod object
        if this_line_no_whitespace_or_trailing_comments.startswith("def test") and this_line_no_whitespace_or_trailing_comments.endswith(":"):
            all_test_methods.append(TestMethod(origin, filepath, ll + 1, False, False))

    # Save these objects for future use     # TODO: Should this instead be done in find_tests_of_same_files_methods_and_classes?
    if post_as_user_test_method_objects:
        shared_variables.initialize(user_test_method_objects_in=all_test_methods)

    # Return!
    return all_test_methods
