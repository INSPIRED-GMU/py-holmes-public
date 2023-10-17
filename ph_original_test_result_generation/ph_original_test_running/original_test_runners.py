"""Classes and functions for running the user's original test and extracting data for use later in causal testing."""

from io import StringIO
import unittest
from warnings import warn
import os
import trace
import io
from contextlib import redirect_stdout
from ast import parse
import pickle

from ph_basic_processing.parsers import remove_leading_substring, get_folder_delimiter, get_indices_containing_function_body_and_indentation_of_definition, count_indentation_in_spaces, get_method_name_from_definition_line, leading_spaces_of, find_class_containing_method, get_call_from_traceback
from ph_basic_processing.stripping import strip_custom
from ph_original_test_result_generation.ph_original_test_running.importers import *
from ph_basic_processing.trace_exit_line_adders import add_exit_lines_to_trace, remove_before_user_runtime, remove_after_user_runtime


#
# CLASSES
#
class OriginalUnitTestResult:
    """Container for those results of an original unit test that are relevant for causal testing."""

    def __init__(self, input_args_tree=None, execution_path=None, failed=None, traceback=None, trace_indices_descended_from_non_ignored_user_code=None, test_class_string=None, test_method_string=None, involved_user_and_py_holmes_modules=None, activations=None) -> None:
        """
        :param input_args_tree: Python ast containing arguments of BOTH the first assert failed in this test-case method AND the function tested within that assert
        :param execution_path: String.  Execution trace in string form.  ONLY INCLUDES THE LINES RUN DURING THE USER'S TEST'S RUNTIME; lines from before and after this have been cropped away
        :param failed: Boolean.  True if one or more assert calls in the test failed, else False.
        :param traceback: String of traceback
        :param trace_indices_descended_from_non_ignored_user_code: List of ints.  Indices of lines of execution_path that are linelogs descended from user code not in .holmesignore
        :param test_class_string: String.  The type of the class containing the test.  For example, "<class 'circle_method_test.TestCircleArea'>"
        :param test_method_string: The name of the test method, without parentheses.  For example: "test_values"
        :param involved_user_and_py_holmes_modules: A list of user and py-holmes module names (without a file extension) used in the entire (pre-cropping) trace.  Holmesignored modules are not excluded from this list.
        :param activations: Only for use when py-holmes is being used with the --dl flag.  Dictionary of tensors representing the activation of each layer.
        """
        self.input_args_tree = input_args_tree
        self.execution_path = execution_path
        self.failed = failed
        self.traceback = traceback
        self.trace_indices_descended_from_non_ignored_user_code = trace_indices_descended_from_non_ignored_user_code
        self.test_class_string = test_class_string
        self.test_method_string = test_method_string
        self.involved_user_and_py_holmes_modules = involved_user_and_py_holmes_modules
        self.activations = activations


