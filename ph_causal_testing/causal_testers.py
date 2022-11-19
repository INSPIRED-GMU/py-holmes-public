"""Classes and functions for performing causal testing after the results of the original test have been gathered."""


from os import remove

from ph_variable_sharing import shared_variables
from ph_original_test_result_generation.ph_original_test_running.original_test_runners import OriginalUnitTestResult
from ph_causal_testing.unit_test_finders import find_tests_of_same_files_methods_and_classes
from ph_causal_testing.unit_test_cutters import cut_found_tests
from ph_causal_testing.unit_test_fuzzers import fuzz_tests
from ph_causal_testing.class_for_test_method import TestMethod
from ph_causal_testing.variant_test_runners import run_variants_and_show_results


def run_causal_testing(original_test_result: OriginalUnitTestResult, use_dev_only_test_mode: bool, manual_fuzzing_characters: bool) -> None:
    """Perform causal testing given a single original unit test result.
    use_dev_only_test_mode determines whether to print the attributes of the most recent failing test.
    :param original_test_result:        an OriginalUnitTestResult object for the original test
    :param use_dev_only_test_mode:      whether --dev_only_test_mode was set to True when py-holmes was called from the command line
    :param manual_fuzzing_characters:   whether --character_palette_manual was set to True when py-holmes was called from the command line
    """
    # Handle errors
    # original_test_result not an OriginalUnitTestResult object
    if not isinstance(original_test_result, OriginalUnitTestResult):
        raise TypeError("original_test_result must be an OriginalUnitTestResult object")
    # use_dev_only_test_mode not a bool
    if not isinstance(use_dev_only_test_mode, bool):
        raise TypeError("use_dev_only_test_mode must be a bool")
    # manual_fuzzing_characters not a bool
    if not isinstance(manual_fuzzing_characters, bool):
        raise TypeError("manual_fuzzing_characters must be a bool")

    # Start with a print to say which test method is being subjected to causal testing
    tested_class = original_test_result.test_class_string
    tested_method = original_test_result.test_method_string
    print(f"{'*' * 16} BEGIN CAUSAL TESTING RESULTS FOR {tested_class}.{tested_method} {'*' * 16}")

    # If in dev-only test mode, print all attributes of original_test_result
    if use_dev_only_test_mode:
        print("EXECUTION PATH:\n" + str(original_test_result.execution_path))
        print("INPUT ARGS TREE:\n" + str(original_test_result.input_args_tree))
        print("FAILED:\n" + str(original_test_result.failed))
        print("TRACEBACK:\n" + str(original_test_result.traceback))

    # Run causal testing
    # Create a TestMethod object for the original test and post it to shared_variables.py
    shared_variables.initialize()
    original_test_file_absolute_path = shared_variables.file_absolute
    original_test_method_definition_line = shared_variables.definition_line
    original_test = TestMethod(origin="found", test_filepath=original_test_file_absolute_path, starting_test_lineno=original_test_method_definition_line, is_fuzzed=False, is_original=True)
    shared_variables.initialize_original_test_method_object(original_test)

    # Find the set of existing tests in the user's project that test the same file/class
    # TODO: Might be able to skip this step and use cut_found_tests to find the similar-enough tests to begin with
    found_similar_tests = find_tests_of_same_files_methods_and_classes(original_test, use_dev_only_test_mode)

    # Cut found similar tests that aren't call-similar
    found_similar_tests = list(found_similar_tests)
    found_similar_tests = cut_found_tests(found_similar_tests, original_test, use_dev_only_test_mode)

    # Fuzz tests that survived the cut, as well as the original test
    num_test_variants = shared_variables.num_test_variants
    tests_to_fuzz = [original_test] + found_similar_tests
    fuzzed_from_original, fuzzed_from_found = fuzz_tests(tests_to_fuzz, original_test_file_absolute_path, use_dev_only_test_mode, manual_fuzzing_characters, num_tests=num_test_variants)

    # Run some of the fuzzed tests and show results
    run_variants_and_show_results(original_test_result, original_test, fuzzed_from_original, fuzzed_from_found, use_dev_only_test_mode)

    # Delete fuzzed file unless in dev-only test mode (test_outputs_fuzzed.py)
    if not use_dev_only_test_mode:
        shared_variables.initialize_fuzzed_test_file()
        remove(shared_variables.fuzzed_file_path)

    # Announce end of causal testing
    print(f"{'*' * 16} END CAUSAL TESTING RESULTS FOR {tested_class}.{tested_method} {'*' * 16}\n")
