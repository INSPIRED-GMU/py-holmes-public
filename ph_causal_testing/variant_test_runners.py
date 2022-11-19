"""Classes and functions for running variants of the original test and showing results"""


from datetime import datetime, timedelta
import unittest
import os
import json
import trace
import io
from io import StringIO
from contextlib import redirect_stdout
from warnings import warn
from difflib import ndiff
from colorama import Fore, Style
import importlib
from ast import parse
from astor import to_source
from importlib import import_module

from ph_original_test_result_generation.ph_original_test_running.original_test_runners import OriginalUnitTestResult
from ph_causal_testing.class_for_test_method import TestMethod
from ph_original_test_result_generation.ph_original_test_running.importers import import_by_string
from ph_basic_processing.trace_exit_line_adders import add_exit_lines_to_trace, remove_before_function_runtime, remove_after_function_runtime
from ph_basic_processing.parsers import indices_of_all_occurrences_of_character_in_string, minimize_indents, is_just_whitespace, is_linelog, concatenate_list_to_string, get_folder_delimiter, remove_leading_substring, remove_whitespace_only_lines_from_extremes_of_list


#
# CLASSES
#
class FuzzedUnitTestResult:
    """Container for those results of a fuzzed unit test that are relevant for causal testing."""

    def __init__(self, execution_path: str, failed: bool, test_method: TestMethod) -> None:
        """
        :param execution_path:  execution trace in string form.  SHOULD ALREADY BE POSTPROCESSED USING ADD_EXIT_LINES_TO_TRACE().  SHOULD ONLY INCLUDE THE LINES RUN DURING THE TEST'S RUNTIME
        :param failed:          boolean.  True if one or more assert calls in the test failed, else False.
        :param test_method:     TestMethod object for this test
        """
        # Handle errors
        # execution_path not a string
        if not isinstance(execution_path, str):
            raise TypeError("execution_path must be a string")
        # execution_path doesn't look like a post-processed execution trace
        if "\n" not in execution_path or "modulename: " not in execution_path or "---" not in execution_path or "|||" not in execution_path:
            raise ValueError("execution_path doesn't look like a post-processed execution trace")
        # failed not a bool
        if not isinstance(failed, bool):
            raise TypeError("failed must be a bool")
        # test_method not a TestMethod object
        if not isinstance(test_method, TestMethod):
            raise TypeError("test_method must be a TestMethod object")

        self.execution_path = execution_path
        self.failed = failed
        self.test_method = test_method