#
# HELPER FUNCTIONS
#
def build_and_run_test_suite_dl() -> dict:
    """Build a test suite containing the original test, run, and return neuron activations."""
    # Get inputs via globaling, to get around NameError: name 'foo' is not defined
    from ph_variable_sharing import shared_variables
    shared_variables.initialize()
    pickle_filename = shared_variables.pickle_filename
    file_absolute = shared_variables.file_absolute
    ROOT_DIR = shared_variables.ROOT_DIR
    tatosp = shared_variables.tatosp
    dev_only_test_mode = shared_variables.dev_only_test_mode

    # Change to the working directory of the test file, and remember the previous directory for changing back
    if os.path.dirname(file_absolute) != ROOT_DIR:
        old_working_directory = os.getcwd()
        os.chdir(ROOT_DIR)  # Step up to the top of the project so that we can avoid having to step upward to reach the file
        folder_change = remove_leading_substring(ROOT_DIR, file_absolute)
        folder_delimiter = get_folder_delimiter(folder_change)
        folder_change = concatenate_list_to_string(folder_change.split(folder_delimiter)[:-1], between=folder_delimiter)    # Remove file from end, so that folder_change is a string of only directories
        if folder_change.startswith(folder_delimiter):
            folder_change = folder_change[1:]
        if folder_change.endswith(folder_delimiter):
            folder_change = folder_change[:-1]
        os.chdir(folder_change)     # Step down to the folder containing the test file

    # Without modifying the user-written test file, create a new test that matches the original, except inject the
    # creation of a pickle file to hold neuron activations
    # Get original file content as string
    with open(file_absolute, "r", encoding="utf-8") as file:
        file_content = file.read().split("\n")
    # Get the part of the file that is our function specifically
    index_body_start, index_body_end, definition_indentation = get_indices_containing_function_body_and_indentation_of_definition(file_content, test_case_as_string)
    body_indentation = definition_indentation + tatosp
    function_body = file_content.copy()[index_body_start:index_body_end]
    # Put test content in a try block
    function_body.insert(0, f"{' '*body_indentation}try:")
    for ll, line in enumerate(function_body):
        if ll >= 1:
            function_body[ll] = " "*tatosp + function_body[ll]
    # Before try block, import pickle, add a variable to check whether the test failed, a dictionary to hold
    # activations, and declare a function to get activations
    function_body = [
        " "*body_indentation + "import pickle",
        " "*body_indentation + "ph_test_failed = False",
        " "*body_indentation + "ph_activation = {}",
        "",
        " "*body_indentation + "def ph_get_activation(name):",
        " "*body_indentation + " "*tatosp + "def hook(model, input, output):",
        " "*body_indentation + " "*tatosp*2 + "ph_activation[name] = output.detach()",
        " "*body_indentation + " "*tatosp + "return hook",
        "",
                    ] + function_body
    # Just after model is instantiated, add a hook to each layer.  These hooks allow us to retrieve the activations of
    # neurons in the model after it's fed an input.
    model_instantiation_line = None
    for ll, line in enumerate(function_body):
        if "model = " in line:
            model_instantiation_line = ll
            model_instantiation_indentation = count_indentation_in_spaces(line)
            break
    if model_instantiation_line is None:
        raise RuntimeError("could not find model instantiation in test method")
    function_body.insert(model_instantiation_line+1, " "*model_instantiation_indentation + "for ph_modulename in model._modules:")
    function_body.insert(model_instantiation_line+2, " "*model_instantiation_indentation + " "*tatosp + '''eval(f"model.{ph_modulename}.register_forward_hook(ph_get_activation('{ph_modulename}'))")''')
    # Add an "except AssertionErr as err" block that sets the failed flag to true
    function_body += [
        " "*body_indentation + "except AssertionError as err:",
        " "*body_indentation + " "*tatosp + "ph_test_failed = True",
    ]
    # Add a finally block that writes the pickle file and raises an AssertionError if the test failed.
    function_body += [
        " "*body_indentation + "finally:",
        " "*body_indentation + " "*tatosp + '''with open("ph_activations.pickle", "wb") as pickle_file:''',
        " "*body_indentation + " "*tatosp*2 + '''pickle.dump(ph_activation, pickle_file)''',
        " "*body_indentation + " "*tatosp + '''if ph_test_failed:''',
        " "*body_indentation + " "*tatosp*2 + '''raise AssertionError("test failed")''',
    ]
    # Replace the part of file_content that contains our function body with our new function body
    if index_body_end is None:
        file_content = file_content[:index_body_start] + function_body
    else:
        file_content = file_content[:index_body_start] + function_body + file_content[index_body_end:]
    # Write to new file
    with open("ph_test_hooked.py", "w", encoding="utf-8") as file:
        for line in file_content:
            file.write(line + "\n")

    # If in dev-only test mode, print content of new file
    if dev_only_test_mode:
        print("HOOKED ORIGINAL TEST FILE CONTENT:\n" + concatenate_list_to_string(file_content, "\n"))

    # Build a test suite which contains only this test method
    test_class = import_by_string(importstring)
    suite = unittest.TestSuite()
    suite.addTest(test_class(test_case_as_string))

    # Run test and get results
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream)
    output_runner_result = runner.run(suite)    # Unit test result
    with open("ph_activations.pickle", "rb") as pickle_file:
        activations = pickle.load(pickle_file)
    os.remove("ph_activations.pickle")

    # Revert to whatever directory we were in before this was called
    if os.path.dirname(file_absolute) != ROOT_DIR:
        os.chdir(old_working_directory)

    # If we encountered any errors (not just failures), warn the user
    if len(output_runner_result.errors) > 0:
        warning_text = "The following tests were interrupted due to the following error(s) (not just failure(s)):"
        for this_error in output_runner_result.errors:
            warning_text = warning_text + "\n" + str(this_error)
        warn(warning_text)

    # Warn the user if there's already a file with the name pickle_filename
    if os.path.exists(pickle_filename):
        response = input(
            pickle_filename + " already exists in the uppermost project directory. py-holmes needs to overwrite this file. Continue? (Y/n): ")
        if response in ["Y", "y"]:
            print("Deleting " + pickle_filename)
            os.remove(pickle_filename)
        else:
            print("Exiting")
            exit()
    # Create the .pickle file with all info we need
    with open(pickle_filename, "wb") as pickle_file:
        # Create a dictionary of all relevant results
        len_failures = len(output_runner_result.failures)
        dictionary = {
            "length_of_failures_list": len_failures,
            "failed_test_traceback": output_runner_result.failures[0][1] if len_failures > 0 else None,
            "test_class_string_version": str(test_class),
            "test_case_string_version": test_case_as_string,
            "activations": activations,
        }
        pickle.dump(dictionary, pickle_file)


