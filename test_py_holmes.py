"""Unit tests and integration tests for py_holmes.py.  Even the unit tests still use the unittest module for convenience and consistency.
WARNING: TO DO A COMPLETE TEST OF PY-HOLMES' CAPABILITIES, ALSO RUN mnist_demo.ipynb AND ENSURE RESULTS LOOK REASONABLE.
"""
import unittest
import os
import ast
import re
import torch
from math import pi, atan2, ceil
from datetime import datetime
from ph_variable_sharing import shared_variables
from ph_causal_testing import unit_test_finders, oracle_tools, unit_test_cutters, unit_test_fuzzers, class_for_test_method, variant_test_runners
from ph_basic_processing.parsers import first_line_in_file_beginning_with_ignoring_whitespace, minimize_indents, concatenate_list_to_string, levenshtein_distance, is_just_whitespace, remove_duplicates_from_list, remove_whitespace_only_lines_from_extremes_of_list
from ph_basic_processing.cleanup import cleanup
shared_variables.initialize()
ROOT_DIR = shared_variables.ROOT_DIR
from colorama import Fore, Style
#
# USER-SET PARAMETERS
#
log_file_name = "log_from_most_recent_run.log"  # The log file created when py_holmes runs
#
# CLASSES
#
class TestOriginalUnitTestExtraction(unittest.TestCase):
    """Tests of py_holmes's ability to extract accurate OriginalUnitTestResult objects from the user's original test.
    This is really a class of integration tests, not of unit tests, but the unittest module is used for convenience.
    """

    def test_call_with_no_args(self):
        """Run py_holmes without giving it any command line arguments."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py --dev_only_test_mode")
        desired = "py_holmes.py: error: the following arguments are required: --file/-f"
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_call_with_nonexistent_file(self):
        """Run py_holmes with the file argument being a file that does not exist."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f my_nonexistent_file.py --dev_only_test_mode")
        desired = "FileNotFoundError: [Errno 2] No such file or directory: 'my_nonexistent_file.py'"
        result = contents_of_log_file()
        self.assertIn(desired, result)


    def test_call_with_non_unittest_file(self):
        """Run py_holmes with its file argument pointing to an existent file that is not a unittest."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f circle_method.py --dev_only_test_mode")
        desired = "The file requested by the user contains no classes for unit testing (ie classes which are subclasses of the unittest class)"
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_call_with_non_numeric_lines(self):
        """Run py_holmes with its lines argument containing a string that does not correspond to a number."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method.py -l foo --dev_only_test_mode")
        desired = "ValueError: invalid literal for int() with base 10: "
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_call_with_float_lines(self):
        """Run py_holmes with its lines argument containing a float."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method.py -l 3.14159 --dev_only_test_mode")
        desired = "ValueError: invalid literal for int() with base 10: "
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_call_with_non_numeric_spaces_per_tab(self):
        """Run py_holmes with its tatosp argument containing a string that does not correspond to a number."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method.py -t foo --dev_only_test_mode")
        desired = "error: argument --tatosp/-t: invalid int value: "
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_call_with_float_spaces_per_tab(self):
        """Run py_holmes with its tatosp argument containing a float."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method.py -t 3.14159 --dev_only_test_mode")
        desired = "error: argument --tatosp/-t: invalid int value: "
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_call_with_zero_spaces_per_tab(self):
        """Run py_holmes with its tatosp argument set to 0."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method.py -t 0 --dev_only_test_mode")
        desired = "--tatosp (aka -t) must be positive; cannot have tabs equivalent to a non-positive number of spaces"
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_empty_unittest_file(self):
        """Run py_holmes on an empty unit test file."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_empty_unittest_file.py --dev_only_test_mode")
        desired = "ValueError: The file requested by the user contains no classes for unit testing (ie classes which are subclasses of the unittest class)"
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_unittest_file_that_doesnt_import_unittest(self):
        """Run py_holmes on a unittest file that doesn't import Python's unittest module."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method_that_fails_to_import_unittest.py --dev_only_test_mode")
        desired = "NameError: name 'unittest' is not defined"
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_empty_method(self):
        """Test a method with no content."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method_with_an_empty_test_method.py -l 30 --dev_only_test_mode")
        desired = "Test method test_empty contains no code"
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_method_with_all_passes(self):
        """Test a method where all asserts pass."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method.py -l 12 --dev_only_test_mode")
        desired_0 = "No failed tests encountered (except for possible failures that aren't the user's fault -- each showed up in this console as a warning, if any)."
        desired_1 = "If you would like to run causal testing anyway, rerun with '-p' to enable causal testing on passing tests"
        result = contents_of_log_file()
        self.assertIn(desired_0, result)
        self.assertIn(desired_1, result)

    def test_method_with_failure(self):
        """Test a method that contains a failed assert call."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method.py -l 20 --dev_only_test_mode")
        desired = "BEGIN CAUSAL TESTING RESULTS FOR <"
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_unittest_file_with_bad_import(self):
        """Test a method from a unit test file that requires an import that does not exist."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method_with_bad_import.py -l 11 --dev_only_test_mode")
        desired = "UserWarning: The following tests were interrupted due to the following error(s) (not just failure(s)):"
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_unittest_with_no_assert_that_crashes(self):
        """Test a method from a unit test file that contains no asserts and crashes due to being poorly written."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method_with_tests_without_asserts.py -l 30 --dev_only_test_mode")
        desired = "UserWarning: The following tests were interrupted due to the following error(s) (not just failure(s)):"
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_unittest_with_no_assert_that_does_not_crash(self):
        """Test a method from a unit test file that contains no asserts and does not produce an exception."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method_with_tests_without_asserts.py -l 40 --dev_only_test_mode")
        desired = "UserWarning: No assert calls in function test_without_asserts_no_exception"
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_unittest_of_function_that_crashes(self):
        """Run a test method that runs an assert on a user-written function which fails before the assert call can
        resolve."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method_that_calls_crashing_method.py -l 31 --dev_only_test_mode")
        desired = "UserWarning: The following tests were interrupted due to the following error(s) (not just failure(s)):"
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_single_working_test_method_that_fails(self):
        """Run a test method that fails and check the OriginalUnitTestResult."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method.py -l 20 --dev_only_test_mode")
        desired0 = "INPUT ARGS TREE:\n<_ast.Module object at 0x"
        desired1 = "EXECUTION PATH:\n --- modulename: "
        desired2 = "FAILED:\nTrue"
        desired3 = "TRACEBACK:\nTraceback (most recent call last):"
        result = contents_of_log_file()
        self.assertIn(desired0, result)
        self.assertIn(desired1, result)
        self.assertIn(desired2, result)
        self.assertIn(desired3, result)

    def test_all_test_methods_in_a_file(self):
        """Run all 3 test methods in a class, where one passes and two fails, and check that run_causal_testing is
        executed twice.
        """
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method.py -l all --dev_only_test_mode")
        result = contents_of_log_file()
        num_ast_prints = result.count("INPUT ARGS TREE:\n<_ast.Module object at 0x")
        num_execution_traces = result.count("EXECUTION PATH:\n --- modulename: ")
        num_fails = result.count("FAILED:\nTrue")
        num_tracebacks = result.count("TRACEBACK:\nTraceback (most recent call last):")
        self.assertAlmostEqual(2, num_ast_prints)
        self.assertAlmostEqual(2, num_execution_traces)
        self.assertAlmostEqual(2, num_fails)
        self.assertAlmostEqual(2, num_tracebacks)

    def test_file_with_2_spaces_for_each_tab(self):
        """Run a test method in a file with a mix of tabs and spaces, for which each tab corresponds to 2 spaces."""
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method_with_tatosp_2.py -l all -t 2 --dev_only_test_mode")
        result = contents_of_log_file()
        num_ast_prints = result.count("INPUT ARGS TREE:\n<_ast.Module object at 0x")
        num_execution_traces = result.count("EXECUTION PATH:\n --- modulename: ")
        num_fails = result.count("FAILED:\nTrue")
        num_tracebacks = result.count("TRACEBACK:\nTraceback (most recent call last):")
        self.assertAlmostEqual(2, num_ast_prints)
        self.assertAlmostEqual(2, num_execution_traces)
        self.assertAlmostEqual(2, num_fails)
        self.assertAlmostEqual(2, num_tracebacks)

    def test_optional_causal_testing_on_pass_for_specific_line(self):
        """Call py-holmes specifying a single passing line (ie single passing test method),
        with -p flag enabled.  Causal testing should still be initiated.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method.py -l 12 --passing_tests_include --dev_only_test_mode")
        desired = " passed; nonetheless running causal testing by user request."
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_optional_causal_testing_on_pass_for_all_lines(self):
        """Call py-holmes specifying all lines (ie all test methods).  For test methods that pass,
        causal testing should still be performed.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method.py -l all --passing_tests_include --dev_only_test_mode")
        desired = " passed; nonetheless running causal testing by user request."
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_warning_optional_causal_testing_on_pass_for_specific_line(self):
        """With -p flag enabled, call py-holmes specifying a single test method whose execution involves a failure that is not the user's
        fault.
        Causal testing should still be initiated.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Add circle_method_to_be_holmesignored_in_testing.py to .holmesignore
        with open(".holmesignore", "w", encoding="utf-8") as file:
            file.write(os.path.abspath("circle_method_to_be_holmesignored_in_testing.py") + "\n")

        # Run
        os.system("python py_holmes.py -f test_circle_method_to_be_holmesignored_in_testing.py -l 20 --passing_tests_include --dev_only_test_mode")
        desired = "Nonetheless running causal testing by user request."
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_warning_optional_causal_testing_on_pass_for_all_lines(self):
        """With -p flag enabled, call py-holmes specifying all test methods.
        Of these test methods, two methods' executions involve a failure that is not the user's fault.
        Causal testing should still be initiated twice.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Add circle_method_to_be_holmesignored_in_testing.py to .holmesignore
        with open(".holmesignore", "w", encoding="utf-8") as file:
            file.write(os.path.abspath("circle_method_to_be_holmesignored_in_testing.py") + "\n")

        # Run
        os.system("python py_holmes.py -f test_circle_method_to_be_holmesignored_in_testing.py -l all --passing_tests_include --dev_only_test_mode")
        desired = "Nonetheless running causal testing by user request."
        result = contents_of_log_file()
        desired_count_in_result = result.count(desired)
        self.assertEqual(2, desired_count_in_result)