#
# HELPER FUNCTIONS
#
def show_report(failing_results_for_showing: list, passing_results_for_showing: list, original_execution_trace: str, original_test_method: TestMethod) -> None:
    """Given lists of results to show for both failing and passing tests, print a report in which the differences in
    literals are highlighted, and execution traces are cropped so that only the parts that differ remain.
    :param failing_results_for_showing:         list of failing FuzzedUnitTestResult objects to account for in the report
    :param passing_results_for_showing:         list of passing FuzzedUnitTestResult objects to account for in the report
    :param original_execution_trace:            string representing the execution trace of the original user-written test
    :param original_test_method:                TestMethod object for the original test
    """
    # Handle errors
    # failing_results_for_showing not a list
    if not isinstance(failing_results_for_showing, list):
        raise TypeError("failing_results_for_showing must be a list")
    # failing_results_for_showing contains non-FuzzedUnitTestResult element
    for element in failing_results_for_showing:
        if not isinstance(element, FuzzedUnitTestResult):
            raise TypeError("failing_results_for_showing contains non-FuzzedUnitTestResult element")
    # passing_results_for_showing not a list
    if not isinstance(passing_results_for_showing, list):
        raise TypeError("passing_results_for_showing must be a list")
    # passing_results_for_showing contains non-FuzzedUnitTestResult element
    for element in passing_results_for_showing:
        if not isinstance(element, FuzzedUnitTestResult):
            raise TypeError("passing_results_for_showing contains non-FuzzedUnitTestResult element")
    # no elements in both failing_results_for_showing and passing_results_for_showing
    if len(failing_results_for_showing) == 0 and len(passing_results_for_showing) == 0:
        raise ValueError("failing_results_for_showing and passing_results_for_showing must not both be empty")
    # original_execution_trace not a string
    if not isinstance(original_execution_trace, str):
        raise TypeError("original_execution_trace must be a string")

    results_for_showing = passing_results_for_showing + failing_results_for_showing

    for result in results_for_showing:
        # Print whether this result passed or failed, including a color code
        if result.failed:
            print(f"{Fore.RED}{'/'*24} FAILING TEST {'/'*24}{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}{'/'*24} PASSING TEST {'/'*24}{Style.RESET_ALL}")

        # Create a standardized version of the original and new test content so that they can be more meaningfully compared
        # Standardize text of original test by converting to ast and back again.  This also removes comments, which
        # muddle comparison
        original_content = concatenate_list_to_string(original_test_method.test_content, between="\n")
        original_content = to_source(parse(original_content)).split("\n")
        # Minimize indents from both
        original_content = minimize_indents(original_content)
        to_display_no_colors = minimize_indents(result.test_method.test_content)
        # Remove trailing blank lines from both
        for content in [original_content, to_display_no_colors]:
            for ll in range(len(content)-1, -1, -1):
                line = content[ll]
                if is_just_whitespace(line):
                    content.pop(ll)
                else:
                    break

        # Print the entirety of the test method, highlighting any literals that were changed (this needs to be by ast-node, rather than by text, because the fuzzed variants may format a literal differently from how the user did
        # TODO: For now we just highlight the parts of the test that are different, but in the future we should highlight the parts whose node values are different.
        print(f"{Fore.BLUE}{'~' * 16} Test Content Changes {'~' * 16}{Style.RESET_ALL}")
        content_diff = ndiff(original_content, to_display_no_colors)
        changes = [element for element in content_diff]
        content_changelog = changes.copy()  # For troubleshooting purposes, so that we can look at the initial state of changes
        # Build to_display_with_colors
        to_display_with_colors = []
        for line in to_display_no_colors:
            was_line_changed = False
            line_with_colors = line     # We'll add colors to line_with_colors if appropriate, and then append it to to_display_with_colors
            # Get rid of any removal lines; we ignore these
            while changes[0].startswith("-"):    # If a removal occurred, do nothing
                while len(changes) > 0 and changes[0][0] in ["-", "?"]:
                    changes.pop(0)
                was_line_changed = True
            # Remove all relevant elements from the front of changes and put them in change_buffer
            if changes[0].startswith(" "):  # If nothing was changed, do nothing
                changes.pop(0)
                change_buffer = []
            elif changes[0].startswith("+"):    # Put this changeline and the "?" line that follows (if any) in change_buffer
                change_buffer = [changes.pop(0)]
                if len(changes) > 0 and changes[0].startswith("?"):
                    change_buffer.append(changes.pop(0))
                was_line_changed = True
            else:
                raise RuntimeError("Don't know what to do with this starting symbol")
            # If there was a change, make the changed value in line_with_colors green
            if len(change_buffer) > 0:
                if len(change_buffer) == 1:     # If the whole line needs to be highlighted:
                    line_with_colors = Fore.GREEN + line_with_colors + Style.RESET_ALL
                elif len(change_buffer) == 2:   # If only a portion of the line needs to be highlighted:
                    indices_to_color = []
                    for index in indices_of_all_occurrences_of_character_in_string("+", change_buffer[1]):
                        indices_to_color.append(index - 2)  # Subtracting 2 compensates for extra indentation in changes
                    for index in indices_of_all_occurrences_of_character_in_string("^", change_buffer[1]):
                        indices_to_color.append(index - 2)  # Subtracting 2 compensates for extra indentation in changes
                    indices_to_color.sort(reverse=True)
                    for index_to_color in indices_to_color:
                        # Calculate prefix
                        if index_to_color == 0:
                            prefix = ""
                        else:
                            prefix = line_with_colors[:index_to_color]
                        # Calculate suffix
                        suffix = line_with_colors[index_to_color+1:]
                        # Color that character!
                        line_with_colors = prefix + Fore.GREEN + line_with_colors[index_to_color] + Style.RESET_ALL + suffix
                else:
                    raise RuntimeError(f"length of change_buffer unexpected: {len(change_buffer)}")
            # Also add a blue asterisk to any line where there was a change, or a removal before that line.  If not, add extra whitespace
            if was_line_changed:
                line_with_colors = Fore.BLUE + "* " + Style.RESET_ALL + line_with_colors
            else:
                line_with_colors = "  " + line_with_colors
            # Append line_with_colors to to_display_with_colors
            to_display_with_colors.append(line_with_colors)
        for line in to_display_with_colors:
            print(line)

        # Print the parts of the execution trace that are different, highlighting insertions green and removals red.
        # Omit linelogs that only differ in their pre-colon content.
        # Convert traces to newline-separated lists
        print(f"{Fore.BLUE}{'~' * 16} Execution Path Changes {'~' * 16}{Style.RESET_ALL}")
        original_execution_trace_list = original_execution_trace.split("\n")
        result_execution_path_list = result.execution_path.split("\n")
        # Remove all pre-colon content from linelog lines in both original_execution_trace_list and result_execution_path_list
        for this_trace in [original_execution_trace_list, result_execution_path_list]:
            for ll in range(len(this_trace)):
                line = this_trace[ll]
                if is_linelog(line):
                    index_colon = line.index(": ")
                    this_trace[ll] = line[index_colon+2:]
        # Get diff
        trace_diff = ndiff(original_execution_trace_list, result_execution_path_list)
        changes = [element for element in trace_diff]
        trace_changelog = changes.copy()  # For troubleshooting purposes, so that we can look at the initial state of changes
        # Create empty list which we'll build into the trace
        trace_with_colors = []
        # Build trace_with_colors
        for change in changes:
            if change.startswith(" "):
                trace_with_colors.append(change[1:])
            elif change.startswith("+"):
                trace_with_colors.append(Fore.GREEN + change[2:] + Style.RESET_ALL)
            elif change.startswith("-"):
                trace_with_colors.append(f"{Fore.RED} (Line removed: {change[2:]}){Style.RESET_ALL}")
            elif change.startswith("?"):
                pass    # We don't do anything for '?' lines because we treat all '+' and '-' lines like additions/removals of an entire line
        # Convert trace_with_colors back into a string, cropping any lines that aren't near a change, and print it
        trace_with_colors_as_string = ""
        most_recent_ll_added = -1
        for ll in range(len(trace_with_colors)):
            line = trace_with_colors[ll]
            # Get whether there's a colored line within 2 spaces away
            lines_nearby = ""
            try:
                lines_nearby += trace_with_colors[ll-2]
            except IndexError as err:
                pass
            try:
                lines_nearby += trace_with_colors[ll-1]
            except IndexError as err:
                pass
            try:
                lines_nearby += trace_with_colors[ll]
            except IndexError as err:
                pass
            try:
                lines_nearby += trace_with_colors[ll+1]
            except IndexError as err:
                pass
            try:
                lines_nearby += trace_with_colors[ll+2]
            except IndexError as err:
                pass
            colored_line_nearby = Style.RESET_ALL in lines_nearby
            # If distance is small enough, append to trace_with_colors_as_string, as well as a newline.  Add a ' (...)'
            # line if we skipped over anything.
            if colored_line_nearby:
                if most_recent_ll_added != ll - 1:
                    trace_with_colors_as_string += " (...)\n"
                trace_with_colors_as_string += line + "\n"
                most_recent_ll_added = ll
        # Add a final trailing ' (...)' if the last line added was not the last line of the trace
        if most_recent_ll_added != len(trace_with_colors) - 1:
            trace_with_colors_as_string += " (...)\n"
        print(trace_with_colors_as_string)