def build_and_run_test_suite() -> None:
    """To be traced by the python trace module, called by get_unit_test_result().
    Build a test suite containing the original test, run, and return test results by creating a .pickle file.
    """
    # Get inputs via globaling, to get around NameError: name 'foo' is not defined
    global test_case_as_string
    global class_as_string
    global test_filename_without_file_extension
    global line_number
    global importstring
    line_number_as_int = int(line_number)
    from ph_variable_sharing import shared_variables
    shared_variables.initialize()
    pickle_filename = shared_variables.pickle_filename
    file_absolute = shared_variables.file_absolute
    ROOT_DIR = shared_variables.ROOT_DIR

    # Change to the working directory of the test file, and remember the previous directory for changing back
    if os.path.dirname(file_absolute) != ROOT_DIR:
        old_working_directory = os.getcwd()
        os.chdir(ROOT_DIR)  # Step up to the top of the project so that we can avoid having to step upward to reach the file
        folder_change = remove_leading_substring(ROOT_DIR, file_absolute)
        folder_delimiter = get_folder_delimiter(folder_change)
        folder_change = concatenate_list_to_string(folder_change.split(folder_delimiter)[:-1], between=folder_delimiter)    # Remove file from end, so that folder_change is a string of only directories
        if folder_change.startswith(folder_delimiter):
            folder_change = folder_change[1:]
        if folder_change.endswith(folder_delimiter):
            folder_change = folder_change[:-1]
        os.chdir(folder_change)     # Step down to the folder containing the test file

    # Build a test suite which contains only this test method
    test_class = import_by_string(importstring)
    suite = unittest.TestSuite()
    suite.addTest(test_class(test_case_as_string))

    # Run test and get results
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream)
    output_runner_result = runner.run(suite)    # Unit test result

    # Revert to whatever directory we were in before this was called
    if os.path.dirname(file_absolute) != ROOT_DIR:
        os.chdir(old_working_directory)

    # If we encountered any errors (not just failures), warn the user
    if len(output_runner_result.errors) > 0:
        warning_text = "The following tests were interrupted due to the following error(s) (not just failure(s)):"
        for this_error in output_runner_result.errors:
            warning_text = warning_text + "\n" + str(this_error)
        warn(warning_text)

    # In a perfect world, we'd want to return output_runner_result.  But because build_and_run_test_suite() gets called
    # by tracer.run() in get_unit_test_result(), and tracer.run() returns None due to the way trace.py is designed, we
    # instead have to write the important part(s) of the runner_result to a file.

    # Warn the user if there's already a file with the name pickle_filename
    if os.path.exists(pickle_filename):
        response = input(pickle_filename + " already exists in the uppermost project directory. py-holmes needs to overwrite this file. Continue? (Y/n): ")
        if response in ["Y", "y"]:
            print("Deleting " + pickle_filename)
            os.remove(pickle_filename)
        else:
            print("Exiting")
            exit()
    # Create the .pickle file with all info we need
    with open(pickle_filename, "wb") as pickle_file:
        # Create a dictionary of all relevant results
        len_failures = len(output_runner_result.failures)
        dictionary = {
            "length_of_failures_list": len_failures,
            "failed_test_traceback": output_runner_result.failures[0][1] if len_failures > 0 else None,
            "test_class_string_version": str(test_class),
            "test_case_string_version": test_case_as_string
        }
        pickle.dump(dictionary, pickle_file)


