"""Classes and functions to cut dissimilar unit tests."""


from ast import parse, NodeVisitor, NodeTransformer, AST, iter_fields, Name, Store, arg, Constant

from ph_causal_testing.class_for_test_method import TestMethod
from ph_basic_processing.parsers import minimize_indents, concatenate_list_to_string
from ph_variable_sharing import shared_variables


#
# CLASSES
#
class SimilarityChecker(NodeVisitor):
    """Determines whether two asts are 'call-similar'.  See cut_found_tests() for how we define
    'call-similar.'
    """
    def __init__(self, variant, original):
        """
        :param variant:                 root node AST for the test being compared to the original
        :param original:                root node AST for the original test
        """
        # Handle errors
        # variant not an ast
        if not isinstance(variant, AST):
            raise TypeError("variant must be an AST node")
        # original not an ast
        if not isinstance(original, AST):
            raise TypeError("original must be an AST node")

        self.variant = variant
        self.original = original

        # Populate self.variant_call_sequence
        self.variant_call_sequence = []
        self.generic_visit(self.variant, self.variant_call_sequence)

        # Get self.original_call_sequence from shared_variables.  If it isn't there, calculate it and post it to save time in the future.
        shared_variables.initialize_original_call_sequence()
        try:
            self.original_call_sequence = shared_variables.original_call_sequence
        except AttributeError as err:
            self.original_call_sequence = []
            self.generic_visit(self.original, self.original_call_sequence)
            shared_variables.initialize_original_call_sequence(self.original_call_sequence)

        # Determine whether they're call-similar
        self.extremely_similar = (self.variant_call_sequence == self.original_call_sequence)

    def generic_visit(self, node, call_sequence_attribute=None) -> None:
        """Populate a particular call sequence variable.
        :param node:                        the node itself, as an AST node object.  This should be the root node the first time generic_visit is called
        :param call_sequence_attribute:     list of strings (recommended to be empty when self.generic_visit() is first called).  The call sequence attribute to be updated, such as self.original_call_sequence or self.variant_call_sequence
        """
        # Handle errors
        # node not an ast
        if not isinstance(node, AST):
            raise TypeError("node must be an AST node")
        # call_sequence_attribute not a list
        if not isinstance(call_sequence_attribute, list):
            raise TypeError("call_sequence_attribute must be a list")
        # call_sequence_attribute contains non-string element
        for element in call_sequence_attribute:
            if not isinstance(element, str):
                raise TypeError("all elements of call_sequence_attributes must be strings")

        # If this is a Call node, then find the name of the function being called and add it to call sequence attribute
        if type(node).__name__ == "Call":
            try:
                call_sequence_attribute.append(node.func.id)
            except AttributeError as err:
                call_sequence_attribute.append(node.func.attr)  # This line is used if the call is a method, eg "self.assertEqual()"

        # Call the base generic_visit so that other nodes are visited.
        # Rather than a direct call to generic_visit(), this is a copypaste of the source code for generic_visit(),
        # with modification so that path_to_node is passed along
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for ii in range(len(value)):
                    item = value[ii]
                    if isinstance(item, AST):
                        self.generic_visit(item, call_sequence_attribute=call_sequence_attribute)
            elif isinstance(value, AST):
                self.generic_visit(value, call_sequence_attribute=call_sequence_attribute)


#
# HELPER FUNCTIONS
#
def cut_found_tests(found_tests: list, original_test, dev_only_test_mode: bool) -> list:
    """Given a list of found tests, return only those tests that are 'call-similar' to the original test.
    We define 'call-similar' as having the same sequence of function calls, regardless of those function calls'
    arguments.  Note that the creation of an object from a class also involves a function call (such as Foo()).
    :param found_tests:     list of TestMethod objects for found user-written tests
    :param original_test:   TestMethod object for the original user-written test
    :param dev_only_test_mode:      whether --dev_only_test_mode was set to True when py-holmes was called from the command line
    """
    # Handle errors
    # found_tests not a list
    if not isinstance(found_tests, list):
        raise TypeError("found_tests must be a list")
    # found_tests contains non-TestMethod element
    for element in found_tests:
        if not isinstance(element, TestMethod):
            raise TypeError("all elements of found_tests must be TestMethod objects")
    # original_test not a TestMethod
    if not isinstance(original_test, TestMethod):
        raise TypeError("original_test must be a TestMethod object")
    # dev_only_test_mode not a bool
    if not isinstance(dev_only_test_mode, bool):
        raise TypeError("dev_only_test_mode must be a bool")

    # Get ast for original test
    original_test_ast = parse(concatenate_list_to_string(minimize_indents(original_test.test_content), between="\n"))

    # Check similarity of each test, potentially adding it to extremely_similar_tests
    extremely_similar_tests = []
    for test in found_tests:
        test_ast = parse(concatenate_list_to_string(minimize_indents(test.test_content), between="\n"))
        checker = SimilarityChecker(test_ast, original_test_ast)
        if checker.extremely_similar:
            extremely_similar_tests.append(test)

    # If in dev-only test mode, print a few attributes of each TestMethod object in output_tests
    if dev_only_test_mode:
        print("BEGIN ATTRIBUTES OF FOUND TESTMETHOD OBJECTS AFTER CUTTING")
        counter = 0
        for obj in extremely_similar_tests:
            print(f"BEGIN ATTRIBUTES FOR EXTANT TESTMETHOD {counter}")
            print(f"TEST FILEPATH: {obj.test_filepath}")
            print(f"TEST CLASS: {obj.test_class}")
            print(f"TEST NAME: {obj.test_name}")
            print(f"END ATTRIBUTES FOR EXTANT TESTMETHOD {counter}")
            counter += 1
        print("END ATTRIBUTES OF FOUND TESTMETHOD OBJECTS AFTER CUTTING")

    return extremely_similar_tests