def distance_between_execution_traces(trace_new: str, trace_old: str) -> int:
    """Given two execution traces that have been post-processed by trace_exit_line_adders.add_exit_lines_to_trace(),
    return a value representing the distance between them
    :param trace_new:           execution trace post-processed by trace_exit_line_adders.add_exit_lines_to_trace()
    :param trace_old:           execution trace post-processed by trace_exit_line_adders.add_exit_lines_to_trace()
    :return:                    an integer representing the distance between the two traces
    """
    # Handle errors
    # trace_new not a string
    if not isinstance(trace_new, str):
        raise TypeError("trace_new must be a string")
    # trace_new doesn't look like a post-processed execution trace
    if "\n" not in trace_new or "modulename: " not in trace_new or "---" not in trace_new or "|||" not in trace_new:
        raise ValueError("trace_new doesn't look like a post-processed execution trace")
    # trace_old not a string
    if not isinstance(trace_old, str):
        raise TypeError("trace_old must be a string")
    # trace_old doesn't look like a post-processed execution trace
    if "\n" not in trace_old or "modulename: " not in trace_old or "---" not in trace_old or "|||" not in trace_old:
        raise ValueError("trace_old doesn't look like a post-processed execution trace")

    # Convert both traces to newline-separated lists of strings
    trace_new = trace_new.split("\n")
    trace_old = trace_old.split("\n")

    # Get diff generator between the traces
    diff = ndiff(trace_old, trace_new)  # Tracks changes from argument 0 to argument 1

    # Calculate distance using the generator.  For each removal or addition, add one distance, unless the
    # removal/addition is a function call, in which case 10 distance should be added instead.  Exit lines (which start
    # with " ||| exiting") do not contribute to distance
    distance = 0
    for i, s in enumerate(diff):
        if " ||| exiting modulename: " not in s:
            if s[0] == " ":     # If no change:
                continue
            elif s[0] == "-":   # If removal from trace_old to trace_new:
                if " --- modulename: " in s:
                    distance += 10
                else:
                    distance += 1
            elif s[0] == "+":   # If addition from trace_old to trace_new:
                if " --- modulename: " in s:
                    distance += 10
                else:
                    distance += 1

    # Return!
    return distance


