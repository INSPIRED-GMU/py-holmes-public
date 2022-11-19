"""Layer that can simply be run on top of unit tests.
Based on input from the user, either find all failing test cases in a file, or check if single test case fails.
For all failing tests, print results of causal testing for that test.

This file should be called from the command line along with the -f or --file flag, followed by the path of a test
file to run causal testing on, and a -l or --line flag, followed by either "all" or a
sequence of line numbers for test cases to run, separated by spaces.  The first line of the unit test file is line 1,
not line 0.

Here are some example command line calls:

python py_holmes.py -f my_test.py -l all
python py_holmes.py -f my_test.py --line all
python py_holmes.py --file my_test.py -l 2 43 109
python py_holmes.py --file my_test.py -l 2 43 109

Similarly, if the file containing your unit tests contains a mixture of tabs and spaces for indentation, and your tabs
are not equivalent to 4 spaces, you should use the --tatosp or -t flag, to indicate how many spaces a tab represents.
For example, if your tabs are equivalent to 2 spaces, you might call:
python py_holmes.py -f my_test.py -l all -t 2
The default value of tatosp is 4.

If you have any files for which you would like causal testing NOT to be run when these files
are responsible for failing tests, it is recommended that you name these files in a .holmesignore file (just like
you would create a .gitignore).  This file should be in the top level of your project folder.  Causal testing may be
performed without this file but may incur warnings.  Begin a line in .holmesignore with / to create an absolute
filepath.  Your test module will automatically be added to .holmesignore if it is not already covered, but failures
that originate in it will still be caught.

If your project involves any files not found in the project folder, interpreter folder, or default Python install
location for our OS, it is recommended that you name these files in a .holmessearchextend file (same syntax as a
.gitignore).  This file should be in the top level of your project folder.  Begin a lines in .holmessearchextend with /
to create an absolute filepath.

Ensure that all of the unit test files in your project either begin or end with the word "test", and that no other files
in your project begin or end this way.

Your uppermost project folder should not contain or be contained by the default Python install folder for your operating
system.  Your uppermost project folder may contain the folder of the Python executable you're using, but your project
folder must not be contained by it.

In accordance with PEP 8 E401, no file should import more than one module on the same line.
For example, "import math, random" is not acceptable, but "from math import sin, cos" is acceptable.

In accordance with PEP 8, no file should use relative imports.  As an additional restriction, explicit relative imports
are not permitted either.  Only absolute imports are permitted.

No user-written method should have its definition line span more than one row in the file.

This module is designed for use with the unittest module, not the pytest package.

Inside all user-written unittest classes, for all calls to self.assert*(), where * is Equal, NotEqual, etc, if there is
an oracle (ie expected) argument, then that/those oracle argument(s) should be in (a) specific position(s).
For example, self.assertEqual(0, my_program()) is valid, but self.assertEqual(my_program(), 0) is not.
Here are the positional oracle rules by assert call:
CLASS 1: The exact list of self.assert*() functions where the oracle should take the first position is as follows:
self.assertEqual()
self.assertNotEqual()
self.assertIs()
self.assertIsNot()
self.assertAlmostEqual()
self.assertNotAlmostEqual()
self.assertGreater()
self.assertGreaterEqual()
self.assertLess()
self.assertLessEqual()
self.assertCountEqual()
self.assertMultiLineEqual()
self.assertSequenceEqual()
self.assertListEqual()
self.assertTupleEqual()
self.assertSetEqual()
self.assertDictEqual()
CLASS 2: For these other self.assert*() functions, have your oracle be whichever position argument you like, based on
your needs.  In this category, py-holmes will treat the argument with fewer variables as the oracle node.  In the case
of a tie, it will ask for the user to manually indicate which is the oracle at runtime.
self.assertIn()
self.assertNotIn()
self.assertRegexpMatches()
self.assertNotRegexpMatches()
For these other self.assert*() functions, all arguments are considered oracle arguments:
self.assertRaisesRegexp()
self.assertWarnsRegex()
self.assertLogs()
CLASS 3: All positions are considered oracle arguments
self.assertRaisesRegexp()
self.assertWarnsRegex()
self.assertLogs()
CLASS 4: No positions are oracles
self.assertTrue().  Reason: The oracle is in the method name; it's okay to fuzz arguments
self.assertFalse().  Reason: The oracle is in the method name; it's okay to fuzz arguments
self.assertIsNone().  Reason: The oracle is in the method name; it's okay to fuzz arguments
self.assertIsNotNone().  Reason: The oracle is in the method name; it's okay to fuzz arguments
self.assertIsInstance().  Reason: The oracle is in the method name plus the instance.  Neither are literals or determined by literals, so neither are fuzzed.
self.assertNotIsInstance().  Reason: The oracle is in the method name plus the instance.  Neither are literals or determined by literals, so neither are fuzzed.
self.assertRaises().  Reason: The oracle is in the method name plus the exception type.  Neither are literals or determined by literals, so neither are fuzzed.
self.assertWarns().  Reason: The oracle is in the method name plus the exception type.  Neither are literals or determined by literals, so neither are fuzzed.

Your project should not contain files with any of the following names:
test_outputs_fuzzed.py

If you wish to perform causal testing even if your test passes, then include the -p (or --passing_tests_include) flag.

If you wish to manually provide character palettes for string fuzzing, rather than have py-holmes attempt to infer them,
then include the -c or --character_palette_manual flag.  If you do, then py-holmes will prompt you to provide these
palettes when it is ready for them.

Multiple runtimes of py-holmes cannot be run in parallel, because of the way it creates and reads temporary files.
"""