def get_unit_test_result(test_filepath_temp: str, test_filename_temp: str, line_number_temp: int) -> OriginalUnitTestResult:
    """Return an OriginalUnitTestResult object for the test case in test_filepath_temp at line line_number_temp.
    line_number_temp indexes starting from 1, not 0.
    test_filepath_temp includes test_filename_temp, preceded by leading folders
    If line_number points to a line within a test case, then that test case will be run from the top.  However, note
    that an early failure in the test case may prevent testing from reaching the line specified on line_number.
    For this reason it is recommended to minimize the number of assert calls per unit test case method, ideally down to
    1.
    """
    # Handle errors
    # test_filepath_temp not a string
    if not isinstance(test_filepath_temp, str):
        raise TypeError("test_filepath_temp must be a string")
    # test_filepath_temp doesn't end with .py
    if not test_filepath_temp.endswith(".py"):
        raise ValueError("test_filepath_temp must end with .py")
    # test_filename_temp not a string
    if not isinstance(test_filename_temp, str):
        raise TypeError("test_filename_temp must be a string")
    # line_number_temp not an int
    if not isinstance(line_number_temp, int):
        raise TypeError("line_number_temp must be a string")

    # Global some variables for later use by build_and_run_test_suite()
    global test_case_as_string
    global class_as_string
    global test_filename_without_file_extension
    global line_number
    global importstring
    from ph_variable_sharing import shared_variables
    shared_variables.initialize()
    pickle_filename = shared_variables.pickle_filename
    line_number = line_number_temp

    # Create test_filename_with_file_extension and test_filename_without_file_extension
    if len(test_filepath_temp) <= 3 and ".py" not in test_filepath_temp:    # Handle 3-character or shorter filenames missing .py
        test_filename_without_file_extension = test_filename_temp
        test_filename_with_file_extension = test_filename_temp + ".py"
    if test_filepath_temp[-3:] == ".py":
        test_filename_without_file_extension = test_filename_temp[:-3]
        test_filename_with_file_extension = test_filename_temp
    else:
        test_filename_without_file_extension = test_filename_temp
        test_filename_with_file_extension = test_filename_temp + ".py"

    # Get line number as index
    line_number_as_index = line_number - 1  # For indexing starting at 0

    # Determine which test case contains line_number
    # Get the content of the test
    with open(test_filepath_temp, "r", encoding="utf-8") as file:
        test_module_content = file.readlines()
    # Find the test case we want
    test_case_as_string = None
    def_line_index = None
    leading_spaces_of_def_line = None
    if strip_custom(test_module_content[line_number_as_index], ["\t", " "], "head")[:8] == "def test":    # If line_number already points to the definition line, just grab it
        test_case_as_string = get_method_name_from_definition_line(test_module_content[line_number_as_index])
        leading_spaces_of_def_line = leading_spaces_of(test_module_content[line_number_as_index])
        def_line_index = line_number_as_index
    else:   # Else, we have to search upward, by beginning at the line just above line_number, then going upward one line at a time until we find a line that starts with "{ , \t}*def test" and that has fewer leading spaces/tabs than the line at line_number
        leading_spaces_for_line_number = leading_spaces_of(test_module_content[line_number_as_index])
        for ii in range(line_number_as_index-1, -1, -1):
            # If this line has fewer leading spaces/tabs than the line at line_number:
            if leading_spaces_of(test_module_content[ii]) < leading_spaces_for_line_number:
                # If, after stripping leading tabs and spaces, this line starts with "def test":
                if strip_custom(test_module_content[ii], ["\t", " "], "head")[:8] == "def test":
                    # This must be the method definition line that we want.  Get the name of the method.
                    test_case_as_string = get_method_name_from_definition_line(test_module_content[ii])
                    leading_spaces_of_def_line = leading_spaces_of(test_module_content[ii])
                    def_line_index = ii
                    break

    # Handle error if no test case method found containing the line
    if test_case_as_string is None:
        raise ValueError("No test case method found containing line " + str(line_number))

    # Post test_case_as_string and def_line_index+1 to shared_variables, so that other files can access them
    shared_variables.initialize(test_method_in=test_case_as_string, definition_line_in=def_line_index+1)

    # Check that there's actual code within the test method
    triple_quotes_encountered = 0
    for ii in range(def_line_index+1, len(test_module_content)):
        triple_quotes_index_this_line = None    # Index of the first quote in triple quotes
        opened_by = None    # String; keeps track of whether the current docstring was created by """ or '''
        this_line = test_module_content[ii]
        this_line_head_stripped = strip_custom(this_line, ["\t", " "], "head")
        this_line_tail_stripped = strip_custom(this_line, ["\t", " ", "\n"], "tail")
        this_line_both_stripped = strip_custom(this_line_head_stripped, ["\t", " ", "\n"], "tail")
        leading_spaces_of_this_line = leading_spaces_of(this_line)
        # Handle docstring triple quotes at front of line
        if len(this_line_both_stripped) >= 3:
            # If this line begins with triple quotes that actually initiate a new docstring or terminate the current
            # one, increment triple_quotes_encountered
            if this_line_head_stripped.startswith('"""') and not (triple_quotes_encountered % 2 != 0 and opened_by == "'''"):
                triple_quotes_encountered += 1
                triple_quotes_index_this_line = this_line.index('"""')
                if triple_quotes_encountered % 2 == 0:
                    opened_by = None
                else:
                    opened_by = '"""'
            elif this_line_head_stripped.startswith("'''") and not (triple_quotes_encountered % 2 != 0 and opened_by == '"""'):
                triple_quotes_encountered += 1
                triple_quotes_index_this_line = this_line.index("'''")
                if triple_quotes_encountered % 2 == 0:
                    opened_by = None
                else:
                    opened_by = "'''"
        # If this line isn't just part of a docstring:
        if triple_quotes_encountered % 2 == 0:
            # If this line is part of the function definition, we're in the clear; break the loop
            if leading_spaces_of_this_line > leading_spaces_of_def_line:
                break
        # Handle docstring triple quotes at end of line
        if len(this_line_both_stripped) >= 3:
            # If this line ends with triple quotes, and they aren't the same triple quotes that we already counted, and these quotes actually initiate a new docstring or terinate the current one, increment triple_quotes_encountered
            if ((this_line_tail_stripped.endswith('"""') and not (triple_quotes_encountered % 2 != 0 and opened_by == "'''")) or (this_line_tail_stripped.endswith("'''") and not (triple_quotes_encountered % 2 != 0 and opened_by == '"""'))) and len(this_line) - 4 != triple_quotes_index_this_line:
                triple_quotes_encountered += 1
                if triple_quotes_encountered % 2 == 0:
                    opened_by = None
                else:
                    opened_by = this_line_tail_stripped[-3:]
        # If we haven't broken the loop by the time we reach a non-whitespace line with indentation equal to or less than the definition line's indentation, or if we've reached this point in the current iteration and this is the last line in the file, then the function contains no content.  Raise an error
        if (leading_spaces_of_this_line <= leading_spaces_of_def_line and this_line_both_stripped != "") or ii == len(test_module_content)-1:
            raise ValueError("Test method " + test_case_as_string + " contains no code")

    # Warn the user if there are no assert calls within the test method
    triple_quotes_encountered = 0
    for ii in range(def_line_index+1, len(test_module_content)):
        triple_quotes_index_this_line = None
        opened_by = None    # String; keeps track of whether the current docstring was created by """ or '''
        this_line = test_module_content[ii]
        this_line_head_stripped = strip_custom(this_line, ["\t", " "], "head")
        this_line_tail_stripped = strip_custom(this_line, ["\t", " ", "\n"], "tail")
        this_line_both_stripped = strip_custom(this_line_head_stripped, ["\t", " ", "\n"], "tail")
        leading_spaces_of_this_line = leading_spaces_of(this_line)
        # Handle docstring triple quotes at front of line
        if len(this_line_both_stripped) >= 3:
            # If this line begins with triple quotes that actually initiate a new docstring or terminate the current
            # one, increment triple_quotes_encountered
            if this_line_head_stripped.startswith('"""') and not (triple_quotes_encountered % 2 != 0 and opened_by == "'''"):
                triple_quotes_encountered += 1
                triple_quotes_index_this_line = this_line.index('"""')
                if triple_quotes_encountered % 2 == 0:
                    opened_by = None
                else:
                    opened_by = '"""'
            elif this_line_head_stripped.startswith("'''") and not (triple_quotes_encountered % 2 != 0 and opened_by == '"""'):
                triple_quotes_encountered += 1
                triple_quotes_index_this_line = this_line.index("'''")
                if triple_quotes_encountered % 2 == 0:
                    opened_by = None
                else:
                    opened_by = "'''"
        # If this line isn't just part of a docstring:
        if triple_quotes_encountered % 2 == 0:
            # If this line is part of the function definition and contains the word assert, break the loop
            if leading_spaces_of_this_line > leading_spaces_of_def_line and "assert" in this_line and this_line_head_stripped[:3] != '"""':
                break
        # Handle docstring triple quotes at end of line
        if len(this_line_both_stripped) >= 3:
            # If this line ends with triple quotes, and they aren't the same triple quotes that we already counted, and these quotes actually initiate a new docstring or terinate the current one, increment triple_quotes_encountered
            if ((this_line_tail_stripped.endswith('"""') and not (triple_quotes_encountered % 2 != 0 and opened_by == "'''")) or (this_line_tail_stripped.endswith("'''") and not (triple_quotes_encountered % 2 != 0 and opened_by == '"""'))) and len(this_line) - 4 != triple_quotes_index_this_line:
                triple_quotes_encountered += 1
                if triple_quotes_encountered % 2 == 0:
                    opened_by = None
                else:
                    opened_by = this_line_tail_stripped[-3:]
        # If we haven't broken the loop by the time we reach a non-whitespace line with indentation equal to or less than the definition line's indentation, or if we've reached this point in the current iteration and this is the last line in the file, then the function does not contain the word assert.  Raise a warning
        if (leading_spaces_of_this_line <= leading_spaces_of_def_line and this_line_both_stripped != "") or ii == len(test_module_content)-1:
            warn("No assert calls in function " + test_case_as_string)


    # Find the class containing this test method by searching upward, beginning at the line just above line_number, then going upward one line at a time until we find a line that starts with "{ , \t}*class " and that has fewer leading spaces/tabs than the line at line_number
    class_as_string = find_class_containing_method(line_number, test_module_content)[0]

    # Build importstring
    folder_delimiter = get_folder_delimiter(test_filepath_temp)
    if folder_delimiter in test_filepath_temp:  # If the file isn't in the top-level directory:
        before_class = test_filepath_temp.replace(folder_delimiter, ".")
        if before_class.endswith(".py"):
            before_class = before_class[:-3]
        if shared_variables.dl:  # If running in dl mode, change the name of the containing file to ph_test_hooked because this is where the hooked version of the user-written test will be created.
            before_class[-1] = "ph_test_hooked"
        importstring = f"from {before_class} import {class_as_string}"
    else:   # File IS in the top-level directory
        if shared_variables.dl:  # If running in dl mode, change the name of the containing file to ph_test_hooked because this is where the hooked version of the user-written test will be created.
            importstring = f"from ph_test_hooked import {class_as_string}"
        else:
            importstring = f"from {test_filename_without_file_extension} import {class_as_string}"

    # Run the test and get either execution information or neuron activation information, depending on whether the user gave the --dl flag.
    if shared_variables.dl:
        # Run test and get neuron activation information
        try:
            build_and_run_test_suite_dl()
            with open(pickle_filename, "rb") as pickle_file:
                runner_result = pickle.load(pickle_file)
        finally:
            # Delete the pickle file; we have no more use for it
            os.remove(pickle_filename)

        # Get whether test failed (ie whether any asserts failed in this test-case method)
        test_failed = (runner_result["length_of_failures_list"] != 0)

        # Get the execution trace, unless the test didn't fail and the user didn't request causal testing be performed anyway
        still_run_causal_testing_on_passing_tests = shared_variables.still_run_causal_testing_on_passing_tests
        if test_failed or still_run_causal_testing_on_passing_tests:
            activations = runner_result["activations"]
        else:
            activations = None

        if test_failed:
            # Get the traceback of the failing test
            test_traceback = runner_result["failed_test_traceback"]

            # Get the string of the assert call that failed
            failed_assert_call = get_call_from_traceback(test_traceback)

            # Get input arguments of BOTH the first assert failed in this test-case method AND the function tested within that assert
            test_args_tree = parse(failed_assert_call)

            # Get test class and case
            test_class_string_version = runner_result["test_class_string_version"]
            test_case_string_version = runner_result["test_case_string_version"]
        else:
            test_traceback = runner_result["failed_test_traceback"]
            failed_assert_call = None
            test_args_tree = None
            test_class_string_version = runner_result["test_class_string_version"]
            test_case_string_version = runner_result["test_case_string_version"]

        # Return an OriginalUnitTestResult object with the information that we need for causal testing
        return OriginalUnitTestResult(input_args_tree=test_args_tree,
                                      failed=test_failed, traceback=test_traceback,
                                      test_class_string=test_class_string_version,
                                      test_method_string=test_case_string_version,
                                      activations=activations)
    else:
        # Run test and get results, simultaneously tracing execution.
        # Getting tracer results involves redirecting stdout to a buffer and capturing it later as a variable.
        # Getting unittest runner results requires reading the important results from a pickle
        # that build_and_run_test_suite() writes
        tracer = trace.Trace(count=0, trace=1, countfuncs=0, countcallers=0, ignoremods=(), ignoredirs=(), infile=None, outfile=None, timing=False)
        trace_buffer = io.StringIO()
        try:
            with redirect_stdout(trace_buffer):   # To prevent the execution trace from getting printed to the screen
                tracer.run("build_and_run_test_suite()")   # Unit test result.  Running this line leads to warning about using PyDev debugger with sys.settrace()
            with open(pickle_filename, "rb") as pickle_file:
                runner_result = pickle.load(pickle_file)
        finally:
            # Delete the pickle file; we have no more use for it
            os.remove(pickle_filename)

        # Get whether test failed (ie whether any asserts failed in this test-case method)
        test_failed = (runner_result["length_of_failures_list"] != 0)

        # Get the execution trace, unless the test didn't fail and the user didn't request causal testing be performed anyway
        still_run_causal_testing_on_passing_tests = shared_variables.still_run_causal_testing_on_passing_tests
        if test_failed or still_run_causal_testing_on_passing_tests:
            tracer_result = trace_buffer.getvalue()
            tracer_result = remove_before_user_runtime(tracer_result)
            tracer_result, non_ignored_user_code_indices, traced_user_and_py_holmes_modules = add_exit_lines_to_trace(tracer_result)  # Add exit lines to tracer_result for every time we exit a function or class, and do some other touch-ups as well
            # Remove all but the user's runtime from the execution trace, and update non_ignored_user_code_indices accordingly
            tracer_result, non_ignored_user_code_indices = remove_after_user_runtime(tracer_result, non_ignored_user_code_indices)
        else:
            tracer_result = None
            non_ignored_user_code_indices = None
            traced_user_and_py_holmes_modules = None

        if test_failed:
            # Get the traceback of the failing test
            test_traceback = runner_result["failed_test_traceback"]

            # Get the string of the assert call that failed
            failed_assert_call = get_call_from_traceback(test_traceback)

            # Get input arguments of BOTH the first assert failed in this test-case method AND the function tested within that assert
            test_args_tree = parse(failed_assert_call)

            # Get execution path of failing test
            test_execution_path = tracer_result

            # Get indices of user-descended code
            test_trace_indices_descended_from_non_ignored_user_code = non_ignored_user_code_indices

            # Get test class and case
            test_class_string_version = runner_result["test_class_string_version"]
            test_case_string_version = runner_result["test_case_string_version"]

            # Get list of user modules used in the test.  Holmesignored user files are not excluded from this list.
            test_user_and_py_holmes_modules = traced_user_and_py_holmes_modules

        else:
            test_traceback = runner_result["failed_test_traceback"]
            failed_assert_call = None
            test_args_tree = None
            test_execution_path = tracer_result
            test_trace_indices_descended_from_non_ignored_user_code = non_ignored_user_code_indices
            test_class_string_version = runner_result["test_class_string_version"]
            test_case_string_version = runner_result["test_case_string_version"]
            test_user_and_py_holmes_modules = traced_user_and_py_holmes_modules

        # Return an OriginalUnitTestResult object with the information that we need for causal testing
        return OriginalUnitTestResult(input_args_tree=test_args_tree, execution_path=test_execution_path, failed=test_failed, traceback=test_traceback, trace_indices_descended_from_non_ignored_user_code=test_trace_indices_descended_from_non_ignored_user_code, test_class_string=test_class_string_version, test_method_string=test_case_string_version, involved_user_and_py_holmes_modules=test_user_and_py_holmes_modules)