def filter_for_minimally_different_passing_and_failing_tests(results: list, original_execution_trace: str) -> list:
    """Given a list of FuzzedUnitTestResult objects, return a list with just the 3 passing and 3 failing tests that have
    minimally different execution traces from the original test's execution trace.
    :param results:                     list of FuzzedUnitTestResult objects to be filtered
    :param original_execution_trace:    execution trace from original test, in string form
    :return:                            list of two sublists, where the first sublist is the FuzzedUnitTestResult objects for the 3 most similar failing tests, and the second sublist is the FuzzedUnitTestResult objects for the 3 most similar passing tests
    """
    # Handle errors
    # results not a list
    if not isinstance(results, list):
        raise TypeError("results must be a list")
    # results contains non-FuzzedUnitTestResult element
    for element in results:
        if not isinstance(element, FuzzedUnitTestResult):
            raise TypeError("results contains non-FuzzedUnitTestResult element")
    # results empty
    if len(results) == 0:
        raise ValueError("results must not be empty")
    # original_execution_trace not a string
    if not isinstance(original_execution_trace, str):
        raise TypeError("original_execution_trace must be a string")

    # Divide results into failing and passing
    failing_results = []
    passing_results = []
    for result in results:
        if result.failed:
            failing_results.append(result)
        else:
            passing_results.append(result)

    # Remove all tests from each category except for the 3 in that category with the least distant trace from the
    # original trace
    if len(failing_results) <= 3:
        filtered_failing = failing_results
    else:
        distances_failing = [distance_between_execution_traces(element.execution_path, original_execution_trace) for element in failing_results]  # Beware: The 3 smallest distances will later be set to +inf
        failing_least_distant_indices = []
        for ii in range(3):
            failing_least_distant_index = distances_failing.index(min(distances_failing))
            failing_least_distant_indices.append(failing_least_distant_index)
            distances_failing[failing_least_distant_index] = float("inf")
        filtered_failing = [failing_results[index] for index in failing_least_distant_indices]
    if len(passing_results) <= 3:
        filtered_passing = passing_results
    else:
        distances_passing = [distance_between_execution_traces(element.execution_path, original_execution_trace) for element in passing_results]    # Beware: The 3 smallest distances will later be set to +inf
        passing_least_distant_indices = []
        for ii in range(3):
            passing_least_distant_index = distances_passing.index(min(distances_passing))
            passing_least_distant_indices.append(passing_least_distant_index)
            distances_passing[passing_least_distant_index] = float("inf")
        filtered_passing = [passing_results[index] for index in passing_least_distant_indices]

    # Return!
    return [filtered_failing, filtered_passing]