#
# IMPORTS
#
# Written for this project
from ph_variable_sharing.shared_variables import initialize
from ph_log_writing.writers import *
from ph_basic_processing.parsers import strip_custom, matches_an_ignore_pattern, index_of_last_substring_in_string
from ph_basic_processing.scrapers_for_holmesignore_and_holmessearchextend import append_root_and_add_to_holmesignore
from ph_original_test_result_generation.ph_original_test_running.original_test_runners import get_unit_test_result, build_and_run_test_suite  # We must import build_and_run_test_suite here so that tracer.run() can access it
from ph_original_test_result_generation.ph_fault_assessment.execution_trace_fault_assessers import user_at_fault
from ph_causal_testing.causal_testers import run_causal_testing
from ph_causal_testing.variant_test_runners import build_and_run_fuzzed_test_suite  # We must import build_and_run_fuzzed_test_suite here so that tracer.run() can access it
from ph_basic_processing.cleanup import cleanup

# Other modules/packages
import argparse
from warnings import warn
from os import path
from sys import platform


#
# MAIN SCRIPT
#
# If in dev-only test mode, create a logger using this thread: https://stackoverflow.com/questions/47325506/making-python-loggers-log-all-stdout-and-stderr-messages
if "-d" in sys.argv or "--dev_only_test_mode" in sys.argv:
    logger = writer()
    sys.stdout = logger
    sys.stderr = logger