class TestExitLinesAndHolmesignoreEXTERNAL(unittest.TestCase):
    """WARNING: THIS CLASS OF TESTS SHOULD BE PERFORMED WITH A PYTHON INTERPRETER THAT IS NOT IN A SUBDIRECTORY OF THE
    PROJECT DIRECTORY!  Otherwise, test_exit_line_for_file_in_executable_folder() is moot.
    Test the validity of exit lines added to execution traces.
    """

    def test_exit_line_for_file_in_executable_folder(self):
        """Test that exit lines are added for files in the executable folder, even if that folder isn't a subdirectory
        of the project folder.
        Also tests for proper handling of imports of third-party packages
        Takes longer than most other tests to run; execution trace is about 150,000 lines long
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create test_circle_method_with_numpy.py by using test_circle_method_with_numpy.txt as a template
        with open("test_circle_method_with_numpy.txt", "r") as file:
            content = file.read()
        with open("test_circle_method_with_numpy.py", "w") as file:
            file.write(content)

        os.system("python py_holmes.py -f test_circle_method_with_numpy.py -l 35 --dev_only_test_mode")

        # Delete test-circle_method_with_numpy.py
        os.remove("test_circle_method_with_numpy.py")

        # Check result
        desired = "fromnumeric.py(3203):     return (a,)"   # This line appears in the executable folder (specifically within numpy), and does not appear in any file in the py-holmes folder or the default Python install directory
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_exit_line_for_file_in_default_install_folder(self):
        """Test that exit lines are added for files in the default Python install folder for the operating system, even
        if that folder isn't a subdirectory of the project folder."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method.py -l 20 --dev_only_test_mode")
        desired = "case.py(814):"
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_stacklike(self):
        """Test that every function entered is later exited in a stacklike way."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method.py -l 20 --dev_only_test_mode")
        result = contents_of_log_file()

        # Filter for just the execution lines
        execution_lines = result.split("\n")
        index_execution_path_start = execution_lines.index("EXECUTION PATH:")
        index_execution_path_end = execution_lines.index("INPUT ARGS TREE:")
        execution_lines = execution_lines[index_execution_path_start+1:index_execution_path_end]
        # Check for stacklike order.  If there isn't, raise an error.
        function_stack = []
        for line in execution_lines:
            if " --- modulename: " in line and not ("<" in line and ">" in line and "funcname: <" not in line):
                function_being_entered = line[line.index(", funcname: ") + 12:]
                function_stack.append(function_being_entered)
                print(function_stack)   # For easy troubleshooting
            elif " ||| exiting modulename: " in line and not ("<" in line and ">" in line and "funcname: <" not in line):
                if not ("ALL REMAINING CONTAINERS" in line and "ALL REMAINING FILES" in line):
                    function_being_exited = line[line.index(", funcname: ") + 12:]
                    pop_result = function_stack.pop()
                    print(function_stack)   # For easy troubleshooting
                    self.assertEqual(function_being_exited, pop_result)

    def test_parse_holmesignore(self):
        """WARNING: OVERWRITES .HOLMESIGNORE
        Run parse_holmesignore() on a tricky .holmesignore file (including comments, blank lines, and some entries in
        subfolders) and ensure it worked.
        """
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.

        # Set up .holmesignore
        with open(".holmesignore", "w", encoding="utf-8") as file:
            file.write("# Tricky file written by test_parse_holmesignore()\n")
            file.write("\n")
            file.write("\n")
            file.write("\r\n")
            file.write(os.path.join(ROOT_DIR, "py_holmes.py") + "\r")
            file.write("\n\r")
            file.write(os.path.abspath(os.path.join(os.path.abspath("py-holmes-external-interpreter-for-testing"), "venv/Scripts/activate_this.py")) + "\n")
            file.write("#" + os.path.abspath(os.path.join(os.path.abspath("py-holmes-external-interpreter-for-testing"), "venv/Lib/site-packages/_virtualenv.py")) + "\r")
            file.write("\n \r")

        # Parse and test results
        from ph_basic_processing.scrapers_for_holmesignore_and_holmessearchextend import parse_holmesignore
        desired = [os.path.join(ROOT_DIR, "py_holmes.py"), os.path.abspath(os.path.join(os.path.abspath("py-holmes-external-interpreter-for-testing"), "venv/Scripts/activate_this.py"))]
        result = parse_holmesignore()
        for entry in desired:
            self.assertIn(entry, result)


    def test_matches_an_ignore_pattern(self):
        """Check if a few different paths (including some in subfolders) match any of a list of ignore patterns.
        """
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.

        # Set up ignore pattern
        patterns_to_ignore = []
        patterns_to_ignore.append(os.path.abspath(os.path.join(ROOT_DIR, "budget_calculations/*")))
        patterns_to_ignore.append(os.path.abspath(os.path.join(ROOT_DIR, "?racking_tennis_ball_attempt_*/main.py")))
        patterns_to_ignore.append(os.path.join(ROOT_DIR, "Pictures"))

        # Set up filenames and whether they match patterns in .holmesignore
        oracle = {
            os.path.abspath(os.path.join(ROOT_DIR, "budget_calculations/total_spending_complicated.py")): True,
            os.path.abspath(os.path.join(ROOT_DIR, "budget_calculations/venv/Scripts")): True,
            os.path.abspath(os.path.join(ROOT_DIR, "badger_conniptions/venv/Scripts")): False,
            os.path.abspath(os.path.join(ROOT_DIR, "tracking_tennis_ball_attempt_0/main.py")): True,
            os.path.abspath(os.path.join(ROOT_DIR, "fracking_tennis_ball_attempt_/main.py")): True,
            os.path.abspath(os.path.join(ROOT_DIR, "racking_tennis_ball_attempt_2/main.py")): False,
            os.path.abspath(os.path.join(ROOT_DIR, "Pictures")): True,
            os.path.abspath(os.path.join(ROOT_DIR, "Pictures/my_image.png")): False,
            os.path.abspath(os.environ["USERPROFILE"]): False
        }

        # Check results
        from ph_basic_processing.parsers import matches_an_ignore_pattern
        for filename in oracle:
            desired = oracle[filename]
            result = matches_an_ignore_pattern(filename, optional_ignore_patterns=patterns_to_ignore)
            self.assertEqual(desired, result)


class TestHolmessearchextendEXTERNAL(unittest.TestCase):
    """WARNING: THIS CLASS OF TESTS SHOULD BE PERFORMED WITH A PYTHON INTERPRETER THAT IS NOT IN A SUBDIRECTORY OF THE
    PROJECT DIRECTORY!  Otherwise, test_search_in_holmessearchextend() is moot.
    Test support of the .holmessearchextend file as a way of adding new files to be searched.
    """

    def test_parse_holmessearchextend(self):
        """WARNING: OVERWRITES .HOLMESSEARCHEXTEND
        Run parse_holmessearchextend() on a tricky .holmessearchextend file (including comments, blank lines, and some
        entries in subfolders) and ensure it worked.
        """
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.

        # Set up .holmesignore
        with open(".holmessearchextend", "w", encoding="utf-8") as file:
            file.write("# Tricky file written by test_parse_holmessearchextend()\n")
            file.write("\n")
            file.write("\n")
            file.write("\r\n")
            file.write(os.path.join(ROOT_DIR, "py_holmes.py") + "\r")
            file.write("\n\r")
            file.write(os.path.abspath(os.path.join(os.path.abspath("py-holmes-external-interpreter-for-testing"), "venv/Scripts/activate_this.py")) + "\n")
            file.write("#" + os.path.abspath(os.path.join(os.path.abspath("py-holmes-external-interpreter-for-testing"), "venv/Lib/site-packages/_virtualenv.py")) + "\r")
            file.write("\n \r")

        # Parse and test results
        from ph_basic_processing.scrapers_for_holmesignore_and_holmessearchextend import parse_holmessearchextend
        desired = [os.path.join(ROOT_DIR, "py_holmes.py"), os.path.abspath(os.path.join(os.path.abspath("py-holmes-external-interpreter-for-testing"), "venv/Scripts/activate_this.py"))]
        result = parse_holmessearchextend()
        self.assertEqual(desired, result)

    def test_search_in_holmessearchextend(self):
        """WARNING: OVERWRITES .HOLMESSEARCHEXTEND
        Test that .holmessearchextend is used to search for files not found in the project directory, interpreter
        directory, or default Python install location for the OS.
        """
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.

        # Set up .holmesignore
        with open(".holmessearchextend", "w", encoding="utf-8") as file:
            file.write(os.path.abspath(os.path.dirname(ROOT_DIR) + os.path.normpath("/") + os.path.normpath("py-holmes-external-interpreter-for-testing/") + os.path.normpath("/") + "*\n"))

        # Check results
        os.system("python py_holmes.py -f test_circle_method_with_call_to_file_outside_project_folder.py -l 32 --dev_only_test_mode")
        desired = 'my_file.py(2):     print("Hi!")'
        result = contents_of_log_file()
        self.assertIn(desired, result)


class TestOnlyRespondingToFailuresInUserCode(unittest.TestCase):
    """Tests py_holmes's ability to ignore failures in non-user-written code, and ability to always catch failures in
    user's code.
    """

    def test_failure_in_test_method(self):
        """A test produces a failure (not an error) in the unittest file itself. Should perform causal testing."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 32 --dev_only_test_mode")
        desired = ("BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_in_function_called_by_test_method(self):
        """A test calls a method which produces a failure (not an error). Should perform causal testing."""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system("python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 22 --dev_only_test_mode")
        desired = ("BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_error_in_py_holmes(self):
        """Create a faulty variant of py_holmes.py called py_holmes_built_to_fail.py, then use it on a passing test
        method.  Should not run causal testing.  Then delete py_holmes_built_to_fail.py."""
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Write py_holmes_built_to_fail.py
        # Get the content of the normal py_holmes.py
        with open("py_holmes.py", "r", encoding="utf-8") as file:
            py_holmes_content = file.readlines()
        # Insert a faulty line right after the comment "# Strip leading tabs and spaces from all content"
        insertion_index = 1 + py_holmes_content.index("    # Strip leading tabs and spaces from all content\n")
        py_holmes_content.insert(insertion_index, "    raise RuntimeError('This is an intentional failure inserted by a test method')\n")
        # Write this to a new file
        with open("py_holmes_built_to_fail.py", "w", encoding="utf-8") as file:
            file.writelines(py_holmes_content)

        # Attempt to use py_holmes_built_to_fail.py; it fails
        os.system("python py_holmes_built_to_fail.py -f test_circle_method.py -l 12 --dev_only_test_mode")

        # Delete py_holmes_built_to_fail.py
        if os.path.exists("py_holmes_built_to_fail.py"):
            os.remove("py_holmes_built_to_fail.py")

        # Check that we didn't perform causal testing
        desired_to_be_absent = ("BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertNotIn(desired_to_be_absent, result)

    def test_failure_in_holmesignore(self):
        """A test calls a method which produces a failure in a file in .holmesignore.
        Should not run causal testing.
        """
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.

        # Add circle_method_to_be_holmesignored_in_testing.py to .holmesignore
        with open(".holmesignore", "w", encoding="utf-8") as file:
            file.write(os.path.abspath("circle_method_to_be_holmesignored_in_testing.py") + "\n")

        # Run
        os.system("python py_holmes.py -f test_circle_method_to_be_holmesignored_in_testing.py -l 20 --dev_only_test_mode")
        desired = " failed but not due to a fault in the user's test or any of its call descendants."
        desired_to_be_absent = "BEGIN CAUSAL TESTING RESULTS FOR <"  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)
        self.assertNotIn(desired_to_be_absent, result)

    # Here begins a battery of failures of various kinds of assert when it *is* the user's fault.
    # Tests of Class 2 asserts come first, to make running this class more convenient by front-loading human assistance.
    def test_failure_on_assertIn(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 60 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertNotIn(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 63 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertRegexpMatches(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 98 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertNotRegexpMatches(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 101 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertEqual(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 36 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertNotEqual(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 39 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertTrue(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 42 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertFalse(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 45 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertIs(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 48 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertIsNot(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 51 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertIsNone(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 54 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertIsNotNone(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 57 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertIsInstance(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 66 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertNotIsInstance(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 69 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertRaises(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 72 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertRaisesRegexp(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 76 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertAlmostEqual(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 80 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertNotAlmostEqual(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 83 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertGreater(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 86 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertGreaterEqual(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 89 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertLess(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 92 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertLessEqual(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 95 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertCountEqual(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 104 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertWarns(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 107 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertWarnsRegex(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 111 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertLogs(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 115 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertMultiLineEqual(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 119 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertSequenceEqual(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 130 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertListEqual(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 133 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertTupleEqual(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 136 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertSetEqual(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 139 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)

    def test_failure_on_assertDictEqual(self):
        """User's fault; should run causal testing"""
        wipe_old_files()    # Remove key files that, if left over, may interfere with the flow of a test.
        os.system(
            "python py_holmes.py -f test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py -l 144 --dev_only_test_mode")
        desired = (
            "BEGIN CAUSAL TESTING RESULTS FOR <")  # Proof that causal testing is triggered
        result = contents_of_log_file()
        self.assertIn(desired, result)


class TestUnitTestFinding(unittest.TestCase):
    """Tests py-holmes's ability to search the user's project folder for unit tests"""

    def test_find_all_test_methods_in_file(self):
        """Try extracting test methods from test_py_holmes.py"""
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.
        result = unit_test_finders.find_all_test_methods_in_file(os.path.join(ROOT_DIR, "test_py_holmes.py"), post_as_user_test_method_objects=True)

        # Check that a decent number of tests are present
        result_test_names = [element.test_name for element in result]
        self.assertLessEqual(50, len(result_test_names))  # Ensure we got a lot of tests
        desired = ["test_call_with_no_args", "test_call_with_non_numeric_lines", "test_stacklike"]
        for this_desired in desired:
            self.assertIn(this_desired, result_test_names)

        # Grab the TestMethod object for test_call_with_no_args and...
        obj = None
        for element in result:
            if element.test_name == "test_parse_holmessearchextend":
                obj = element
                break

        # ...check test_filepath
        self.assertEqual(os.path.join(ROOT_DIR, "test_py_holmes.py"), obj.test_filepath)

        # ...check test_class
        self.assertEqual("TestHolmessearchextendEXTERNAL", obj.test_class)

        # ...check class_content
        lines_to_check = [
            'class TestHolmessearchextendEXTERNAL(unittest.TestCase):',
            '    PROJECT DIRECTORY!  Otherwise, test_search_in_holmessearchextend() is moot.',
            '    def test_parse_holmessearchextend(self):',
            '        # Set up .holmesignore',
            '        from ph_basic_processing.scrapers_for_holmesignore_and_holmessearchextend import parse_holmessearchextend',
            '        desired = [os.path.join(ROOT_DIR, "py_holmes.py"), os.path.abspath(os.path.join(os.path.abspath("py-holmes-external-interpreter-for-testing"), "venv/Scripts/activate_this.py"))]',
            '',
            '        self.assertEqual(desired, result)',
            '    def test_search_in_holmessearchextend(self):'
        ]
        for line_to_check in lines_to_check:
            self.assertIn(line_to_check, obj.class_content)

        # ...check test_content
        lines_to_check = [
            '    def test_parse_holmessearchextend(self):',
            '        # Set up .holmesignore',
            '        from ph_basic_processing.scrapers_for_holmesignore_and_holmessearchextend import parse_holmessearchextend',
            '        desired = [os.path.join(ROOT_DIR, "py_holmes.py"), os.path.abspath(os.path.join(os.path.abspath("py-holmes-external-interpreter-for-testing"), "venv/Scripts/activate_this.py"))]',
            '',
            '        self.assertEqual(desired, result)'
        ]
        for line_to_check in lines_to_check:
            self.assertIn(line_to_check, obj.test_content)

        # ...check files_methods_and_classes_testing
        desired = {"ph_basic_processing.scrapers_for_holmesignore_and_holmessearchextend.parse_holmessearchextend"}
        self.assertSetEqual(desired, obj.files_methods_and_classes_testing)

        # Get oracle variables
        correct_test_startline = first_line_in_file_beginning_with_ignoring_whitespace(os.path.join(ROOT_DIR, "test_py_holmes.py"), "def test_parse_holmessearchextend(self):")
        correct_test_endline = first_line_in_file_beginning_with_ignoring_whitespace(os.path.join(ROOT_DIR, "test_py_holmes.py"), """from ph_basic_processing.scrapers_for_holmesignore_and_holmessearchextend import parse_holmessearchextend""") + 5
        correct_class_startline = first_line_in_file_beginning_with_ignoring_whitespace(os.path.join(ROOT_DIR, "test_py_holmes.py"), "class TestHolmessearchextendEXTERNAL(unittest.TestCase):")
        correct_class_endline = first_line_in_file_beginning_with_ignoring_whitespace(os.path.join(ROOT_DIR, "test_py_holmes.py"), "class TestOnlyRespondingToFailuresInUserCode(unittest.TestCase):")

        # ...check starting_test_lineno and starting_test_lineno_as_index
        self.assertEqual(correct_test_startline, obj.starting_test_lineno)
        self.assertEqual(obj.starting_test_lineno - 1, obj.starting_test_lineno_as_index)

        # ...check ending_test_lineno and ending_test_lineno_as_index
        self.assertEqual(correct_test_endline, obj.ending_test_lineno)
        self.assertEqual(obj.ending_test_lineno - 1, obj.ending_test_lineno_as_index)

        # ...check starting_class_lineno and starting_class_lineno_as_index
        self.assertEqual(correct_class_startline, obj.starting_class_lineno)
        self.assertEqual(obj.starting_class_lineno - 1, obj.starting_class_lineno_as_index)

        # ...check ending_class_lineno and ending_class_lineno_as_index
        self.assertEqual(correct_class_endline, obj.ending_class_lineno)
        self.assertEqual(obj.ending_class_lineno - 1, obj.ending_class_lineno_as_index)

    def test_calculate_all_imports_and_files_methods_and_classes_testing(self):
        """Ensure that running calculate_all_imports_and_files_methods_and_classes_testing on a TestMethod object
        returns the correct values to be turned into self.all_imports and self.files_methods_and_classes_testing.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.
        # Create a TestMethod object and set its files_methods_and_classes_testing attribute
        obj = class_for_test_method.TestMethod(origin="found", test_filepath=os.path.join(ROOT_DIR, "test_circle_method.py"), starting_test_lineno=12, is_fuzzed=False, is_original=False)
        desired = [{"math.pi", "circle_method.circle_area"}, {"circle_method.circle_area"}]
        self.assertSetEqual(desired[0], obj.all_imports)
        self.assertSetEqual(desired[1], obj.files_methods_and_classes_testing)

    def test_finding_all_related_tests_simple(self):
        """Run find_tests_of_same_files_methods_and_classes() on test_circle_method.test_types and ensure that all
        relevant tests in the project are found.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.
        # Get tests of same files/methods/classes as test_circle_method.test_area -- that is, tests that reference a
        # nonempty subset of {circle_area}
        test_method = class_for_test_method.TestMethod("found", os.path.join(ROOT_DIR, "test_circle_method.py"), 24, False, False)
        objects = unit_test_finders.find_tests_of_same_files_methods_and_classes(test_method, dev_only_test_mode=True)
        result = [[this_object.test_filepath, this_object.test_name] for this_object in objects]
        desired = [
            [os.path.join(ROOT_DIR, 'test_circle_method.py'), 'test_area'],
            [os.path.join(ROOT_DIR, 'test_circle_method.py'), 'test_values'],
            [os.path.join(ROOT_DIR, 'test_circle_method_that_fails_to_import_unittest.py'), 'test_area'],
            [os.path.join(ROOT_DIR, 'test_circle_method_that_fails_to_import_unittest.py'), 'test_values'],
            [os.path.join(ROOT_DIR, 'test_circle_method_that_fails_to_import_unittest.py'), 'test_types'],
            [os.path.join(ROOT_DIR, 'test_circle_method_that_calls_crashing_method.py'), 'test_area'],
            [os.path.join(ROOT_DIR, 'test_circle_method_that_calls_crashing_method.py'), 'test_values'],
            [os.path.join(ROOT_DIR, 'test_circle_method_that_calls_crashing_method.py'), 'test_types'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_an_empty_test_method.py'), 'test_area'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_an_empty_test_method.py'), 'test_values'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_an_empty_test_method.py'), 'test_types'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_asterisk_import_0.py'), 'test_area'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_asterisk_import_0.py'), 'test_values'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_asterisk_import_0.py'), 'test_types'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_asterisk_import_1.py'), 'test_area'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_asterisk_import_1.py'), 'test_values'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_asterisk_import_1.py'), 'test_types'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_bad_import.py'), 'test_area'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_bad_import.py'), 'test_values'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_bad_import.py'), 'test_types'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_call_to_file_outside_project_folder.py'), 'test_area'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_call_to_file_outside_project_folder.py'), 'test_values'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_call_to_file_outside_project_folder.py'), 'test_types'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py'), 'test_area'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py'), 'test_values'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_features_for_TestOnlyRespondingToFailuresInUserCode.py'), 'test_types'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_tatosp_2.py'), 'test_area'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_tatosp_2.py'), 'test_values'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_tatosp_2.py'), 'test_types'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_tests_without_asserts.py'), 'test_area'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_tests_without_asserts.py'), 'test_values'],
            [os.path.join(ROOT_DIR, 'test_circle_method_with_tests_without_asserts.py'), 'test_types'],
            [os.path.join(ROOT_DIR, 'test_methods_for_test_cut_found_tests.py'), 'test_original'],
            [os.path.join(ROOT_DIR, 'test_methods_for_test_cut_found_tests.py'), 'test_variant_0'],
            [os.path.join(ROOT_DIR, 'test_methods_for_test_cut_found_tests.py'), 'test_variant_1'],
            [os.path.join(ROOT_DIR, 'test_methods_for_test_cut_found_tests.py'), 'test_variant_2'],
            [os.path.join(ROOT_DIR, 'test_methods_for_test_cut_found_tests.py'), 'test_variant_3'],
            [os.path.join(ROOT_DIR, 'test_methods_for_test_cut_found_tests.py'), 'test_variant_4'],
            [os.path.join(ROOT_DIR, 'test_methods_for_test_cut_found_tests.py'), 'test_variant_5'],
            [os.path.join(ROOT_DIR, 'test_methods_for_test_cut_found_tests.py'), 'test_variant_6'],
            [os.path.join(ROOT_DIR, 'test_circle_method_format_fitting.py'), 'test_area'],
            [os.path.join(ROOT_DIR, 'test_circle_method_format_fitting.py'), 'test_types'],
            [os.path.join(ROOT_DIR, 'test_circle_method_format_fitting.py'), 'test_values'],
            [os.path.join(ROOT_DIR, 'test_circle_method_provoke_human_help_request.py'), 'test_area'],
            [os.path.join(ROOT_DIR, 'test_circle_method_provoke_human_help_request.py'), 'test_types'],
            [os.path.join(ROOT_DIR, 'test_circle_method_provoke_human_help_request.py'), 'test_values'],
        ]
        self.assertCountEqual(desired, result)

    def test_finding_all_related_tests_with_asterisk_imports(self):
        """Find all tests related to test_circle_method_with_asterisk_import_0.test_values, and ensure that
        test_circle_method_with_asterisk_import_1.test_values is among these.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.
        test_method = class_for_test_method.TestMethod("found", os.path.join(ROOT_DIR, "test_circle_method_with_asterisk_import_0.py"), 20, False, False)
        result = unit_test_finders.find_tests_of_same_files_methods_and_classes(test_method, dev_only_test_mode=True)
        filepaths_with_names = [(element.test_filepath, element.test_name) for element in result]
        self.assertIn((os.path.join(ROOT_DIR, 'test_circle_method_with_asterisk_import_1.py'), "test_values"), filepaths_with_names)

    def test_finding_all_related_tests_with_folder_relativity(self):
        """Find all tests related to ph_assets_for_test_py_holmes_0.test_bark_method_same_folder_absolute_reference.test_bark, and ensure
        that the following tests are included:
        * ph_assets_for_test_py_holmes_0.test_bark_method_same_folder_relative_reference.test_bark
        * test_bark_method_higher_folder_absolute_reference.test_bark
        Then find all tests related to ph_assets_for_test_py_holmes_0.test_bark_method_same_folder_relative_reference.test_bark, and
        ensure that the following tests are included:
        * ph_assets_for_test_py_holmes_0.test_bark_method_same_folder_absolute_reference.test_bark
        * test_bark_method_higher_folder_absolute_reference.test_bark
        Finally, find all tests related to test_bark_method_higher_folder_absolute_reference.test_bark and ensure that
        the following tests are included:
        * ph_assets_for_test_py_holmes_0.test_bark_method_same_folder_absolute_reference.test_bark
        * ph_assets_for_test_py_holmes_0.test_bark_method_same_folder_relative_reference.test_bark
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # First check
        test_method = class_for_test_method.TestMethod("found", os.path.abspath(os.path.join(ROOT_DIR,
                                                                                             "ph_assets_for_test_py_holmes_0/test_bark_method_same_folder_absolute_reference.py")), 6, False, False)
        result = unit_test_finders.find_tests_of_same_files_methods_and_classes(test_method, dev_only_test_mode=True)
        filepaths_with_names = [(element.test_filepath, element.test_name) for element in result]
        self.assertIn((os.path.abspath(os.path.join(ROOT_DIR,
                                                    "ph_assets_for_test_py_holmes_0/test_bark_method_same_folder_relative_reference.py")), "test_bark"), filepaths_with_names)
        self.assertIn((os.path.join(ROOT_DIR, "test_bark_method_higher_folder_absolute_reference.py"), "test_bark"), filepaths_with_names)

        # Second check
        test_method = class_for_test_method.TestMethod("found", os.path.abspath(os.path.join(ROOT_DIR,
                                                                                             "ph_assets_for_test_py_holmes_0/test_bark_method_same_folder_relative_reference.py")), 6, False, False)
        result = unit_test_finders.find_tests_of_same_files_methods_and_classes(test_method, dev_only_test_mode=True)
        filepaths_with_names = [(element.test_filepath, element.test_name) for element in result]
        self.assertIn((os.path.abspath(os.path.join(ROOT_DIR,
                                                    "ph_assets_for_test_py_holmes_0/test_bark_method_same_folder_absolute_reference.py")), "test_bark"), filepaths_with_names)
        self.assertIn((os.path.abspath(os.path.join(ROOT_DIR, "test_bark_method_higher_folder_absolute_reference.py")), "test_bark"), filepaths_with_names)

        # Third check
        test_method = class_for_test_method.TestMethod("found", os.path.abspath(os.path.join(ROOT_DIR, "test_bark_method_higher_folder_absolute_reference.py")), 6, False, False)
        result = unit_test_finders.find_tests_of_same_files_methods_and_classes(test_method, dev_only_test_mode=True)
        filepaths_with_names = [(element.test_filepath, element.test_name) for element in result]
        self.assertIn((os.path.abspath(os.path.join(ROOT_DIR,
                                                    "ph_assets_for_test_py_holmes_0/test_bark_method_same_folder_absolute_reference.py")), "test_bark"), filepaths_with_names)
        self.assertIn((os.path.abspath(os.path.join(ROOT_DIR,
                                                    "ph_assets_for_test_py_holmes_0/test_bark_method_same_folder_relative_reference.py")), "test_bark"), filepaths_with_names)

    def test_finding_all_related_tests_with_asterisk_imports_AND_folder_relativity(self):
        """Find all tests related to ph_assets_for_test_py_holmes_0.test_bark_method_same_folder_absolute_reference.test_bark, and ensure
        that the following tests are included:
        * ph_assets_for_test_py_holmes_0.test_bark_method_same_folder_relative_reference_asterisk.test_bark
        * test_bark_method_higher_folder_absolute_reference_asterisk.test_bark
        Then find all tests related to ph_assets_for_test_py_holmes_0.test_bark_method_same_folder_relative_reference_asterisk.test_bark,
        and ensure that the following tests are included:
        * ph_assets_for_test_py_holmes_0.test_bark_method_same_folder_absolute_reference.test_bark
        * test_bark_method_higher_folder_absolute_reference.test_bark
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # First check
        test_method = class_for_test_method.TestMethod("found", os.path.abspath(os.path.join(ROOT_DIR,
                                                                                             "ph_assets_for_test_py_holmes_0/test_bark_method_same_folder_absolute_reference.py")), 6, False, False)
        result = unit_test_finders.find_tests_of_same_files_methods_and_classes(test_method, dev_only_test_mode=True)
        filepaths_with_names = [(element.test_filepath, element.test_name) for element in result]
        self.assertIn((os.path.abspath(os.path.join(ROOT_DIR,
                                                    "ph_assets_for_test_py_holmes_0/test_bark_method_same_folder_relative_reference_asterisk.py")), "test_bark"), filepaths_with_names)
        self.assertIn((os.path.join(ROOT_DIR, "test_bark_method_higher_folder_absolute_reference_asterisk.py"), "test_bark"), filepaths_with_names)

        # Second check
        test_method = class_for_test_method.TestMethod("found", os.path.abspath(os.path.join(ROOT_DIR,
                                                                                             "ph_assets_for_test_py_holmes_0/test_bark_method_same_folder_relative_reference_asterisk.py")), 6, False, False)
        result = unit_test_finders.find_tests_of_same_files_methods_and_classes(test_method, dev_only_test_mode=True)
        filepaths_with_names = [(element.test_filepath, element.test_name) for element in result]
        self.assertIn((os.path.abspath(os.path.join(ROOT_DIR,
                                                    "ph_assets_for_test_py_holmes_0/test_bark_method_same_folder_absolute_reference.py")), "test_bark"), filepaths_with_names)
        self.assertIn((os.path.join(ROOT_DIR, "test_bark_method_higher_folder_absolute_reference.py"), "test_bark"), filepaths_with_names)

    def test_import_with_commas_involving_from(self):
        """Create a TestMethod object for ph_assets_for_test_py_holmes_0.test_comma_imports_method.test_comma_imports_method_with_from(),
        then ensure it has a correct files_methods_and_classes_testing attribute
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        obj = class_for_test_method.TestMethod("found", test_filepath=os.path.abspath(os.path.join(ROOT_DIR,
                                                                                                   "ph_assets_for_test_py_holmes_0/test_comma_imports_method.py")), starting_test_lineno=11, is_fuzzed=False, is_original=False)
        self.assertSetEqual({"ph_assets_for_test_py_holmes_0.comma_imports_method.compute", "ph_assets_for_test_py_holmes_0.comma_imports_imported.my_sin", "ph_assets_for_test_py_holmes_0.comma_imports_imported.my_cos", "ph_assets_for_test_py_holmes_0.comma_imports_imported.my_tan"}, obj.files_methods_and_classes_testing)

    def test_import_foo_as_bar(self):
        """Create a TestMethod object for ph_assets_for_test_py_holmes_0.test_as_imports_methods.test_using_import_foo_as_bar(),
        then ensure it has a correct files_methods_and_classes_testing_attribute
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        obj = class_for_test_method.TestMethod("found", test_filepath=os.path.abspath(os.path.join(ROOT_DIR,
                                                                                                   "ph_assets_for_test_py_holmes_0/test_as_imports_methods.py")), starting_test_lineno=10, is_fuzzed=False, is_original=False)
        self.assertSetEqual({"ph_assets_for_test_py_holmes_0.as_imports_methods"}, obj.files_methods_and_classes_testing)

    def test_from_foo_import_bar_as_baz(self):
        """Create a TestMethod object for ph_assets_for_test_py_holmes_0.test_as_imports_methods.test_using_from_foo_import_bar_as_baz(),
        then ensure it has a correct files_methods_and_classes_testing_attribute
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        obj = class_for_test_method.TestMethod("found", test_filepath=os.path.abspath(os.path.join(ROOT_DIR,
                                                                                                   "ph_assets_for_test_py_holmes_0/test_as_imports_methods.py")), starting_test_lineno=15, is_fuzzed=False, is_original=False)
        self.assertSetEqual({"ph_assets_for_test_py_holmes_0.as_imports_methods.compute0"}, obj.files_methods_and_classes_testing)

    def test_from_foo_import_bar_as_baz_comma_car_as_caz(self):
        """Create a TestMethod object for
        ph_assets_for_test_py_holmes_0.test_as_imports_methods.test_using_from_foo_import_bar_as_baz_comma_car_as_caz(),
        then ensure it has a correct files_methods_and_classes_testing_attribute
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        obj = class_for_test_method.TestMethod("found", test_filepath=os.path.abspath(os.path.join(ROOT_DIR,
                                                                                                   "ph_assets_for_test_py_holmes_0/test_as_imports_methods.py")), starting_test_lineno=20, is_fuzzed=False, is_original=False)
        self.assertSetEqual({"ph_assets_for_test_py_holmes_0.as_imports_methods.compute0", "ph_assets_for_test_py_holmes_0.as_imports_methods.compute1"}, obj.files_methods_and_classes_testing)

    def test_cut_found_tests(self):
        """Run ph_causal_testing.unit_test_cutters.cut_found_tests on a set of found tests, and ensure that the cut/keep
        choices are made.
        """

        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a TestMethod object for the original test
        original = class_for_test_method.TestMethod(origin="found", test_filepath=os.path.join(ROOT_DIR, "test_methods_for_test_cut_found_tests.py"), starting_test_lineno=10, is_fuzzed=False, is_original=False)

        # Create a list of TestMethod objects for the variant tests
        variants = []
        for lineno in [16, 24, 32, 40, 47, 56, 64]:
            variants.append(class_for_test_method.TestMethod(origin="found", test_filepath=os.path.join(ROOT_DIR, "test_methods_for_test_cut_found_tests.py"), starting_test_lineno=lineno, is_fuzzed=False, is_original=False))

        # Run cut_found_tests()
        result = unit_test_cutters.cut_found_tests(variants, original, dev_only_test_mode=True)

        # Ensure that the correct variants are kept vs cut
        result_names = [test.test_name for test in result]
        desired_names = ["test_variant_0", "test_variant_1", "test_variant_6"]
        self.assertCountEqual(desired_names, result_names)


class TestUnitTestFuzzing(unittest.TestCase):
    """Tests py-holmes's ability to fuzz both found and generated unit tests"""

    def test_fuzz_targeting(self):
        """Run a FuzzTargeter on an ast and ensure that the correct nodes for fuzzing are targeted"""
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Get a test
        with open("test_another_literals_indirectly_linked_to_oracles.py", "r", encoding="utf-8") as file:
            file_content = file.read()
        file_test = file_content[file_content.index("   def test_"):]
        file_test = file_test.split("\n")
        # Minimize indentation
        file_test = minimize_indents(file_test)
        file_test = concatenate_list_to_string(file_test, between="\n")
        # Parse into an ast
        test_ast = ast.parse(file_test)

        # Run the targeter on the ast and collect which nodes it thinks should become fuzzed
        targeter = unit_test_fuzzers.FuzzTargeter(test_ast)
        nodes_for_fuzzing = targeter.fuzzing_targets

        # Check for correct targeting
        values_for_fuzzing = [element.value for element in nodes_for_fuzzing]
        self.assertCountEqual([4, "here's another number: ", 8], values_for_fuzzing)

    def test_fuzz_actuation(self):
        """Run a FuzzActuator on an ast and ensure that the requested nodes for fuzzing are fuzzed"""
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Get an ast
        with open("test_another_literals_indirectly_linked_to_oracles.py", "r", encoding="utf-8") as file:
            file_content = file.read()
        file_test = file_content[file_content.index("   def test_"):]
        file_test = file_test.split("\n")
        # Minimize indentation
        file_test = minimize_indents(file_test)
        file_test = concatenate_list_to_string(file_test, between="\n")
        # Parse into an ast
        test_ast = ast.parse(file_test)

        # Run the targeter on the ast and collect which nodes it thinks should become fuzzed
        targeter = unit_test_fuzzers.FuzzTargeter(test_ast)
        nodes_for_fuzzing = targeter.fuzzing_targets
        paths_to_nodes_for_fuzzing = targeter.fuzzing_target_paths

        # Get "replacement nodes" (these are just spoofs so that we can avoid running other functions, so that we can
        # test FuzzActuator in isolation)
        template_replacement = ast.Constant(value="placeholder", kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)
        replacement_nodes = [template_replacement for _ in nodes_for_fuzzing]

        # Fuzz those nodes
        actuator = unit_test_fuzzers.FuzzActuator(test_ast, paths_to_nodes_for_fuzzing, replacement_nodes)
        test_ast = actuator.generic_visit(test_ast, path_to_node=None)

        # Check that exactly the nodes we requested are turned into "placeholder", and no other nodes are changed this
        # way
        class FuzzChecker(ast.NodeVisitor):
            """Checks that exactly the nodes we requested are turned into the constant node "placeholder", and no other
            nodes are changed this way
            """
            def __init__(self, root, paths_that_should_be_placeholder: list):
                """
                :param root:                                root node object of an ast
                :param paths_that_should_be_placeholder:    list of all the paths that should be replaced with the constant node "placeholder"
                """
                # Handle errors
                # root not an AST
                if not isinstance(root, ast.AST):
                    raise TypeError("root must be an AST object")
                # paths_that_should_be_placeholder not a list
                if not isinstance(paths_that_should_be_placeholder, list):
                    raise TypeError("paths_that_should_be_placeholder must be a list")
                # paths_that_should_be_placeholder contains non-list element
                for element in paths_that_should_be_placeholder:
                    if not isinstance(element, list):
                        raise TypeError("all elements of paths_that_should_be_placeholder must be lists")

                self.root = root
                self.paths_that_should_be_placeholder = paths_that_should_be_placeholder

                # Check for correct placeholders
                self.generic_visit(node=root)

            def generic_visit(self, node, path_to_node=None):
                """Ensure that every node in the tree is either:
                ...not "placeholder" and doesn't appear in self.paths_that_should_be_placeholder
                OR
                ..."placeholder" and appears in self.paths_that_should_be_placeholder
                """
                if path_to_node is None:
                    path_to_node = []

                if path_to_node in self.paths_that_should_be_placeholder:
                    assert hasattr(node, "value") and node.value == "placeholder"
                else:
                    if hasattr(node, "value"):
                        assert node.value != "placeholder"

                # Call the base generic_visit so that other nodes are visited.
                # Rather than a direct call to generic_visit(), this is a copypaste of the source code for generic_visit(),
                # with modification so that path_to_node is passed along
                for field, value in ast.iter_fields(node):
                    if isinstance(value, list):
                        for ii in range(len(value)):
                            item = value[ii]
                            if isinstance(item, ast.AST):
                                self.generic_visit(item, path_to_node=path_to_node + [f".{field}", f"[{str(ii)}]"])
                    elif isinstance(value, ast.AST):
                        self.generic_visit(value, path_to_node=path_to_node + [f".{field}"])

        checker = FuzzChecker(test_ast, paths_to_nodes_for_fuzzing)

    def test_fuzzing_int(self):
        """Run fuzz_literal_node on a node representing an int.  Ensure that the requested number of fuzzed variants
        are returned, and that they are all in the appropriate range.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a node
        node = ast.Constant(value=50, kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        for _ in range(100):    # Repeat 100 times to improve reliability, since fuzzing is random
            # Fuzz!
            fuzzed = unit_test_fuzzers.fuzz_literal_node(node, dev_only_test_mode=False, fuzzing_mutants_count=5, fuzzing_max_string_changes=3, fuzzing_max_num_added=10, fuzzing_num_chance_to_negate=0.5, fuzzing_max_complex_angle_change=pi, fuzzing_bool_chance_to_flip=0.5)

            # Check that the requested number of fuzzed variants are returned
            self.assertEqual(5, len(fuzzed))

            # Check that each variant is in the appropriate range
            for element in fuzzed:
                value = element.value
                self.assertTrue(-1050 <= value <= 1050)

    def test_fuzzing_float(self):
        """Run fuzz_literal_node on a node representing a float.  Ensure that the requested number of fuzzed variants
        are returned, and that they are all in the appropriate range.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a node
        node = ast.Constant(value=50.05, kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        for _ in range(100):  # Repeat 100 times to improve reliability, since fuzzing is random
            # Fuzz!
            fuzzed = unit_test_fuzzers.fuzz_literal_node(node, dev_only_test_mode=False, fuzzing_mutants_count=5, fuzzing_max_string_changes=3, fuzzing_max_num_added=10, fuzzing_num_chance_to_negate=0.5, fuzzing_max_complex_angle_change=pi, fuzzing_bool_chance_to_flip=0.5)

            # Check that the requested number of fuzzed variants are returned
            self.assertEqual(5, len(fuzzed))

            # Check that each variant is in the appropriate range
            for element in fuzzed:
                value = element.value
                self.assertTrue(-1050.05 <= value <= 1050.05)

    def test_fuzzing_complex(self):
        """Run fuzz_literal_node on a node representing a complex number.  Ensure that the requested number of fuzzed
        variants are returned, and that they are all in the appropriate range.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a node
        node = ast.Constant(value=complex(50, 50), kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        for _ in range(100):  # Repeat 100 times to improve reliability, since fuzzing is random
            # Fuzz!
            fuzzed = unit_test_fuzzers.fuzz_literal_node(node, dev_only_test_mode=False, fuzzing_mutants_count=5, fuzzing_max_string_changes=3, fuzzing_max_num_added=10, fuzzing_num_chance_to_negate=0.5, fuzzing_max_complex_angle_change=pi/4, fuzzing_bool_chance_to_flip=0.5)

            # Check that the requested number of fuzzed variants are returned
            self.assertEqual(5, len(fuzzed))

            # Check that each variant is in the appropriate range
            for element in fuzzed:
                value = element.value
                angle = atan2(value.imag, value.real)
                if angle < 0:
                    angle += 2*pi
                # Check magnitude
                self.assertGreater(1070.7107, abs(value))
                # Check angle
                self.assertTrue(0 <= angle <= pi/2)

    def test_fuzzing_string(self):
        """Run fuzz_literal_node on a node representing a string.  Ensure that the requested number of fuzzed variants
        are returned, and that they are all in the appropriate 'range'.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a node
        node = ast.Constant(value="foo", kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        for _ in range(100):  # Repeat 100 times to improve reliability, since fuzzing is random
            # Fuzz!
            fuzzed = unit_test_fuzzers.fuzz_literal_node(node, dev_only_test_mode=False, fuzzing_mutants_count=5, fuzzing_max_string_changes=3, fuzzing_max_num_added=10, fuzzing_num_chance_to_negate=0.5, fuzzing_max_complex_angle_change=pi, fuzzing_bool_chance_to_flip=0.5)

            # Check that the requested number of fuzzed variants are returned
            self.assertEqual(5, len(fuzzed))

            # Check that each variant is in the appropriate range
            for element in fuzzed:
                value = element.value
                # Check that no more than 3 changes were made
                self.assertGreaterEqual(3, levenshtein_distance("foo", value))
                # Check that only lowercase alphabetical characters are present
                for char in value:
                    self.assertIn(char, "abcdefghijklmnopqrstuvwxyz")

    def test_fuzzing_bool(self):
        """Run fuzz_literal_node on a node representing a bool, without requesting more variants than can be provided.
        Ensure that the requested number of fuzzed variants are returned, and that they are all in the appropriate
        'range'.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a node
        node = ast.Constant(value=True, kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        for _ in range(100):  # Repeat 100 times to improve reliability, since fuzzing is random
            # Fuzz!
            fuzzed = unit_test_fuzzers.fuzz_literal_node(node, dev_only_test_mode=False, fuzzing_mutants_count=2, fuzzing_max_string_changes=3, fuzzing_max_num_added=10, fuzzing_num_chance_to_negate=0.5, fuzzing_max_complex_angle_change=pi, fuzzing_bool_chance_to_flip=0.5)

            # Check that the list contains one True and one False
            values = [node.value for node in fuzzed]
            self.assertCountEqual([True, False], values)

    def test_int_space_limited_fuzz(self):
        """Run fuzz_literal_node on a node representing an int, while requesting more unique variants than can actually
        be provided.  Check that the length of the returned list is as long as it can be.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a node
        node = ast.Constant(value=1, kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        for _ in range(100):  # Repeat 100 times to improve reliability, since fuzzing is random
            # Fuzz!
            fuzzed = unit_test_fuzzers.fuzz_literal_node(node, dev_only_test_mode=False, fuzzing_mutants_count=10, fuzzing_max_string_changes=3, fuzzing_max_num_added=1, fuzzing_num_chance_to_negate=0.5, fuzzing_max_complex_angle_change=pi, fuzzing_bool_chance_to_flip=0.5)

            # Check that the correct number of fuzzed variants are returned
            self.assertEqual(5, len(fuzzed))

    def test_float_space_limited_fuzz(self):
        """Run fuzz_literal_node on a node representing a float, while requesting more unique variants than can actually
        be provided.  Check that the length of the returned list is as long as it can be.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a node
        node = ast.Constant(value=1.1, kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        for _ in range(100):  # Repeat 100 times to improve reliability, since fuzzing is random
            # Fuzz!
            fuzzed = unit_test_fuzzers.fuzz_literal_node(node, dev_only_test_mode=False, fuzzing_mutants_count=10, fuzzing_max_string_changes=3, fuzzing_max_num_added=0, fuzzing_num_chance_to_negate=0.5, fuzzing_max_complex_angle_change=pi, fuzzing_bool_chance_to_flip=0.5)

            # Check that the correct number of fuzzed variants are returned
            self.assertEqual(2, len(fuzzed))

    def test_complex_space_limited_fuzz(self):
        """Run fuzz_literal_node on a node representing a complex, while requesting more unique variants than can
        actually be provided.  Check that the length of the returned list is as long as it can be.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a node
        node = ast.Constant(value=complex(50, 50), kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        for _ in range(100):  # Repeat 100 times to improve reliability, since fuzzing is random
            # Fuzz!
            fuzzed = unit_test_fuzzers.fuzz_literal_node(node, dev_only_test_mode=False, fuzzing_mutants_count=10, fuzzing_max_string_changes=3, fuzzing_max_num_added=0, fuzzing_num_chance_to_negate=0.5, fuzzing_max_complex_angle_change=0, fuzzing_bool_chance_to_flip=0.5)

            # Check that the correct number of fuzzed variants are returned
            self.assertEqual(1, len(fuzzed))

    def test_string_space_limited_fuzz(self):
        """Run fuzz_literal_node on a node representing a string, while requesting more unique variants than can
        actually be provided.  Check that the length of the returned list is as long as it can be.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a node
        node = ast.Constant(value="&", kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        for _ in range(100):  # Repeat 100 times to improve reliability, since fuzzing is random
            # Fuzz!
            fuzzed = unit_test_fuzzers.fuzz_literal_node(node, dev_only_test_mode=False, fuzzing_mutants_count=10, fuzzing_max_string_changes=3, fuzzing_max_num_added=1, fuzzing_num_chance_to_negate=0.5, fuzzing_max_complex_angle_change=pi, fuzzing_bool_chance_to_flip=0.5)

            # Check that the correct number of fuzzed variants are returned
            self.assertEqual(5, len(fuzzed))

    def test_bool_space_limited_fuzz(self):
        """Run fuzz_literal_node on a node representing a bool, while requesting more unique variants than can actually
        be provided.  Check that the length of the returned list is as long as it can be.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a node
        node = ast.Constant(value=True, kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        for _ in range(100):  # Repeat 100 times to improve reliability, since fuzzing is random
            # Fuzz!
            fuzzed = unit_test_fuzzers.fuzz_literal_node(node, dev_only_test_mode=False, fuzzing_mutants_count=10, fuzzing_max_string_changes=3, fuzzing_max_num_added=1, fuzzing_num_chance_to_negate=0.5, fuzzing_max_complex_angle_change=pi, fuzzing_bool_chance_to_flip=0.5)

            # Check that the correct number of fuzzed variants are returned
            self.assertEqual(2, len(fuzzed))

    def test_fuzzing_on_real_test(self):
        """Run py-holmes so that a real test is fuzzed, then ensure all tests are runnable and that their literals line
        up with their originals.
        THIS TEST NEEDS TO BE RUN USING UNITTEST, NOT PYTEST.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f test_all_literals_isolated_assert.py -l 9 --dev_only_test_mode")

        # Get the fuzzed tests
        with open("test_outputs_fuzzed.py", "r", encoding="utf-8") as file:
            fuzzed_output = file.readlines()

        # Get the line index of the first test in the output
        first_test_index = None
        for ll in range(len(fuzzed_output)):
            line = fuzzed_output[ll]
            if line.startswith("    def test_fuzzed_"):
                first_test_index = ll
                break
        self.assertIsNotNone(first_test_index)

        # Ensure at least 20 unique tests are in the output
        tests = []  # List of sublists, where each sublist is a particular test method line-by-line
        for ll in range(first_test_index, len(fuzzed_output)):  # We skip the lines before the first test method
            line = fuzzed_output[ll]
            # If this line is the start of a new test, append it to tests
            if line.startswith("    def test_fuzzed_") and line.endswith("):\n"):
                tests.append([line])
            # Else, append this line to the most recent test in tests
            else:
                tests[-1].append(line)
        # Shave off the last element of the last test; this is an extra newline at the end of the file
        if is_just_whitespace(tests[-1][-1]):
            del tests[-1][-1]
        # Remove duplicates
        tests = remove_duplicates_from_list(tests)
        # Check number of tests
        self.assertLessEqual(20, len(tests))

        # Run a linter on all fuzzed tests to ensure they don't have errors
        os.system("pylint test_outputs_fuzzed.py > pylint_result.txt")
        with open("pylint_result.txt", "r", encoding="utf-8") as file:
            pylint_output = file.readlines()
        pylint_code_starting_letters = [line.split(": ")[1][0] for line in pylint_output if line.startswith("test_outputs_fuzzed.py")]
        self.assertNotIn("E", pylint_code_starting_letters)

        # Ensure all test nodes are the same as the original, except for fuzzable nodes
        response = input("HUMAN HELP NEEDED: Could the tests currently in test_outputs_fuzzed.py have reasonably been created by fuzzing the test at test_all_literals_isolated_assert.py? (Y/n): ")
        self.assertEqual("Y", response.upper())

    def test_infer_character_palette(self):
        """Run infer_character_palette() on some strings and ensure it returns the appropriate palette.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Alphabetical lowercase single
        self.assertCountEqual([char for char in "abcdefghijklmnopqrstuvwxyz"], unit_test_fuzzers.infer_character_palette("e"))

        # Alphabetical uppercase single
        self.assertCountEqual([char for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"], unit_test_fuzzers.infer_character_palette("E"))

        # Number single
        self.assertCountEqual([char for char in "0123456789"], unit_test_fuzzers.infer_character_palette("5"))

        # Punctuation single
        self.assertCountEqual([char for char in ".!?,"], unit_test_fuzzers.infer_character_palette(","))

        # Four-function single
        self.assertCountEqual([char for char in "+-/*"], unit_test_fuzzers.infer_character_palette("/"))

        # Parentheses single
        self.assertCountEqual([char for char in "()"], unit_test_fuzzers.infer_character_palette("("))

        # Square bracket single
        self.assertCountEqual([char for char in "[]"], unit_test_fuzzers.infer_character_palette("]"))

        # Curly brace single
        self.assertCountEqual([char for char in "{}"], unit_test_fuzzers.infer_character_palette("{"))

        # Angle bracket single
        self.assertCountEqual([char for char in "<>"], unit_test_fuzzers.infer_character_palette(">"))

        # Mix of several including an ungrouped character
        self.assertCountEqual([char for char in "().!?,ABCDEFGHIJKLMNOPQRSTUVWXYZ "], unit_test_fuzzers.infer_character_palette("(A!) "))

    def test_user_defined_character_palette(self):
        """Run fuzz_literal_node with manual user-defined character palettes.  Ensure that all characters the user
        entered are represented, and none that the user didn't enter are.
        THIS TEST NEEDS TO BE RUN USING UNITTEST, NOT PYTEST.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        print("HUMAN HELP NEEDED: When asked to enter a manual character string, enter 'a?!'")

        # Create a node
        node = ast.Constant(value="Hello", kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        # Fuzz!  We ask for very many fuzzed variants and very high distance, to ensure reliability
        fuzzed = unit_test_fuzzers.fuzz_literal_node(node, dev_only_test_mode=False, manual_fuzzing_characters=True, fuzzing_mutants_count=1000, fuzzing_max_string_changes=1000, fuzzing_max_num_added=10, fuzzing_num_chance_to_negate=0.5, fuzzing_max_complex_angle_change=pi, fuzzing_bool_chance_to_flip=0.5)

        # Check that each fuzzed result has only permitted characters
        permitted = "Helloa?!"
        for node in fuzzed:
            result_string = node.value
            for char in result_string:
                self.assertIn(char, permitted)

    def test_single_literal_fuzzing_of_original_test(self):
        """Fuzz an original test and ensure that each fuzzed variant differs from it by exactly one literal."""
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a TestMethod object from an original test
        test_method = class_for_test_method.TestMethod("found", os.path.join(ROOT_DIR, "test_circle_method.py"), 24, is_fuzzed=False, is_original=True)

        # Get fuzzed test strings; we create 58 for reliability
        fuzzed_strings = unit_test_fuzzers.create_fuzzed_test_strings(test_method, False, False, num_tests_to_create=58)

        # Check that each fuzzed variant differs from the original by exactly one literal
        original_literals_as_strings = [" 2 + 5.0j", "True", "'Hello'"]
        for this_test in fuzzed_strings:
            count_different = 0
            for element in original_literals_as_strings:
                if element not in this_test:
                    count_different += 1
            self.assertEqual(1, count_different)

    def test_half_of_fuzzed_tests_are_from_original(self):
        """Fuzz a list of original tests and ensure that half of the fuzzed variants are from the original test"""
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f test_circle_method.py -l 24 --dev_only_test_mode")
        result = contents_of_log_file()

        # Postprocess result
        # Get just the variant tally
        index_begin = result.index("BEGIN FUZZ VARIANT TALLY")
        index_end = result.index("END FUZZ VARIANT TALLY")
        result = result[index_begin+87:index_end-1]
        result = result.split("\n")
        # Parse
        parsed = []     # Each element is a sublist representing one test.  Each sublist's element 0 is whether the test is original, and element 1 is the number of variants
        variants_total = 0
        variants_from_original = None
        for line in result:
            is_original = line.startswith("True")
            num_variants = int(line.split("\t")[-1])
            variants_total += num_variants
            if is_original:
                variants_from_original = num_variants
            parsed.append([is_original, num_variants])
        self.assertIsNotNone(variants_from_original)

        # Ensure that half of the fuzzed variants are from the original test
        self.assertEqual(ceil(variants_total/2), variants_from_original)

    def test_custom_number_variants(self):
        """Run py-holmes with a CLI flag to generate a non-default number of variant tests.  Check that the requested
        number of variant tests is produced.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f test_circle_method.py -l 24 --num_test_variants 100 --dev_only_test_mode")

        # Get the fuzzed tests
        with open("test_outputs_fuzzed.py", "r", encoding="utf-8") as file:
            fuzzed_output = file.read()

        # Ensure the correct number of tests was written
        self.assertEqual(100, fuzzed_output.count("def test"))

    def test_user_help_skip_for_oracle_recognition(self):
        """Run py-holmes on a unit test for which it would normally request human help, but use the --user_help_skip
        flag.  Check that it doesn't request human help.
        THIS TEST NEEDS TO BE RUN USING UNITTEST, NOT PYTEST.
        """
        # TODO: Ensure that human help is requested when the flag is not used.
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f test_circle_method_provoke_human_help_request.py -l 30 --user_help_skip")

        # Ensure that human help was not requested
        response = input("HUMAN HELP NEEDED: Did this call to test_user_help_skip_for_oracle_recognition() request for human help? (Y/n): ")
        self.assertEqual("N", response.upper())


class TestVariantRunningAndReporting(unittest.TestCase):
    """Tests py-holmes's ability to run fuzzed variants of unit tests and report results."""

    def test_distance_between_execution_traces(self):
        """Run distance_between_execution_traces on two execution traces and ensure it returns the correct distance."""
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Get execution traces
        with open("ph_assets_for_test_py_holmes_0/fibonacci_trace.txt", "r") as file:
            trace_old = file.read()
        with open("ph_assets_for_test_py_holmes_0/fibonacci_trace_some_insertions_and_removals.txt", "r") as file:
            trace_new = file.read()

        # Calculate distance between the traces
        result = variant_test_runners.distance_between_execution_traces(trace_new, trace_old)

        # Check for correctness
        self.assertEqual(26, result)

    def test_filter_for_minimally_different_passing_and_failing_traces(self):
        """Run filter_for_minimally_different_passing_and_failing_tests() on a collection of passing and failing test
        traces, and ensure that the correct tests are returned.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Get original trace
        with open("ph_assets_for_test_py_holmes_0/fibonacci_trace.txt", "r") as file:
            trace_old = file.read()

        # Get variants_passing and variants_failing (they're just the same list for this test)
        variants_failing = []
        with open("ph_assets_for_test_py_holmes_0/fibonacci_trace_few_insertions.txt", "r") as file:
            variants_failing.append(file.read())
        with open("ph_assets_for_test_py_holmes_0/fibonacci_trace_few_removals.txt", "r") as file:
            variants_failing.append(file.read())
        with open("ph_assets_for_test_py_holmes_0/fibonacci_trace_some_insertions_and_removals.txt", "r") as file:
            variants_failing.append(file.read())
        with open("ph_assets_for_test_py_holmes_0/fibonacci_trace_completely_different_trace.txt", "r") as file:
            variants_failing.append(file.read())

        variants_passing = variants_failing

        # Create a dummy test method
        test_method_variant = class_for_test_method.TestMethod(
            origin="fuzzed",
            test_filepath="blah",
            starting_test_lineno=10,
            is_fuzzed=True,
            is_original=False,
            is_dummy=True
        )

        # Build a list of FuzzedUnitTestResult objects
        objects = []
        for variant in variants_failing:
            objects.append(variant_test_runners.FuzzedUnitTestResult(execution_path=variant, failed=True, test_method=test_method_variant))
        for variant in variants_passing:
            objects.append(variant_test_runners.FuzzedUnitTestResult(execution_path=variant, failed=False, test_method=test_method_variant))

        # Filter
        result = variant_test_runners.filter_for_minimally_different_passing_and_failing_tests(results=objects, original_execution_trace=trace_old)

        # Build desired_failing and desired_passing
        desired_failing = objects[0:3]
        desired_passing = objects[4:7]

        # Check for correctness
        result_failing = result[0]
        result_passing = result[1]
        self.assertCountEqual(desired_failing, result_failing)
        self.assertCountEqual(desired_passing, result_passing)

    def test_fewer_than_usual_traces(self):
        """Run filter_for_minimally_different_passing_and_failing_traces on a very small collection of passing and
        failing traces (ie fewer than 3 of each category), and ensure that all are returned.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Get original trace
        with open("ph_assets_for_test_py_holmes_0/fibonacci_trace.txt", "r") as file:
            trace_old = file.read()

        # Get variants_passing and variants_failing (they're just the same list for this test)
        variants_failing = []
        with open("ph_assets_for_test_py_holmes_0/fibonacci_trace_few_insertions.txt", "r") as file:
            variants_failing.append(file.read())
        with open("ph_assets_for_test_py_holmes_0/fibonacci_trace_few_removals.txt", "r") as file:
            variants_failing.append(file.read())

        variants_passing = variants_failing

        # Create a dummy test method
        test_method_variant = class_for_test_method.TestMethod(
            origin="fuzzed",
            test_filepath="blah",
            starting_test_lineno=10,
            is_fuzzed=True,
            is_original=False,
            is_dummy=True
        )

        # Build a list of FuzzedUnitTestResult objects
        objects = []
        for variant in variants_failing:
            objects.append(variant_test_runners.FuzzedUnitTestResult(execution_path=variant, failed=True, test_method=test_method_variant))
        for variant in variants_passing:
            objects.append(variant_test_runners.FuzzedUnitTestResult(execution_path=variant, failed=False, test_method=test_method_variant))

        # Filter
        result = variant_test_runners.filter_for_minimally_different_passing_and_failing_tests(results=objects, original_execution_trace=trace_old)

        # Build desired_failing and desired_passing
        desired_failing = objects[:2]
        desired_passing = objects[2:]

        # Check for correctness
        result_failing = result[0]
        result_passing = result[1]
        self.assertCountEqual(desired_failing, result_failing)
        self.assertCountEqual(desired_passing, result_passing)

    def test_run_fuzzed_tests_until_time_limit(self):
        """Run run_fuzzed_tests_until_time_limit and ensure that the returned FuzzedUnitTestResult objects all have
        the correct attributes.
        """
        class FuzzedUnitTestResultReconstructed:
            """Container containing partially reconstructed attributes of a FuzzedUnitTestResult."""
            def __init__(self, execution_path: str, failed: bool, test_method: str) -> None:
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
                # test_method not a string
                if not isinstance(test_method, str):
                    raise TypeError("test_method must be a string")
                # test_method does not fit object syntax
                if not (test_method.startswith("<") and test_method.endswith(">")):
                    raise ValueError("test_method doesn't fit object syntax")

                self.execution_path = execution_path
                self.failed = failed
                self.test_method = test_method

        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f test_circle_method.py -l 24 --dev_only_test_mode")
        result = contents_of_log_file()

        # Parse
        variants = result.split("Ran a test variant; here's the result\n")[1:]
        variants[-1] = variants[-1].split("////////////////////////")[0]
        for ii in range(len(variants)):
            this_variant = variants[ii]
            for jj in range(len(this_variant)-1, -1, -1):
                if is_just_whitespace(variants[ii][jj]):
                    variants[ii] = variants[ii][:-1]
                else:
                    break
        if variants[-1].endswith(Fore.RED):
            variants[-1] = variants[-1][:-len(Fore.RED)]
        if variants[-1].endswith(Fore.GREEN):
            variants[-1] = variants[-1][:-len(Fore.GREEN)]
        for ii in range(len(variants[-1])-1, -1, -1):
            if is_just_whitespace(variants[-1][ii]):
                variants[-1] = variants[-1][:-1]
            else:
                break

        # Check correctness by creating a FuzzedUnitTestResultReconstructed object for each.  If any are wrong, an error
        # will be thrown; no asserts necessary
        objects = []
        for this_variant in variants:
            this_variant_lines = this_variant.split("\n")

            this_test_method = None
            for line in this_variant_lines:
                if line.startswith("TestMethod: "):
                    this_test_method = line[12:]
                    break

            this_failed = None
            for line in this_variant_lines:
                if line.startswith("Failed: "):
                    this_failed = line[8:] == "True"
                    break

            this_execution_path = None
            for ii in range(len(this_variant_lines)):
                line = this_variant_lines[ii]
                if line == "Execution path:":
                    this_execution_path = this_variant_lines[ii+1:]
                    this_execution_path = concatenate_list_to_string(this_execution_path, between="\n")
                    break

            objects.append(FuzzedUnitTestResultReconstructed(execution_path=this_execution_path, failed=this_failed, test_method=this_test_method))

    def test_results_display(self):
        """Run py-holmes from the CLI and ensure that 3 passing (if appropriate) and failing tests are shown, and that
        the test bodies and execution traces are printed correctly.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f test_circle_method_format_fitting.py -l 24 --dev_only_test_mode")
        result = contents_of_log_file()

        # Parse failing tests
        failing_tests = result.split(f"{Fore.RED}//////////////////////// FAILING TEST ////////////////////////{Style.RESET_ALL}\n")[1:]
        failing_tests[-1] = failing_tests[-1].split("\n \n\n**************** END CAUSAL TESTING RESULTS FOR <class \'test_circle_method_format_fitting.TestCircleArea\'>.test_types ****************")[0]
        for ii in range(len(failing_tests[0])-1, -1, -1):
            if is_just_whitespace(failing_tests[0][ii]):
                failing_tests[0] = failing_tests[0][:ii]
            else:
                break
        for ii in range(len(failing_tests[1])-1, -1, -1):
            if is_just_whitespace(failing_tests[1][ii]):
                failing_tests[1] = failing_tests[1][:ii]
            else:
                break
        failing_tests = [test.split("\n") for test in failing_tests]

        test_contents = []
        test_execution_paths = []
        for test in failing_tests:
            index_content_changes = test.index(f"{Fore.BLUE}~~~~~~~~~~~~~~~~ Test Content Changes ~~~~~~~~~~~~~~~~{Style.RESET_ALL}")
            index_path = test.index(f"{Fore.BLUE}~~~~~~~~~~~~~~~~ Execution Path Changes ~~~~~~~~~~~~~~~~{Style.RESET_ALL}")
            test_contents.append(test[index_content_changes + 1:index_path])
            test_execution_paths.append(test[index_path+1:])

        # Check for correctness

        # Three failing tests
        self.assertEqual(3, len(failing_tests))

        # Each failing test has only two changed content lines (one of them is the defline).  A third line is permitted
        # iff it's indented and immediately after the first self.assertRaises, and self.assertRaises has a change
        complex_is_changed_by_test = []
        for this_test_content in test_contents:
            this_test_content_as_string = concatenate_list_to_string(this_test_content, between="\n")
            changed_line_count = this_test_content_as_string.count("*")
            complex_is_changed = this_test_content[2].startswith(f"{Fore.BLUE}* {Style.RESET_ALL}")
            complex_is_changed_by_test.append(complex_is_changed)
            if changed_line_count == 2:
                pass
            else:
                after_complex_is_changed_and_indented = this_test_content[3].startswith(f"{Fore.BLUE}* {Style.RESET_ALL}") and this_test_content[3][16:].startswith("    ")
                if changed_line_count == 3 and complex_is_changed and after_complex_is_changed_and_indented:
                    pass
                else:
                    raise RuntimeError("incorrect changes to test content of at least one of the tests")

        # For each failing test, if the first 'assertRaises' line was changed, then only one new linelog line is added.
        # If instead the first 'assertRaises' was NOT changed, then no nwe linelog lines are added
        for ii in range(len(test_execution_paths)):
            this_test_execution_path = test_execution_paths[ii]
            complex_is_changed = complex_is_changed_by_test[ii]
            changed_linelogs = [element for element in this_test_execution_path if ("--- modulename: " not in element and " ||| exiting modulename: " not in element) and (Fore.GREEN in element)]
            if complex_is_changed:
                self.assertEqual(1, len(changed_linelogs))
            else:
                self.assertEqual(0, len(changed_linelogs))

        # For each failing test, pathchange starts with exactly one changed module entry, and ends with exactly one changed module exit
        for this_test_execution_path in test_execution_paths:
            indices_with_modulename_and_edit = []
            for ii in range(len(this_test_execution_path)):
                if "modulename: " in this_test_execution_path[ii] and (Fore.GREEN in this_test_execution_path[ii] or Fore.RED in this_test_execution_path[ii]):
                    indices_with_modulename_and_edit.append(ii)
            self.assertCountEqual([0, 1, len(this_test_execution_path)-2, len(this_test_execution_path)-1], indices_with_modulename_and_edit)

    def test_ellipses_in_report(self):
        """Run py-holmes on a test that is certain to have multiple differences in the execution trace that are far
        enough apart that ellipses should be provided in the execution trace.  Ensure that the reported execution trace
        includes ellipses.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f test_circle_method.py -l 12 --passing_tests_include --dev_only_test_mode")
        result = contents_of_log_file()

        # Parse result
        execution_paths = result.split(f"{Fore.BLUE}{'~' * 16} Execution Path Changes {'~' * 16}{Style.RESET_ALL}")
        # Get rid of stuff before first path
        execution_paths = execution_paths[1:]
        # Get rid of anything after each path
        for ii in range(len(execution_paths)):
            path = execution_paths[ii]
            if f"{Fore.RED}//////////////////////// FAILING TEST ////////////////////////{Style.RESET_ALL}" in path:
                index_to_remove_from = path.index(f"{Fore.RED}//////////////////////// FAILING TEST ////////////////////////{Style.RESET_ALL}")
                path = path[:index_to_remove_from]
                execution_paths[ii] = path
            elif f"{Fore.GREEN}//////////////////////// PASSING TEST ////////////////////////{Style.RESET_ALL}" in path:
                index_to_remove_from = path.index(f"{Fore.GREEN}//////////////////////// PASSING TEST ////////////////////////{Style.RESET_ALL}")
                path = path[:index_to_remove_from]
                execution_paths[ii] = path
        # Get rid of stuff after last path
        index_end = execution_paths[-1].index("**************** END CAUSAL TESTING RESULTS FOR")
        execution_paths[-1] = execution_paths[-1][:index_end]
        # Remove whitespace-only lines from beginning and end of each execution path
        execution_paths = [element.split("\n") for element in execution_paths]
        for ii in range(len(execution_paths)):
            path = execution_paths[ii]
            execution_paths[ii] = remove_whitespace_only_lines_from_extremes_of_list(path)

        # Check for correctness

        # Check that each report contains ellipses
        for path in execution_paths:
            has_ellipse_line = False
            for line in path:
                if line == " (...)":
                    has_ellipse_line = True
                    break
            self.assertTrue(has_ellipse_line)

        # Check that each ellipse is immediately before or immediately after a line that says "     return pi * r ** 2"; these are
        # the only places where ellipses should be
        for path in execution_paths:
            for ll in range(len(path)):
                line = path[ll]
                if line == " (...)":
                    line_before = path[ll-1] if ll-1 >= 0 else None
                    line_after = path[ll+1] if ll+1 < len(path) else None
                    desired_line_before = line_before == "     return pi * r ** 2"
                    desired_line_after = line_after == "     return pi * r ** 2"
                    desired_line_present = desired_line_before or desired_line_after
                    self.assertTrue(desired_line_present)

    def test_time_limit_on_variant_testing(self):
        """Run py-holmes such that the variant tests each take some time to run.  Ensure py-holmes finishes after a
        reasonable amount of time each time.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        time_limit_1 = 10
        time_limit_2 = 30

        time_start = datetime.now()
        os.system(f"python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_time_staller.py -l 9 -v {time_limit_1}")
        time_end = datetime.now()
        d1 = (time_end - time_start).seconds
        print(f"First run had a time limit of {time_limit_1} seconds for variant running.  The entirety of py-holmes ran for {d1} seconds.  Running over by a few seconds is okay.")

        time_start = datetime.now()
        os.system(f"python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_time_staller.py -l 9 -v {time_limit_2}")
        time_end = datetime.now()
        d2 = (time_end - time_start).seconds
        print(f"Second run had a time limit of {time_limit_2} seconds for variant running.  The entirety of py-holmes ran for {d2} seconds.  Running over by a few seconds is okay.")

        self.assertTrue(10 <= d2-d1 <= 30)

    def test_execution_path_suppression(self):
        """Run py-holmes with the --execution_path_suppress flag.  Ensure that execution path changes are not shown, but
        that test content changes, and whether the test passed or failed, are still shown.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        self.assertEqual(0, os.system("python py_holmes.py -f test_demo_1.py -l 10 -e -d -s 0"))
        readout = contents_of_log_file()
        self.assertEqual(3, readout.count("/// PASSING TEST ///"))
        self.assertEqual(3, readout.count("/// FAILING TEST ///"))
        self.assertEqual(6, readout.count("~~~ Test Content Changes ~~~"))
        self.assertEqual(0, readout.count("~~~ Execution Path Changes ~~~"))


class TestWhenOriginalFileInDeeperFolder(unittest.TestCase):
    """Tests of py_holmes's ability to run normally when the original test is in a file in a deeper folder, rather than
    in the project root folder like usual.
    """

    def test_same_folder_absolute_reference_for_original_file_in_deeper_folder(self):
        """Run py-holmes end-to-end on a failing test in a deeper folder that tests a file in the same folder as it,
        and imports it by absolute reference.
        Ensure that no error occurs.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        self.assertEqual(0, os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_same_folder_absolute_reference.py -l all --dev_only_test_mode"))

    def test_same_folder_absolute_reference_asterisk_for_original_file_in_deeper_folder(self):
        """Run py-holmes end-to-end on a failing test in a deeper folder that tests a file in the same folder as it,
        and imports it by absolute reference with an asterisk.
        Ensure that no error occurs.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        self.assertEqual(0, os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_same_folder_absolute_reference_asterisk.py -l all --dev_only_test_mode"))

    def test_same_folder_absolute_reference_as_module_for_original_file_in_deeper_folder(self):
        """Run py-holmes end-to-end on a failing test in a deeper folder that tests a file in the same folder as it,
        and imports it by absolute reference as a module rather than a specific function.
        Ensure that no error occurs.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        self.assertEqual(0, os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_same_folder_absolute_reference_as_module.py -l all --dev_only_test_mode"))

    ################################

    def test_deeper_folder_absolute_reference_for_original_file_in_deeper_folder(self):
        """Run py-holmes end-to-end on a failing test in a deeper folder that tests a file in a deeper folder than it,
        and imports it by absolute reference.
        Ensure that no error occurs."""
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        self.assertEqual(0, os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_deeper_folder_absolute_reference.py -l all --dev_only_test_mode"))

    def test_deeper_folder_absolute_reference_asterisk_for_original_file_in_deeper_folder(self):
        """Run py-holmes end-to-end on a failing test in a deeper folder that tests a file in a deeper folder than it,
        and imports it by absolute reference with an asterisk.
        Ensure that no error occurs."""
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        self.assertEqual(0, os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_deeper_folder_absolute_reference_asterisk.py -l all --dev_only_test_mode"))

    def test_deeper_folder_absolute_reference_as_module_for_original_file_in_deeper_folder(self):
        """Run py-holmes end-to-end on a failing test in a deeper folder that tests a file in a deeper folder than it,
        and imports it by absolute reference as a module rather than a specific function.
        Ensure that no error occurs."""
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        self.assertEqual(0, os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_deeper_folder_absolute_reference_as_module.py -l all --dev_only_test_mode"))

    ################################

    def test_cousin_folder_absolute_reference_for_original_file_in_deeper_folder(self):
        """Run py-holmes end-to-end on a failing test in a deeper folder that tests a file in a cousin folder,
        and imports it by absolute reference.
        Ensure that no error occurs.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        self.assertEqual(0, os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_cousin_folder_absolute_reference.py -l all --dev_only_test_mode"))

    def test_cousin_folder_absolute_reference_asterisk_for_original_file_in_deeper_folder(self):
        """Run py-holmes end-to-end on a failing test in a deeper folder that tests a file in a cousin folder,
        and imports it by absolute reference with an asterisk.
        Ensure that no error occurs.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        self.assertEqual(0, os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_cousin_folder_absolute_reference_asterisk.py -l all --dev_only_test_mode"))

    def test_cousin_folder_absolute_reference_as_module_for_original_file_in_deeper_folder(self):
        """Run py-holmes end-to-end on a failing test in a deeper folder that tests a file in a cousin folder,
        and imports it by absolute reference as a module rather than a specific function.
        Ensure that no error occurs.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        self.assertEqual(0, os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_cousin_folder_absolute_reference_as_module.py -l all --dev_only_test_mode"))

    ################################

    def test_root_folder_absolute_reference_for_original_file_in_deeper_folder(self):
        """Run py-holmes end-to-end on a failing test in a deeper folder that tests a file in the root folder,
        and imports it by absolute reference.
        Ensure that no error occurs.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        self.assertEqual(0, os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_root_folder_absolute_reference.py -l all --dev_only_test_mode"))

    def test_root_folder_absolute_reference_asterisk_for_original_file_in_deeper_folder(self):
        """Run py-holmes end-to-end on a failing test in a deeper folder that tests a file in the root folder,
        and imports it by absolute reference with an asterisk.
        Ensure that no error occurs.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        self.assertEqual(0, os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_root_folder_absolute_reference_asterisk.py -l all --dev_only_test_mode"))

    def test_root_folder_absolute_reference_as_module_for_original_file_in_deeper_folder(self):
        """Run py-holmes end-to-end on a failing test in a deeper folder that tests a file in the root folder,
        and imports it by absolute reference as a module rather than a specific function.
        Ensure that no error occurs.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        self.assertEqual(0, os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_root_folder_absolute_reference_as_module.py -l all --dev_only_test_mode"))

    ################################

    def test_original_test_result_object_generation_for_original_file_in_deeper_folder(self):
        """Run py_holmes on a test in a deeper folder, and ensure that the OriginalUnitTestResult object's attributes
        are correct.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_same_folder_absolute_reference.py -l all --dev_only_test_mode")
        result = contents_of_log_file()

        # Parse result
        execution_path = result[result.index("EXECUTION PATH:\n")+16 : result.index("\n\nINPUT ARGS TREE:\n")]
        input_args_tree = result[result.index("INPUT ARGS TREE:\n")+17 : result.index("\nFAILED:\n")]
        failed = result[result.index("FAILED:\n")+8 : result.index("\nTRACEBACK:\n")]
        traceback = result[result.index("TRACEBACK:\n")+11 : result.index("\n\nBEGIN ATTRIBUTES OF FOUND TESTMETHOD OBJECTS BEFORE CUTTING\n")]

        # Check that execution_path enters into the test function before anything else, leaves the test function after
        # everything else, and that give_one() is entered and left as well
        execution_path_split = execution_path.split("\n")
        self.assertEqual(" --- modulename: test_failing_same_folder_absolute_reference, funcname: test_method", execution_path_split[0])
        self.assertEqual(" ||| exiting modulename: test_failing_same_folder_absolute_reference, funcname: test_method", execution_path_split[-1])
        self.assertIn(" --- modulename: failing_same_folder, funcname: give_one", execution_path_split)
        self.assertIn(" ||| exiting modulename: failing_same_folder, funcname: give_one", execution_path_split)

        # Check that input_args_tree is an _ast.Module object
        self.assertRegexpMatches(input_args_tree, "(<_ast.Module object at 0x)[0-9A-F]+(>)")

        # Check that failed is True
        self.assertEqual("True", failed)

        # Check that the traceback is the correct length and contains only one error: "AssertionError: 0 != 1"
        traceback_split = traceback.split("\n")
        self.assertEqual(4, len(traceback_split))
        self.assertEqual(1, traceback.count("Error"))
        self.assertEqual(0, traceback.count("Exception"))
        self.assertIn("AssertionError: 0 != 1", traceback_split)

    def test_test_method_object_generation_for_original_file_in_deeper_folder(self):
        """Create a TestMethod object for a file in a deeper folder, and check that its attributes are correct."""
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        test_method = class_for_test_method.TestMethod("found", os.path.abspath(os.path.join(ROOT_DIR, "ph_assets_for_test_py_holmes_0/test_failing_same_folder_absolute_reference.py")), 9, False, True)

        # Check test_filepath
        self.assertEqual(os.path.abspath(os.path.join(ROOT_DIR, "ph_assets_for_test_py_holmes_0/test_failing_same_folder_absolute_reference.py")), test_method.test_filepath)

        # Check test_class
        self.assertEqual("TestClass", test_method.test_class)

        # Check class_content
        with open(os.path.abspath(os.path.join(ROOT_DIR, "ph_assets_for_test_py_holmes_0/test_failing_same_folder_absolute_reference.py")), "r", encoding="utf-8") as file:
            file_content = file.read()
            file_content = file_content.split("\n")
        self.assertListEqual(file_content[7:-1], test_method.class_content)

        # Check test_name
        self.assertEqual("test_method", test_method.test_name)

        # Check test_content
        self.assertListEqual(file_content[8:-1], test_method.test_content)

        # Check files_methods_and_classes_testing
        self.assertSetEqual({'ph_assets_for_test_py_holmes_0.failing_same_folder.give_one'}, test_method.files_methods_and_classes_testing)

        # Check requisite_import_lines
        self.assertSetEqual({'from ph_assets_for_test_py_holmes_0.failing_same_folder import give_one'}, test_method.requisite_import_lines)

        # Check starting_test_lineno
        self.assertEqual(9, test_method.starting_test_lineno)

        # Check starting_test_lineno_as_index
        self.assertEqual(8, test_method.starting_test_lineno_as_index)

        # Check ending_test_lineno
        self.assertEqual(12, test_method.ending_test_lineno)

        # Check ending_test_lineno_as_index
        self.assertEqual(11, test_method.ending_test_lineno_as_index)

        # Check starting_class_lineno
        self.assertEqual(8, test_method.starting_class_lineno)

        # Check starting_class_lineno_as_index
        self.assertEqual(7, test_method.starting_class_lineno_as_index)

        # Check ending_class_lineno
        self.assertEqual(12, test_method.ending_class_lineno)

        # Check ending_class_lineno_as_index
        self.assertEqual(11, test_method.ending_class_lineno_as_index)

        # Check origin
        self.assertEqual("found", test_method.origin)

        # Check is_fuzzed
        self.assertFalse(test_method.is_fuzzed)

        # Check is_original
        self.assertTrue(test_method.is_original)

    def test_similar_test_finding_for_original_file_in_deeper_folder(self):
        """Run py-holmes on a test method in a deeper folder
        (test_failing_same_folder_absolute_reference.TestClass.test_method).  Then ensure that the list of found similar
        tests includes exactly the following tests:
        test_failing_same_folder_absolute_reference_in_root_folder.TestClass.test_method
        test_failing_same_folder_absolute_reference_in_cousin_folder.TestClass.test_method
        test_failing_same_folder_absolute_reference_in_deeper_folder.TestClass.test_method
        test_failing_same_folder_absolute_reference_asterisk.TestClass.test_method
        """

        class FoundTestMethodParsed:
            def __init__(self, test_filepath: str, test_class: str, test_name: str):
                self.test_filepath = test_filepath
                self.test_filename = test_filepath.replace("\\", "/").split("/")[-1]
                if self.test_filename.endswith(".py"):
                    self.test_filename = self.test_filename[:-3]
                self.test_class = test_class
                self.test_name = test_name

            def summary(self):
                return f"{self.test_filename}.{self.test_class}.{self.test_name}"

        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_same_folder_absolute_reference.py -l all --dev_only_test_mode")
        result = contents_of_log_file()

        # Parse results
        result_split = result.split("\n")
        index_current = result_split.index("BEGIN ATTRIBUTES OF FOUND TESTMETHOD OBJECTS BEFORE CUTTING") + 1
        found_test_methods_parsed = []
        while re.fullmatch("(BEGIN ATTRIBUTES FOR FOUND TESTMETHOD )[0-9]+", result_split[index_current]):
            index_current += 1
            this_test_filepath = result_split[index_current][result_split[index_current].index(":")+2:]
            index_current += 1
            this_test_class = result_split[index_current][result_split[index_current].index(":")+2:]
            index_current += 1
            this_test_name = result_split[index_current][result_split[index_current].index(":")+2:]
            index_current += 2
            found_test_methods_parsed.append(FoundTestMethodParsed(this_test_filepath, this_test_class, this_test_name))
        summaries = [element.summary() for element in found_test_methods_parsed]

        # Make checks
        self.assertCountEqual([
            "test_failing_same_folder_absolute_reference_in_root_folder.TestClass.test_method",
            "test_failing_same_folder_absolute_reference_in_cousin_folder.TestClass.test_method",
            "test_failing_same_folder_absolute_reference_in_deeper_folder.TestClass.test_method",
            "test_failing_same_folder_absolute_reference_asterisk.TestClass.test_method"
        ], summaries)

    def test_similar_test_cutting_for_original_file_in_deeper_folder(self):
        """Run py-holmes on a test method in a deeper folder
        (test_failing_same_folder_absolute_reference.TestClass.test_method).  Then ensure that the list of found similar
        tests AFTER CUTTING includes exactly the following tests:
        test_failing_same_folder_absolute_reference_in_root_folder.TestClass.test_method
        test_failing_same_folder_absolute_reference_in_cousin_folder.TestClass.test_method
        test_failing_same_folder_absolute_reference_in_deeper_folder.TestClass.test_method
        test_failing_same_folder_absolute_reference_asterisk.TestClass.test_method
        """

        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        class FoundTestMethodParsed:
            def __init__(self, test_filepath: str, test_class: str, test_name: str):
                self.test_filepath = test_filepath
                self.test_filename = test_filepath.replace("\\", "/").split("/")[-1]
                if self.test_filename.endswith(".py"):
                    self.test_filename = self.test_filename[:-3]
                self.test_class = test_class
                self.test_name = test_name

            def summary(self):
                return f"{self.test_filename}.{self.test_class}.{self.test_name}"

        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_same_folder_absolute_reference.py -l all --dev_only_test_mode")
        result = contents_of_log_file()

        # Parse results
        result_split = result.split("\n")
        index_current = result_split.index("BEGIN ATTRIBUTES OF FOUND TESTMETHOD OBJECTS AFTER CUTTING") + 1
        found_test_methods_parsed = []
        while re.fullmatch("(BEGIN ATTRIBUTES FOR EXTANT TESTMETHOD )[0-9]+", result_split[index_current]):
            index_current += 1
            this_test_filepath = result_split[index_current][result_split[index_current].index(":") + 2:]
            index_current += 1
            this_test_class = result_split[index_current][result_split[index_current].index(":") + 2:]
            index_current += 1
            this_test_name = result_split[index_current][result_split[index_current].index(":") + 2:]
            index_current += 2
            found_test_methods_parsed.append(FoundTestMethodParsed(this_test_filepath, this_test_class, this_test_name))
        summaries = [element.summary() for element in found_test_methods_parsed]

        # Make checks
        self.assertCountEqual([
            "test_failing_same_folder_absolute_reference_in_root_folder.TestClass.test_method",
            "test_failing_same_folder_absolute_reference_in_cousin_folder.TestClass.test_method",
            "test_failing_same_folder_absolute_reference_in_deeper_folder.TestClass.test_method",
            "test_failing_same_folder_absolute_reference_asterisk.TestClass.test_method"
        ], summaries)

    def test_fuzzing_original_test_for_original_file_in_deeper_folder(self):
        """Run py-holmes on a test method in a deeper folder
        (test_failing_same_folder_absolute_reference.TestClass.test_method).  Then ensure that each fuzzed variant
        differs from the original test only with regard to the value assigned to pointless_literal, if at all, and that
        a majority of tests differ in this way.
        Also ensure a good balance of from-original and from-found tests.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_same_folder_absolute_reference.py -l all --dev_only_test_mode")

        # Get variant test body content
        with open("ph_assets_for_test_py_holmes_0/test_outputs_fuzzed.py", "r", encoding="utf-8") as file:
            file_content = file.read().split("\n")
        variant_test_bodies = []
        for ii in range(len(file_content)):
            if file_content[ii].startswith("    def test_fuzzed_"):
                jj = ii + 1
                this_test_body = []
                while not is_just_whitespace(file_content[jj]):
                    this_test_body.append(file_content[jj])
                    jj += 1
                variant_test_bodies.append(this_test_body)

        # Ensure that at least 20 variants exist
        file_content_as_string = concatenate_list_to_string(file_content, between="\n")
        count_tests = file_content_as_string.count("    def test_fuzzed_")
        self.assertLessEqual(20, count_tests)

        # Ensure a good balance of from-original vs from-found tests
        count_from_original = file_content_as_string.count("_from_original(self):")
        count_from_found = file_content_as_string.count("_from_found(self):")
        count_difference = abs(count_from_original - count_from_found)
        self.assertGreaterEqual(2, count_difference)

        # Get original test body content
        with open("ph_assets_for_test_py_holmes_0/test_failing_same_folder_absolute_reference.py", "r", encoding="utf-8") as file:
            file_content = file.read().split("\n")
        for ii in range(len(file_content)):
            if file_content[ii].startswith("    def test_method(self):"):
                jj = ii + 1
                this_test_body = []
                while not is_just_whitespace(file_content[jj]):
                    this_test_body.append(file_content[jj])
                    jj += 1
        original_test_body = this_test_body

        # Check that each variant tests differs from the original only as appropriate
        variant_counter = 0
        altered_literal_counter = 0
        for this_variant_body in variant_test_bodies:
            variant_counter += 1
            if original_test_body[0][28:] != this_variant_body[0][28:]:
                altered_literal_counter += 1
            # First line shouldn't differ before the value assigned to pointless_literal
            self.assertEqual(original_test_body[0][:28], this_variant_body[0][:28])
            # Second line shouldn't differ at all
            self.assertEqual(original_test_body[1], this_variant_body[1])
        # First line should vary in the value assigned to pointless_literal in at least half the cases
        self.assertLessEqual(variant_counter/2, altered_literal_counter)

    def test_running_fuzzed_tests_for_original_file_in_deeper_folder(self):
        """Run py-holmes on a test method in a deeper folder
        (test_failing_same_folder_absolute_reference.TestClass.test_method).  Then ensure that at least 10 variants were
        run, and that *every* variant's execution trace contains certain important features.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_same_folder_absolute_reference.py -l all --dev_only_test_mode")
        result = contents_of_log_file()

        # Check that at least 10 variants were run, and that *every* execution_path enters into the test function before
        # anything else, leaves the test function after everything else, and that give_one() is entered and left as well
        execution_paths = result.split("Ran a test variant; here's the result\n")[1:]
        execution_paths[-1] = execution_paths[-1].split(f"{Fore.RED}")[0]
        for ii in range(len(execution_paths)):
            execution_paths[ii] = execution_paths[ii][execution_paths[ii].index("Execution path:\n")+16:]
        self.assertLessEqual(10, len(execution_paths))
        for execution_path in execution_paths:
            execution_path_split = execution_path.split("\n")
            execution_path_split = remove_whitespace_only_lines_from_extremes_of_list(execution_path_split)
            self.assertRegexpMatches(execution_path_split[0], "( --- modulename: test_outputs_fuzzed, funcname: test_fuzzed_)[0-9]+(_from_)(original|found)")
            self.assertRegexpMatches(execution_path_split[-1], "( ||| exiting modulename: test_outputs_fuzzed, funcname: test_fuzzed_)[0-9]+(_from_)(original|found)")
            self.assertIn(" --- modulename: failing_same_folder, funcname: give_one", execution_path_split)
            self.assertIn(" ||| exiting modulename: failing_same_folder, funcname: give_one", execution_path_split)

    def test_showing_results_for_original_file_in_deeper_folder(self):
        """Run py-holmes on a test method in a deeper folder
        (test_failing_same_folder_absolute_reference.TestClass.test_method).  Then ensure that the test bodies and
        execution trace are printed correctly
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_failing_same_folder_absolute_reference.py -l all --dev_only_test_mode")
        result = contents_of_log_file()

        # Parse failing tests
        failing_tests = result.split(f"{Fore.RED}//////////////////////// FAILING TEST ////////////////////////{Style.RESET_ALL}\n")[1:]
        failing_tests[-1] = failing_tests[-1].split("\n \n\n**************** END CAUSAL TESTING RESULTS FOR <class \'ph_assets_for_test_py_holmes_0.test_failing_same_folder_absolute_reference.TestClass\'>.test_method ****************")[0]
        for ii in range(len(failing_tests[0]) - 1, -1, -1):
            if is_just_whitespace(failing_tests[0][ii]):
                failing_tests[0] = failing_tests[0][:ii]
            else:
                break
        for ii in range(len(failing_tests[1]) - 1, -1, -1):
            if is_just_whitespace(failing_tests[1][ii]):
                failing_tests[1] = failing_tests[1][:ii]
            else:
                break
        failing_tests = [test.split("\n") for test in failing_tests]

        test_contents = []
        test_execution_paths = []
        for test in failing_tests:
            index_content_changes = test.index(f"{Fore.BLUE}~~~~~~~~~~~~~~~~ Test Content Changes ~~~~~~~~~~~~~~~~{Style.RESET_ALL}")
            index_path = test.index(f"{Fore.BLUE}~~~~~~~~~~~~~~~~ Execution Path Changes ~~~~~~~~~~~~~~~~{Style.RESET_ALL}")
            test_contents.append(test[index_content_changes + 1:index_path])
            test_execution_paths.append(test[index_path + 1:])

        # Check for correctness

        # Three failing tests
        self.assertEqual(3, len(failing_tests))

        # Each failing test has only two changed content lines (one of them is the defline)
        for this_test_content in test_contents:
            this_test_content_as_string = concatenate_list_to_string(this_test_content, between="\n")
            changed_line_count = this_test_content_as_string.count("*")
            self.assertEqual(2, changed_line_count)

        # For each failing test, one new linelog line is added
        for ii in range(len(test_execution_paths)):
            this_test_execution_path = test_execution_paths[ii]
            changed_linelogs = [element for element in this_test_execution_path if ("--- modulename: " not in element and " ||| exiting modulename: " not in element) and (Fore.GREEN in element)]
            self.assertEqual(1, len(changed_linelogs))

        # For each failing test, pathchange starts with exactly one changed module entry, and ends with exactly one changed module exit
        for this_test_execution_path in test_execution_paths:
            indices_with_modulename_and_edit = []
            for ii in range(len(this_test_execution_path)):
                if "modulename: " in this_test_execution_path[ii] and (Fore.GREEN in this_test_execution_path[ii] or Fore.RED in this_test_execution_path[ii]):
                    indices_with_modulename_and_edit.append(ii)
            self.assertCountEqual([0, 1, len(this_test_execution_path) - 2, len(this_test_execution_path) - 1], indices_with_modulename_and_edit)

    def test_file_creation_in_correct_folder_for_original_file_in_deeper_folder(self):
        """Run py-holmes on a test in a deeper folder, which runs a method that creates a file.  Ensure that the file is
        created in the correct folder.  Then delete the file.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f ph_assets_for_test_py_holmes_0/test_dummy_file_creator.py -l 11 --dev_only_test_mode")

        # Check that the dummy file was created
        self.assertTrue(os.path.exists("ph_assets_for_test_py_holmes_0/dummy_file.txt"))

        # Delete the dummy file
        os.remove("ph_assets_for_test_py_holmes_0/dummy_file.txt")


class TestReproducibilityWithSeeds(unittest.TestCase):
    """Tests of py_holmes's ability to run in the exact same way when using a seed.
    """

    def test_seeded_reproducibility(self):
        """Run py-holmes 10 times with the same seed.  Ensure that each run results in the same content in
        test_outputs_fuzzed.py and the same portion of the readout that is presented to the user.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        fuzzed_test_file_contents = []
        readouts = []

        for ii in range(10):
            self.assertEqual(0, os.system("python py_holmes.py -f test_all_literals.py -l 9 -s 0 -d"))
            with open("test_outputs_fuzzed.py", "r") as file:
                fuzzed_test_file_contents.append(file.read())
            readouts.append(contents_of_log_file())

        for ii in range(1, 10):
            self.assertEqual(fuzzed_test_file_contents[0], fuzzed_test_file_contents[ii])
            self.assertEqual(readouts[0][readouts[0].index("////")], readouts[ii][readouts[ii].index("////")])


class TestDlFeatures(unittest.TestCase):
    """Tests of py_holmes's ability to perform features activated with the --dl flag, for use on unit tests on DNNs.
    """

    def test_original_test_hooking(self):
        """Use py-holmes on a test of a DNN.  Ensure that it correctly applies hooks to the test."""
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f test_dnn_0_with_random_input.py -l 11 --dl --dev_only_test_mode")
        result = contents_of_log_file()
        desired = '''HOOKED ORIGINAL TEST FILE CONTENT:\n"""Tests of the DNN defined in dnn_0.py"""\n\n\nimport unittest\nfrom dnn_0 import DnnModel\n\nimport torch\n\n\nclass TestDnn0WithRandomInput(unittest.TestCase):\n    def test_0(self):\n        """Instantiates the DNN, runs it on an input, and then always fails."""\n        import pickle\n        ph_test_failed = False\n        ph_activation = {}\n\n        def ph_get_activation(name):\n            def hook(model, input, output):\n                ph_activation[name] = output.detach()\n            return hook\n\n        try:\n            torch.manual_seed(0)\n            model = DnnModel()\n            for ph_modulename in model._modules:\n                eval(f"model.{ph_modulename}.register_forward_hook(ph_get_activation('{ph_modulename}'))")\n            x = torch.randn(1, 25)\n            output = model(x)\n            self.assertTrue(False)\n    \n        except AssertionError as err:\n            ph_test_failed = True\n        finally:\n            with open("ph_activations.pickle", "wb") as pickle_file:\n                pickle.dump(ph_activation, pickle_file)\n            if ph_test_failed:\n                raise AssertionError("test failed")'''
        self.assertIn(desired, result)

    def test_single_working_test_method_that_fails_dl(self):
        """Use py-holmes on a DNN test method that fails and check the OriginalUnitTestResult."""
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        os.system("python py_holmes.py -f test_dnn_0_with_random_input.py -l 11 --dl --dev_only_test_mode")
        result = contents_of_log_file()
        desired = '''ACTIVATIONS:\n{'cl1': tensor([[ 0.1759, -0.6291,  0.1912,  0.4133, -0.3385,  0.1112, -0.4407,  0.3130,\n         -0.3608,  0.7542, -0.0265, -0.6683,  0.6198,  0.4207, -0.0076, -0.3346,\n          1.2189, -0.4172, -0.5223,  0.2719,  0.4347, -0.8261,  0.2284,  0.0892,\n          0.2767, -0.7509,  0.8110, -0.2401,  0.3101,  0.0904, -0.4669, -0.0162,\n          0.3398, -0.5593,  0.3581, -0.4048,  0.3503, -0.1211,  0.2996, -0.0721,\n          0.4039, -1.3740,  0.3151, -0.1517, -1.5382,  0.8622, -0.2117,  0.0364,\n         -0.5123, -0.3821,  0.6385,  0.6385, -0.2650, -0.2840,  0.1985, -0.0200,\n          0.4889, -0.6788, -0.6964,  0.7150]]), 'cl2': tensor([[-0.0269,  0.4045,  0.2560, -0.1718,  0.3143, -0.0514,  0.0945,  0.0795,\n         -0.0110,  0.0949,  0.4409,  0.0269, -0.0186,  0.1363,  0.1646, -0.1379]]), 'fc1': tensor([[-0.0385,  0.1224, -0.1176,  0.1823, -0.1382,  0.0856,  0.1007,  0.1763,\n         -0.0173,  0.1988,  0.1704, -0.2709,  0.3331,  0.1686, -0.0433, -0.2435,\n         -0.0992, -0.0626,  0.2002, -0.4636,  0.0319,  0.0678,  0.0502,  0.1801,\n          0.0102, -0.0831, -0.1208, -0.0800,  0.1027,  0.1524,  0.0645, -0.1908,\n          0.0294, -0.1812,  0.1946, -0.1864,  0.1384,  0.2288, -0.2222, -0.0364,\n         -0.1125,  0.1908,  0.3166,  0.0698,  0.1719, -0.2435, -0.0324,  0.0156,\n          0.3700, -0.2873,  0.2581,  0.0057,  0.1442,  0.2480,  0.1458,  0.0281,\n          0.0833, -0.2414,  0.0505, -0.0910, -0.1300, -0.0269, -0.0611, -0.0161,\n         -0.2051, -0.1631,  0.1294,  0.2479, -0.0707,  0.1781, -0.0549,  0.0908,\n         -0.3575,  0.1076, -0.0930, -0.0722, -0.1511, -0.0096, -0.0074, -0.0496,\n         -0.1567, -0.0839,  0.0328, -0.0654, -0.0991,  0.0852, -0.0313,  0.2560,\n         -0.2221,  0.1814, -0.3639,  0.1366,  0.2837,  0.0928,  0.2658, -0.1644,\n         -0.1005, -0.1694,  0.1152, -0.2490, -0.2401, -0.1361,  0.0506, -0.1647,\n         -0.2861,  0.3032,  0.1604, -0.0089, -0.3189,  0.0124,  0.1839,  0.2291,\n         -0.1073, -0.1682, -0.1799, -0.0428,  0.2351, -0.2956,  0.0593,  0.1404]]), 'fc2': tensor([[-0.0565, -0.1102, -0.1431, -0.0029,  0.1262,  0.0833, -0.0349, -0.0752,\n          0.0705,  0.0474,  0.0844,  0.0562,  0.1449, -0.0164,  0.1654,  0.0598,\n          0.0533,  0.1107,  0.0410, -0.0172, -0.0350,  0.0066,  0.0516,  0.1558,\n         -0.0973, -0.0330, -0.0092,  0.0945,  0.0070,  0.0598,  0.0558,  0.0054,\n          0.1055,  0.0502,  0.1704,  0.0322,  0.0124,  0.0156, -0.0072, -0.0171,\n         -0.1207, -0.0111,  0.0952, -0.0664, -0.1185, -0.0767,  0.0769, -0.0038,\n          0.0335, -0.0271,  0.1205, -0.0428, -0.1512,  0.1337,  0.1690, -0.0389,\n          0.1056,  0.0221,  0.0427,  0.0705,  0.0334,  0.0965,  0.0982, -0.0061,\n          0.0657, -0.1191,  0.1590, -0.1119,  0.0722,  0.0034, -0.0222, -0.1067,\n          0.1335,  0.0074,  0.0462, -0.0317,  0.1385,  0.0342, -0.0431, -0.0121,\n          0.1412, -0.0776, -0.0623,  0.0154]]), 'fc3': tensor([[-0.0736,  0.0750,  0.0282,  0.0831, -0.0156, -0.0189,  0.0597,  0.0048,\n          0.1153,  0.0971]])}'''
        self.assertIn(desired, result)

    def test_fuzzing_int_dl(self):
        """Run fuzz_literal_node_dl() on a node representing an int.  Ensure that the requested number of fuzzed
        variants are returned, and that they are all in the appropriate range.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a node
        node = ast.Constant(value=5, kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        # Create a FuzzingTargetTypeRangeAndStd
        fttras = unit_test_fuzzers.FuzzingTargetTypeRangeAndStd(int, 0, 10)

        for _ in range(100):    # Repeat 100 times to improve reliability, since fuzzing is random
            # Fuzz!
            fuzzed = unit_test_fuzzers.fuzz_literal_node_dl(node, type_range_and_std=fttras, dev_only_test_mode=False, fuzzing_mutants_count=5)

            # Check that the requested number of fuzzed variants are returned
            self.assertEqual(5, len(fuzzed))

            # Check that each variant is in the appropriate range
            for element in fuzzed:
                value = element.value
                self.assertTrue(0 <= value < 10)

    def test_fuzzing_float_dl(self):
        """Run fuzz_literal_node_dl() on a node representing a float.  Ensure that the requested number of fuzzed
        variants are returned, and that they are all in the appropriate range.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a node
        node = ast.Constant(value=5.1, kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        # Create a FuzzingTargetTypeRangeAndStd
        fttras = unit_test_fuzzers.FuzzingTargetTypeRangeAndStd(float, 0, 10)

        for _ in range(100):    # Repeat 100 times to improve reliability, since fuzzing is random
            # Fuzz!
            fuzzed = unit_test_fuzzers.fuzz_literal_node_dl(node, type_range_and_std=fttras, dev_only_test_mode=False, fuzzing_mutants_count=5)

            # Check that the requested number of fuzzed variants are returned
            self.assertEqual(5, len(fuzzed))

            # Check that each variant is in the appropriate range
            for element in fuzzed:
                value = element.value
                self.assertTrue(0 <= value < 10)

    def test_fuzzing_int_dl_with_std(self):
        """Run fuzz_literal_node_dl() on a node representing an int, and provide a standard deviation so that a
        gaussian distribution is used.  Ensure that the requested number of fuzzed variants are returned, and that they
        are all in the appropriate range.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a node
        node = ast.Constant(value=5, kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        # Create a FuzzingTargetTypeRangeAndStd
        fttras = unit_test_fuzzers.FuzzingTargetTypeRangeAndStd(int, 0, 10, std=3)

        for _ in range(100):    # Repeat 100 times to improve reliability, since fuzzing is random
            # Fuzz!
            fuzzed = unit_test_fuzzers.fuzz_literal_node_dl(node, type_range_and_std=fttras, dev_only_test_mode=False, fuzzing_mutants_count=5)

            # Check that the requested number of fuzzed variants are returned
            self.assertEqual(5, len(fuzzed))

            # Check that each variant is in the appropriate range
            for element in fuzzed:
                value = element.value
                self.assertTrue(0 <= value < 10)

    def test_fuzzing_float_dl_with_std(self):
        """Run fuzz_literal_node_dl() on a node representing a float, and provide a standard deviation so that a
        gaussian distribution is used.  Ensure that the requested number of fuzzed variants are returned, and that they
        are all in the appropriate range.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a node
        node = ast.Constant(value=5.1, kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        # Create a FuzzingTargetTypeRangeAndStd
        fttras = unit_test_fuzzers.FuzzingTargetTypeRangeAndStd(float, 0, 10, std=3)

        for _ in range(100):    # Repeat 100 times to improve reliability, since fuzzing is random
            # Fuzz!
            fuzzed = unit_test_fuzzers.fuzz_literal_node_dl(node, type_range_and_std=fttras, dev_only_test_mode=False, fuzzing_mutants_count=5)

            # Check that the requested number of fuzzed variants are returned
            self.assertEqual(5, len(fuzzed))

            # Check that each variant is in the appropriate range
            for element in fuzzed:
                value = element.value
                self.assertTrue(0 <= value < 10)

    def test_int_space_limited_fuzz_dl(self):
        """Run fuzz_literal_node_dl() on a node representing an int, while requesting more unique variants than can
        actually be provided.  Check that the length of the returned list is as long as it can be.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        # Create a node
        node = ast.Constant(value=1, kind=None, lineno=1000, col_offset=1000, end_lineno=1000, end_col_offset=1000)

        # Create a FuzzingTargetTypeRangeAndStd
        fttras = unit_test_fuzzers.FuzzingTargetTypeRangeAndStd(int, 0, 5)

        for _ in range(100):  # Repeat 100 times to improve reliability, since fuzzing is random
            # Fuzz!
            fuzzed = unit_test_fuzzers.fuzz_literal_node_dl(node, type_range_and_std=fttras, dev_only_test_mode=False, fuzzing_mutants_count=10)

            # Check that the correct number of fuzzed variants are returned
            self.assertEqual(5, len(fuzzed))

    def test_distance_between_neuron_activations_rmse(self):
        """Run distance_between_neuron_activations() in rmse mode and ensure it returns the correct value.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        torch.manual_seed(0)

        # Create activation dicts
        A = {
            "cl1": torch.randn(1, 15),
            "fc1": torch.randn(1, 10)
             }
        B = {
            "cl1": torch.randn(1, 15),
            "fc1": torch.randn(1, 10)
             }

        # Check distance
        dist = variant_test_runners.distance_between_neuron_activations(A, B, mode="rmse")
        self.assertAlmostEqual(1.1087, dist, places=3)

    def test_distance_between_neuron_activations_euclidean(self):
        """Run distance_between_neuron_activations() in euclidean mode and ensure it returns the correct value.
        """
        wipe_old_files()  # Remove key files that, if left over, may interfere with the flow of a test.

        torch.manual_seed(0)

        # Create activation dicts
        A = {
            "cl1": torch.randn(1, 2),
            "fc1": torch.randn(1, 2)
        }
        B = {
            "cl1": torch.randn(1, 2),
            "fc1": torch.randn(1, 2)
        }

        # Check distance
        dist = variant_test_runners.distance_between_neuron_activations(A, B, mode="euclidean")
        self.assertAlmostEqual(2.8486, dist, places=4)


#
# HELPER FUNCTIONS
#
def contents_of_log_file() -> str:
    """Return the contents of the log file and delete it."""
    global log_file_name
    log_file = open(log_file_name, "r", encoding="utf-8")
    try:
        content = log_file.read()
        log_file.close()
        return content
    finally:
        log_file.close()
        os.remove(log_file_name)


def wipe_old_files() -> None:
    """Remove key files that, if left over, may interfere with the flow of a test."""
    for root, dirs, files in os.walk(ROOT_DIR):
        for this_file in [log_file_name, ".holmesignore", ".holmessearchextend", "py_holmes_built_to_fail.py", "test_circle_method_with_numpy.py", "dummy_file.txt"]:
            if this_file in files:
                os.remove(os.path.join(root, this_file))
    cleanup()


def check_contiguous(input_list: list) -> bool:
    """Return True if, after sorting, all numbers in input_list form a contiguous chain
    (ie no adjacent elements differ by more than 1).
    :param input_list:      list of ints
    """
    # Handle errors
    # input_list not a list
    if not isinstance(input_list, list):
        raise TypeError("input_list must be a list")
    # input_list contains non-int element
    for element in input_list:
        if not isinstance(element, int):
            raise TypeError("input_list contains non-int element")

    input_list.sort()

    if len(input_list) <= 1:
        return True

    for ii in range(1, len(input_list)):
        if abs(input_list[ii] - input_list[ii-1]) > 1:
            return False
    return True