def build_and_run_fuzzed_test_suite() -> None:
    """To be traced by the python trace module, called by get_variant_test_result().
    Build a test suite, run, and return test results by creating a .json file.
    """
    # Get inputs via globaling, to get around NameError: name 'foo' is not defined
    global test_case_as_string
    global class_as_string
    global test_filename_without_file_extension
    global line_number
    global importstring
    global test_filepath_temp_from_rootdir
    line_number_as_int = int(line_number)
    from ph_variable_sharing import shared_variables
    shared_variables.initialize()
    json_filename = shared_variables.json_filename
    ROOT_DIR = shared_variables.ROOT_DIR

    # Change to the working directory of the test file, and remember the previous directory for changing back
    if "/" in test_filepath_temp_from_rootdir or "\\" in test_filepath_temp_from_rootdir:
        folder_delimiter = get_folder_delimiter(test_filepath_temp_from_rootdir)
        old_working_directory = os.getcwd()
        os.chdir(ROOT_DIR)  # Step up to the top of the project so that we can avoid having to step upward to reach the file
        folder_change = concatenate_list_to_string(test_filepath_temp_from_rootdir.split(folder_delimiter)[:-1], between=folder_delimiter)  # Remove file from end, so that folder_change is a string of only directories
        if folder_change.startswith(folder_delimiter):
            folder_change = folder_change[1:]
        if folder_change.endswith(folder_delimiter):
            folder_change = folder_change[:-1]
        os.chdir(folder_change)

    # Build a test suite which contains only this test method
    test_class = import_by_string(importstring)
    this_delimiter = get_folder_delimiter(test_filepath_temp_from_rootdir)
    test_filepath_temp_from_rootdir_with_dots_no_file_extension = test_filepath_temp_from_rootdir.replace(this_delimiter, '.')
    if test_filepath_temp_from_rootdir_with_dots_no_file_extension.endswith(".py"):
        test_filepath_temp_from_rootdir_with_dots_no_file_extension = test_filepath_temp_from_rootdir_with_dots_no_file_extension[:-3]
    test_module = import_module(test_filepath_temp_from_rootdir_with_dots_no_file_extension)
    importlib.reload(test_module)
    suite = unittest.TestSuite()
    suite.addTest(test_class(test_case_as_string))

    # Run test and get results
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream)
    output_runner_result = runner.run(suite)    # Unit test result

    # Revert to whatever directory we were in before this was called
    if "/" in test_filepath_temp_from_rootdir or "\\" in test_filepath_temp_from_rootdir:
        os.chdir(old_working_directory)

    # If we encountered any errors (not just failures), warn the user
    if len(output_runner_result.errors) > 0:
        warning_text = "The following tests were aborted due to the following error(s) (not just failure(s)):"
        for this_error in output_runner_result.errors:
            warning_text = warning_text + "\n" + str(this_error)
        warn(warning_text)

    # In a perfect world, we'd want to return output_runner_result.  But because build_and_run_fuzzed_test_suite() gets
    # called by tracer.run() in get_unit_test_result(), and tracer.run() returns None due to the way trace.py is
    # designed, we instead have to write the important part(s) of the runner_result to a file.  I chose .json because it
    # can be used as a dictionary, and because Python has a built-in .json parser.

    # Warn the user if there's already a file with the name json_filename
    if os.path.exists(json_filename):
        response = input(json_filename + " already exists in the uppermost project directory. py-holmes needs to overwrite this file. Continue? (Y/n): ")
        if response in ["Y", "y"]:
            print("Deleting " + json_filename)
            os.remove(json_filename)
        else:
            print("Aborting")
            exit()
    # Create the .json file with all info we need
    with open(json_filename, "w", encoding="utf-8") as json_file:
        # Create a dictionary of all relevant results
        len_failures = len(output_runner_result.failures)
        dictionary = {
            "length_of_failures_list": len_failures,
        }
        # Convert this dictionary to json-formatted text, then write to the file.
        json_string = json.dumps(dictionary, indent=4)
        json_file.write(json_string)