if __name__ == "__main__":
    # Remove leftover files from any previous runs
    cleanup()
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run causal testing on unit tests")
    parser.add_argument("--file", "-f", action="store", nargs=1, type=str, required=True, help="Filepath of the unit test to be used", dest="test_module_filepath")
    parser.add_argument("--lines", "-l", action="store", nargs="+", default="all", type=str, required=False, help="Line numbers of test case methods to be run, separated by spaces, or use 'all' to run all test cases in the file", dest="line_numbers_to_test")
    parser.add_argument("--tatosp", "-t", action="store", nargs=1, type=int, required=False, default=4, help="Number of spaces of indentation equivalent to one tab in unit test file (default is 4)", dest="tatosp")
    parser.add_argument("--dev_only_test_mode", "-d", action="store_true", required=False, default=False, help="Produce a log of the most recent run and print additional information, for testing during the development of py_holmes itself", dest="dev_only_test_mode")
    parser.add_argument("--passing_tests_include", "-p", action="store_true", required=False, default=False, help="Run causal testing even if all tests pass", dest="still_run_causal_testing_on_passing_tests")
    parser.add_argument("--character_palette_manual", "-c", action="store_true", required=False, default=False, help="Have py-holmes prompt you to provide character palettes for fuzzing, rather than it attempting to infer them", dest="take_manual_characters_for_fuzzing")
    parser.add_argument("--variant_testing_time_limit_seconds", "-v", action="store", nargs=1, type=int, required=False, default=60, help="Time limit for variant test running; after this much time has elapsed, no more variant test runs will be initiated (default is 60)", dest="variant_testing_time_limit_seconds")
    parser.add_argument("--user_help_skip", "-u", action="store_true", required=False, default=False, help="Skip asking for human help with determining which argument is an oracle when it's unclear; just guess blindly instead", dest="user_help_skip")
    parser.add_argument("--num_test_variants", "-n", action="store", nargs=1, type=int, required=False, default=50, help="Number of fuzzed test variants to attempt to generate (default is 50)", dest="num_test_variants")

    args = parser.parse_args()
    test_module_filepath = args.test_module_filepath[0]
    line_numbers_to_test = args.line_numbers_to_test
    temp_tatosp = args.tatosp
    if isinstance(temp_tatosp, int):
        spaces_per_tab = temp_tatosp
    else:
        spaces_per_tab = temp_tatosp[0]
    temp_num_test_variants = args.num_test_variants
    if isinstance(temp_num_test_variants, int):
        num_test_variants = temp_num_test_variants
    else:
        num_test_variants = temp_num_test_variants[0]
    dev_only_test_mode = args.dev_only_test_mode
    user_help_skip = args.user_help_skip
    still_run_causal_testing_on_passing_tests = args.still_run_causal_testing_on_passing_tests
    take_manual_characters_for_fuzzing = args.take_manual_characters_for_fuzzing
    variant_testing_time_limit_seconds = args.variant_testing_time_limit_seconds
    if not isinstance(variant_testing_time_limit_seconds, int):
        variant_testing_time_limit_seconds = variant_testing_time_limit_seconds[0]

    # Remove quotes surrounding test_module_filepath, if any
    while len(test_module_filepath) > 1 and ((test_module_filepath.startswith("'") and test_module_filepath.endswith("'")) or (test_module_filepath.startswith('"') and test_module_filepath.endswith('"'))):
        test_module_filepath = test_module_filepath[1:-1]

    # Add .py extension to test_module_filepath if it isn't already there
    if not test_module_filepath.endswith(".py"):
        test_module_filepath = test_module_filepath + ".py"

    # Change test_module_filepath to UNIX-style or DOS-style, as is appropriate for the operating system
    if platform in ["darwin", "linux"]:
        test_module_filepath = test_module_filepath.replace("\\", "/")
        folder_delimiter = "/"
    elif platform in ["win32", "win64"]:
        test_module_filepath = test_module_filepath.replace("/", "\\")
        folder_delimiter = "\\"
    else:
        raise RuntimeError("Unfamiliar operating system. Don't know the default folder separation character (eg /, \\)for this OS")

    # From test_module_filepath, get filename and path_to_file
    filename = test_module_filepath.split(folder_delimiter)[-1]
    path_to_file = test_module_filepath[:-len(filename)]    # Relative to project root.  Contains only folders; does not include the file itself at the end

    # Get a version of test_module_filepath with no leading directories and with no file extension.
    # In other words, just the filename without a file extension.
    test_module_name = test_module_filepath[:-3]
    final_dir_character_index_forward_slash = -1
    final_dir_character_index_backslash = -1
    try:
        final_dir_character_index_forward_slash = index_of_last_substring_in_string(test_module_name, "/")
    except ValueError:
        pass
    try:
        final_dir_character_index_backslash = index_of_last_substring_in_string(test_module_name, "\\")
    except ValueError:
        pass
    final_dir_character_index = max(final_dir_character_index_forward_slash, final_dir_character_index_backslash)
    test_module_name = test_module_name[final_dir_character_index+1:]

    # Handle incorrect input args not automatically handled by the argparse module:
    # tatosp not positive
    if spaces_per_tab <= 0:
        raise ValueError("--tatosp (aka -t) must be positive; cannot have tabs equivalent to a non-positive number of spaces")
    # variant_testing_time_limit_seconds not positive
    if variant_testing_time_limit_seconds <= 0:
        raise ValueError("--variant_testing_time_limit_seconds (aka -v) must be positive")
    # num_test_variants not positive
    if num_test_variants <= 0:
        raise ValueError("--num_test_variants (aka -n) must be positive")

    # Based on user input, run either all tests or a set number of tests:
    test_module = open(test_module_filepath, "r", encoding="utf-8")
    try:
        test_module_content = test_module.readlines()
    finally:
        test_module.close()
    # Strip leading tabs and spaces from all content
    for ll in range(len(test_module_content)):
        test_module_content[ll] = strip_custom(test_module_content[ll], ["\t", " "], "head")

    # Handle errors
    # File does not contain a subclass of the unittest class, or does not contain a test method
    contains_unittest_class = False
    contains_test_method = False
    for entry in test_module_content:
        if strip_custom(entry, ["\t", " "], "head")[:6] == "class " and ("unittest" in entry) or ("TestCase" in entry):
            contains_unittest_class = True
        if strip_custom(entry, ["\t", " "], "head")[:8] == "def test":
            contains_test_method = True
    if not contains_unittest_class:
        raise ValueError(
            "The file requested by the user contains no classes for unit testing (ie classes which are subclasses of the unittest class)")
    if not contains_test_method:
        raise ValueError("The file requested by the user contains no test methods")

    # Share important variables with all files
    initialize(file_in=test_module_filepath, lines_in=line_numbers_to_test, tatosp_in=spaces_per_tab, dev_only_test_mode_in=dev_only_test_mode, still_run_causal_testing_on_passing_tests_in=still_run_causal_testing_on_passing_tests, variant_testing_time_limit_seconds_in=variant_testing_time_limit_seconds, user_help_skip_in=user_help_skip, num_test_variants_in=num_test_variants)

    # Add the user's test file to .holmesignore, if it isn't there already.  We must add the user's unittest file to .holmesignore here.  This is so that the holmesignore status of its callees can actually matter.  Without the user's unittest file being in .holmesignore, all callees trigger failures, even if they're in holmesignore themselves, because the unittest file is not.
    project_dir = path.dirname(path.abspath(__file__))
    if not matches_an_ignore_pattern(path.abspath(project_dir + "/" + test_module_filepath)):
        append_root_and_add_to_holmesignore(test_module_filepath)

    if "all" in line_numbers_to_test:
        # Run causal testing on all failing tests in the module
        failed_test_encountered_user_fault = False  # This gets set to true if a failed test is encountered and the user is at fault
        for ll in range(len(test_module_content)):
            if strip_custom(test_module_content[ll], ["\t", " "], "head")[0:8] == "def test":     # If this is the start of a unit test definition:
                # Run the test, and if it fails due to the user's fault (ie some failure in a "call descendant" of the user's test file), run causal testing on it
                original_test_result = get_unit_test_result(test_module_filepath, filename, ll+1)
                if original_test_result.failed:
                    if user_at_fault(original_test_result.execution_path, original_test_result.trace_indices_descended_from_non_ignored_user_code, test_module_name, original_test_result.involved_user_and_py_holmes_modules):    # If the user's test is at fault:
                        failed_test_encountered_user_fault = True
                        run_causal_testing(original_test_result, dev_only_test_mode, take_manual_characters_for_fuzzing)
                    else:   # If the user isn't at fault:
                        warn(f"Test on line {str(ll+1)} failed but not due to a fault in the user's test or any of its call descendants.  Traceback is as follows:\n" + original_test_result.traceback)
                        if still_run_causal_testing_on_passing_tests:
                            print(f"Nonetheless running causal testing by user request.")
                            run_causal_testing(original_test_result, dev_only_test_mode, take_manual_characters_for_fuzzing)
                elif still_run_causal_testing_on_passing_tests:     # If the test passed but the user wants us to run testing anyway:
                    print(f"Test on line {str(ll+1)} passed; nonetheless running causal testing by user request.")
                    run_causal_testing(original_test_result, dev_only_test_mode, take_manual_characters_for_fuzzing)
    else:   # 'all' not requested.  Run causal testing on each user-specified line that fails due to the user's fault (ie some failure in a "call descendant" of the user's test file)
        failed_test_encountered_user_fault = False  # This gets set to true if a failed test is encountered and the user is at fault
        for line_requested in line_numbers_to_test:
            line_requested_as_int = int(line_requested)
            original_test_result = get_unit_test_result(test_module_filepath, filename, line_requested_as_int)
            if original_test_result.failed:
                if user_at_fault(original_test_result.execution_path, original_test_result.trace_indices_descended_from_non_ignored_user_code, test_module_name, original_test_result.involved_user_and_py_holmes_modules):    # If the user's test is at fault:
                    failed_test_encountered_user_fault = True
                    run_causal_testing(original_test_result, dev_only_test_mode, take_manual_characters_for_fuzzing)
                else:   # If the user isn't at fault:
                    warn(f"Test on line {line_requested} failed but not due to a fault in the user's test or any of its call descendants.  Causal testing will not be performed.  Traceback is as follows:\n" + original_test_result.traceback)
                    if still_run_causal_testing_on_passing_tests:
                        print(f"Nonetheless running causal testing by user request.")
                        run_causal_testing(original_test_result, dev_only_test_mode, take_manual_characters_for_fuzzing)
            elif still_run_causal_testing_on_passing_tests:  # If the test passed but the user wants us to run testing anyway:
                print(f"Test on line {line_requested} passed; nonetheless running causal testing by user request.")
                run_causal_testing(original_test_result, dev_only_test_mode, take_manual_characters_for_fuzzing)
    if not failed_test_encountered_user_fault:
        if dev_only_test_mode and original_test_result is not None:     # Print detailed test results if in dev-only test mode
            print("MOST RECENT TEST:")
            print("EXECUTION PATH:\n" + str(original_test_result.execution_path))
            print("INPUT ARGS TREE:\n" + str(original_test_result.input_args_tree))
            print("FAILED:\n" + str(original_test_result.failed))
            print("TRACEBACK:\n" + str(original_test_result.traceback))
        print("No failed tests encountered (except for possible failures that aren't the user's fault -- each showed up in this console as a warning, if any).")
        if not still_run_causal_testing_on_passing_tests:
            print("If you would like to run causal testing anyway, rerun with '-p' to enable causal testing on passing tests")