def get_variant_test_result(test_method: TestMethod, dev_only_test_mode: bool) -> FuzzedUnitTestResult:
    """Return a FuzzedUnitTestResult object for the TestMethod object given.
    :param test_method:             a TestMethod object representing the test to be run
    :param dev_only_test_mode:      whether --dev_only_test_mode was set to True when py-holmes was called from the command line
    """
    # Handle errors
    # test_method not a TestMethod object
    if not isinstance(test_method, TestMethod):
        raise TypeError("test_method must be a TestMethod object")
    # dev_only_test_mode not a bool
    if not isinstance(dev_only_test_mode, bool):
        raise TypeError("dev_only_test_mode must be a bool")

    # Global some variables for later use by build_and_run_fuzzed_test_suite()
    global test_case_as_string
    global class_as_string
    global test_filename_without_file_extension
    global line_number
    global importstring
    global test_filepath_temp_from_rootdir
    from ph_variable_sharing import shared_variables
    shared_variables.initialize()
    json_filename = shared_variables.json_filename
    line_number = test_method.starting_test_lineno
    test_filepath_temp = test_method.test_filepath

    # Get test_filename_temp
    test_filename_temp = test_filepath_temp.split("/")[-1]
    test_filename_temp = test_filename_temp.split("\\")[-1]

    # Create test_filename_with_file_extension and test_filename_without_file_extension
    if len(test_filename_temp) <= 3 and ".py" not in test_filename_temp:    # Handle 3-character or shorter filenames missing .py
        test_filename_without_file_extension = test_filename_temp
        test_filename_with_file_extension = test_filename_temp + ".py"
    if test_filename_temp[-3:] == ".py":
        test_filename_without_file_extension = test_filename_temp[:-3]
        test_filename_with_file_extension = test_filename_temp
    else:
        test_filename_without_file_extension = test_filename_temp
        test_filename_with_file_extension = test_filename_temp + ".py"

    # Get line number as index
    line_number_as_index = test_method.starting_test_lineno_as_index  # For indexing starting at 0

    # Determine which test case contains line_number
    # Get the content of test_filepath_temp
    with open(test_filepath_temp, "r", encoding="utf-8") as test_module:
        test_module_content = test_module.readlines()
    # Find the test case we want
    test_case_as_string = test_method.test_name
    def_line_index = test_method.starting_test_lineno_as_index

    # Find the class containing this test method
    class_as_string = test_method.test_class

    # Build importstring
    folder_delimiter = get_folder_delimiter(test_filepath_temp)
    ROOT_DIR = shared_variables.ROOT_DIR
    test_filepath_temp_from_rootdir = remove_leading_substring(ROOT_DIR, test_filepath_temp)
    if test_filepath_temp_from_rootdir.startswith(folder_delimiter):
        test_filepath_temp_from_rootdir = test_filepath_temp_from_rootdir[1:]
    if folder_delimiter in test_filepath_temp:  # If the file isn't in the top-level directory:
        before_class = test_filepath_temp_from_rootdir.replace(folder_delimiter, ".")

        if before_class.endswith(".py"):
            before_class = before_class[:-3]
        importstring = f"from {before_class} import {class_as_string}"
    else:   # File IS in the top-level directory
        importstring = f"from {test_filename_without_file_extension} import {class_as_string}"

    # Run test and get results, simultaneously tracing execution.
    # Getting tracer results involves redirecting stdout to a buffer and capturing it later as a variable.
    # Getting unittest runner results requires reading the important results from a json
    # that build_and_run_fuzzed_test_suite() writes
    tracer = trace.Trace(count=0, trace=1, countfuncs=0, countcallers=0, ignoremods=(), ignoredirs=(), infile=None, outfile=None, timing=False)
    trace_buffer = io.StringIO()
    try:
        with redirect_stdout(trace_buffer):   # To prevent the execution trace from getting printed to the screen
            tracer.run("build_and_run_fuzzed_test_suite()")   # Unit test result.  Running this line leads to warning about using PyDev debugger with sys.settrace()
        json_file = open(json_filename, "r", encoding="utf-8")
        json_string = json_file.read()
        runner_result = json.loads(json_string)
    finally:
        # Close the json file if we ever opened it
        if "json_file" in locals():
            json_file.close()
        # Delete the json file; we have no more use for it
        os.remove(json_filename)

    # Get whether test failed (ie whether any asserts failed in this test-case method)
    test_failed = (runner_result["length_of_failures_list"] != 0)

    # Get the execution trace, regardless of whether the test passed or failed
    tracer_result = trace_buffer.getvalue()
    tracer_result = remove_before_function_runtime(tracer_result, test_method.test_name, test_filename_without_file_extension)
    tracer_result, _, _ = add_exit_lines_to_trace(tracer_result)  # Add exit lines to tracer_result for every time we exit a function or class, and do some other touch-ups as well
    # Remove all but the user's runtime from the execution trace
    tracer_result = remove_after_function_runtime(tracer_result, test_method.test_name, test_filename_without_file_extension)

    # Create a FuzzedUnitTestResult object with the information that we need for causal testing
    output = FuzzedUnitTestResult(execution_path=tracer_result, failed=test_failed, test_method=test_method)

    # If in dev-only testing mode, print the attributes of this object
    if dev_only_test_mode:
        print("Ran a test variant; here's the result")
        print(f"TestMethod: {output.test_method}")
        print(f"Failed: {output.failed}")
        print(f"Execution path:\n{output.execution_path}")

    # Return!
    return output


def run_fuzzed_tests_until_time_limit(fuzzed_to_run: list, dev_only_test_mode: bool, time_limit_seconds=60) -> list:
    """Until time_limit_seconds elapses, start tests in fuzzed_to_run, in the order they're given.  Return a list of
    FuzzedUnitTestResults for each test that completed.
    :param fuzzed_to_run:                list of TestMethod objects for tests to run
    :param dev_only_test_mode:           whether --dev_only_test_mode was set to True when py-holmes was called from the command line
    :param time_limit_seconds:           maximum amount of time to spend running test variants, in units of seconds
    :return:                             list of FuzzedUnitTestResult objects, where each object corresponds to the object in fuzzed_to_run with the same index.
    """
    # Handle errors
    # fuzzed_to_run not a list
    if not isinstance(fuzzed_to_run, list):
        raise TypeError("fuzzed_to_run must be a list")
    # fuzzed_to_run contains non-TestMethod element
    for element in fuzzed_to_run:
        if not isinstance(element, TestMethod):
            raise TypeError("fuzzed_to_run contains non-TestMethod element")
    # fuzzed_to_run has length 0
    if len(fuzzed_to_run) == 0:
        raise ValueError("fuzzed_from_original and fuzzed_from_found are both empty.  No tests to run.")
    # dev_only_test_mode not a bool
    if not isinstance(dev_only_test_mode, bool):
        raise TypeError("dev_only_test_mode must be a bool")
    # time_limit_seconds not an int
    if not isinstance(time_limit_seconds, int):
        raise TypeError("time_limit_seconds must be an int")
    # time_limit_seconds less than 5
    if time_limit_seconds < 5:
        raise ValueError("time_limit_seconds must be at least 5")

    output = []
    to_attempt_index = 0
    timeout_duration = timedelta(seconds=time_limit_seconds)

    # Get starting time
    start_time = datetime.now()

    # Until we're overtime or run out of tests, keep running tests and adding them to output
    while datetime.now() - start_time < timeout_duration and to_attempt_index < len(fuzzed_to_run):
        output.append(get_variant_test_result(fuzzed_to_run[to_attempt_index], dev_only_test_mode))
        to_attempt_index += 1

    # Return!
    return output


def run_variants_and_show_results(original_test_result: OriginalUnitTestResult, original_test_method: TestMethod, fuzzed_from_original: list, fuzzed_from_found: list, dev_only_test_mode: bool, time_limit_seconds=60) -> None:
    """Run variants of the original and found tests until time_limit_seconds elapses, then filter for the 3 most similar
    passing and failing tests and show them.  Obtains time_limit_seconds from shared_variables.py; after this much time
    has elapsed, no new tests will be initiated.
    :param original_test_result:                OriginalUnitTestResult object for the original user-written test
    :param original_test_method:                TestMethod object for the original test
    :param fuzzed_from_original:                list of TestMethod objects for tests produced by fuzzing the original test
    :param fuzzed_from_found:                   list of TestMethod objects for found user-written tests that are call-similar to the original user-written test
    :param dev_only_test_mode:                  whether --dev_only_test_mode was set to True when py-holmes was called from the command line
    """
    # Handle errors
    # original_test_result not an OriginalUnitTestResult object
    if not isinstance(original_test_result, OriginalUnitTestResult):
        raise TypeError("original_test_result must be an OriginalUnitTestResult object")
    # original_test_method not a TestMethod object
    if not isinstance(original_test_method, TestMethod):
        raise TypeError("original_test_method must be a TestMethod object")
    # fuzzed_from_original not a list
    if not isinstance(fuzzed_from_original, list):
        raise TypeError("fuzzed_from_original must be a list")
    # fuzzed_from_original contains non-TestMethod element
    for element in fuzzed_from_original:
        if not isinstance(element, TestMethod):
            raise TypeError("fuzzed_from_original contains non-TestMethod element")
    # fuzzed_from_found not a list
    if not isinstance(fuzzed_from_found, list):
        raise TypeError("fuzzed_from_found must be a list")
    # fuzzed_from_found contains non-TestMethod element
    for element in fuzzed_from_found:
        if not isinstance(element, TestMethod):
            raise TypeError("fuzzed_from_found contains non-TestMethod element")
    # both fuzzed lists have length 0
    if len(fuzzed_from_original) == 0 and len(fuzzed_from_found) == 0:
        raise ValueError("fuzzed_from_original and fuzzed_from_found are both empty.  No tests to run.")
    # dev_only_test_mode not a bool
    if not isinstance(dev_only_test_mode, bool):
        raise TypeError("dev_only_test_mode must be a bool")

    # Get the time limit
    from ph_variable_sharing import shared_variables
    shared_variables.initialize()
    time_limit_seconds = shared_variables.variant_testing_time_limit_seconds

    # Create a list of fuzzed tests to run and remove any tests with duplicate body content from it
    fuzzed_combined = fuzzed_from_original + fuzzed_from_found
    fuzzed_to_run = []
    test_bodies_seen = []   # List of line-separated sublists, each sublist representing a test
    for this_fuzzed in fuzzed_combined:
        this_content_no_whitespace = remove_whitespace_only_lines_from_extremes_of_list(this_fuzzed.test_content[1:])
        if this_content_no_whitespace not in test_bodies_seen:
            test_bodies_seen.append(this_content_no_whitespace)
            fuzzed_to_run.append(this_fuzzed)

    # Run as many fuzzed tests as possible until we reach a time limit.  Prioritize running variants of the original
    # test, rather than running variants of the found test
    test_results = run_fuzzed_tests_until_time_limit(fuzzed_to_run, dev_only_test_mode, time_limit_seconds)

    # Filter for up to 3 passing and 3 failing tests that have minimally different execution traces
    failing_results_to_show, passing_results_to_show = filter_for_minimally_different_passing_and_failing_tests(test_results, original_test_result.execution_path)

    # Show a report in which the differences in literals are highlighted, and execution traces are cropped so that only
    # the parts that differ remain
    show_report(failing_results_to_show, passing_results_to_show, original_test_result.execution_path, original_test_method)
