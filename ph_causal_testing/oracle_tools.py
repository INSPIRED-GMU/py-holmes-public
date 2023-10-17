"""Classes and functions for detection of oracles in test methods."""


from ast import parse, NodeVisitor, NodeTransformer, Subscript, Name, Constant, Load, AST, iter_fields, Name, Store, arg, Module, ClassDef, Attribute, Load
from astor import to_source
from collections import defaultdict

from math import *  # In case the user does.  This is to make node_to_meaningful_name() work
# TODO: We need to import everything the user does, in order to make eval() always work inside node_to_meaningful_name()

from ph_variable_sharing import shared_variables
from ph_basic_processing.parsers import minimize_indents, concatenate_list_to_string, get_module_level_only_from_file_content, remove_trailing_comment, remove_duplicates_from_list
from ph_basic_processing.stripping import strip_custom

# TODO: Both NodeVisitor.generic_visit() and NodeTransformer.generic_visit() seem like they might miss some nodes.  If I call them on the root node, some Name nodes get missed.  If I call them farther down (ie on an assert argument), will Name nodes still get missed?
# TODO: If the test contains no literals, warn the user that we can't generate new tests, and have to rely on fuzzes of similar found tests instead


#
# GLOBAL VARIABLES
#
total = 0   # Used by NameAndCallCounter.generic_visit()


#
# CLASSES
#
class AssignmentGraphCreatorAndOracleNodeLister(NodeVisitor):
    """Creates a list of oracle nodes (self.oracle_nodes and self.oracle_node_names) and creates a graph linking nodes
    to nodes that they play a role in defining.
    """
    def __init__(self, root):
        """
        :param root:    root node object
        """
        self.root = root    # Beware, points to the main ast, not a shallow copy.  Creating a shallow copy of this node would not be enough to make a shallow copy of the whole tree
        self.assignment_graph = defaultdict(lambda: [], dict())  # Goes from meaningful names to meaningful names.  Graph represented as a dictionary of from:to, pointing from values on right side of assignment operator to values on left side of assignment operator
        self.oracle_nodes = []  # List of oracle nodes
        self.oracle_node_names = []     # The names of those nodes
        self.does_literal_lead_to_oracle = defaultdict(lambda: False, dict())  # Keys are literal meaningful names, values are whether they lead to an oracle node using assignment_graph

        # Fill self.assignment_graph, self.oracle_nodes, and self.oracle_node_names
        self.generic_visit(self.root, root=self.root)

        # Fill self.does_literal_lead_to_oracle
        self.set_does_literal_lead_to_oracle()

    def generic_visit(self, node, path_to_node=None, root=None) -> None:
        """DO NOT CALL EXTERNALLY; this is called by self.__init__ instead.
        Build self.assignment_graph and self.oracle_nodes
        :param node:            the node itself, as an AST node object
        :param path_to_node:    the path from the true root of the tree to this node, as a list of strings.  For example, [".body", "[0]", ".body", "[1]"]
        :param root:            the root node of the tree as an AST node object
        """
        if root is None:
            raise TypeError("a value for root is required")
        if path_to_node is None:
            path_to_node = []

        # If this is a literal, Name, Call, or Attribute node, then search iteratively upward for an Assign node that is its parent
        # on the value side (not on the target side).  If one is found, then add edges to self.assignment_graph linking
        # its meaningful name it to every meaningful name in that node.targets[any number]
        if type(node).__name__ in ["Name", "Call", "Attribute", "Constant", "JoinedStr"]:    # Rather than count Lists, Tuples, Sets, and Dicts directly, we count constants within them
            path_to_assign_node_above = None
            path_to_assign_node_above_as_string = None
            assign_node_above = None
            path_testing = path_to_node.copy()
            for ii in range(len(path_to_node)):     # Look iteratively upward until we find our first Assign node, if any
                path_testing.pop()
                path_testing_as_string = concatenate_list_to_string(path_testing)
                node_testing = eval(f"self.root{path_testing_as_string}")
                if type(node_testing).__name__ == "Assign" and path_to_node[len(path_testing)] == ".value":
                    path_to_assign_node_above = path_testing.copy()
                    path_to_assign_node_above_as_string = path_testing_as_string
                    assign_node_above = node_testing    # Intentionally not copying
                    break
            if assign_node_above is not None:   # If we found an Assign with the correct relationship to node:
                # Get the meaningful name of the node
                node_meaningful_name = node_to_meaningful_name(node)

                # Get the meaningful name of each target
                targets_meaningful_names = []
                try:
                    targets_list = assign_node_above.targets[0].elts
                except AttributeError as err:
                    targets_list = assign_node_above.targets
                for target in targets_list:
                    if type(target).__name__ == "Name":
                        targets_meaningful_names.append(target.id)
                    elif type(target).__name__ == "Attribute":
                        targets_meaningful_names.append(target.value.id + "." + target.attr)
                    else:
                        raise RuntimeError(f"target not recognized as a Name or Attribute: {target}")

                # Add edges to self.assignment_graph linking this node's meaningful name to every target's meaningful
                # name.  We don't use the node's meaningful name because two different occurrences of a literal "foo" in
                # the same function aren't the same, but two different occurrences of the same Name or Attribute usually
                # are.
                for target_meaningful_name in targets_meaningful_names:
                    self.assignment_graph[node_meaningful_name].append(target_meaningful_name)

        # If this is an oracle node, add it to self.oracle_nodes and self.oracle_node_names
        if check_if_node_is_oracle(root, node, path_to_node):
            self.oracle_nodes.append(node)
            self.oracle_node_names.append(node_to_meaningful_name(node))

        # Call the base generic_visit so that other nodes are visited.
        # Rather than a direct call to generic_visit(), this is a copypaste of the source code for generic_visit(),
        # with modification so that path_to_node is passed along
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for ii in range(len(value)):
                    item = value[ii]
                    if isinstance(item, AST):
                        self.generic_visit(item, path_to_node=path_to_node+[f".{field}", f"[{str(ii)}]"], root=root)
            elif isinstance(value, AST):
                self.generic_visit(value, path_to_node=path_to_node+[f".{field}"], root=root)

    def set_does_literal_lead_to_oracle(self) -> None:
        """Fill self.does_literal_lead_to_oracle with values"""
        self.does_literal_lead_to_oracle = defaultdict(lambda: False, dict())
        literal_meaningful_names = [key for key in self.assignment_graph]
        for this_literal in literal_meaningful_names:
            # Get visited, a list of all meaningful names reachable from it
            visited = []
            fringe = [this_literal]
            while len(fringe) > 0:  # Until we empty the fringe:
                # Check if fringe has any oracles.  If so, True.
                for element in fringe:
                    if element in self.oracle_node_names:
                        self.does_literal_lead_to_oracle[this_literal] = True
                if this_literal in self.does_literal_lead_to_oracle and self.does_literal_lead_to_oracle[this_literal]:
                    break
                # Add each element in fringe to visited
                for element in fringe:
                    visited.append(element)
                # Empty fringe but keep a temp
                temp = fringe.copy()
                fringe = []
                # For each element in temp, add everything it leads to to the fringe, as long as we haven't already visited that meaningful name
                for fringe_element in temp:
                    for leads_to in self.assignment_graph[fringe_element]:
                        if leads_to not in visited:
                            fringe.append(leads_to)
            # Set to False if no oracle found
            if not (this_literal in self.does_literal_lead_to_oracle and self.does_literal_lead_to_oracle[this_literal]):
                self.does_literal_lead_to_oracle[this_literal] = False


class NameAndCallCounter(NodeVisitor):
    def generic_visit(self, node):
        """Count the number of name nodes AND call nodes among this node and its children.
        NOTE: Before calling this function, reset_total() must first be called.
        """
        global total
        if type(node).__name__ in ["Name", "Call"]:
            total += 1
        NodeVisitor.generic_visit(self, node)
        return total


#
# HELPER FUNCTIONS
#
def reset_total():
    global total
    total = 0


def node_to_meaningful_name(node) -> str:
    """Return the meaningful name of an ast node."""
    # Handle errors
    if node is None:
        raise TypeError("node must not be None")

    if type(node).__name__ == "Name":
        return node.id
    elif type(node).__name__ == "Call":
        try:
            return node.func.id
        except AttributeError as err:
            return node.func.value.id + "." + node.func.attr
    elif type(node).__name__ == "Attribute":
        return node.value.id + "." + node.attr
    elif type(node).__name__ == "Constant":
        return node.value
    elif type(node).__name__ == "JoinedStr":
        return to_source(node)
    elif type(node).__name__ == "List":
        return to_source(node)
    elif type(node).__name__ == "Tuple":
        return to_source(node)
    elif type(node).__name__ == "Set":
        return to_source(node)
    elif type(node).__name__ == "Dict":
        return to_source(node)
    elif type(node).__name__ == "UnaryOp":
        return eval(to_source(node))
    elif type(node).__name__ == "BinOp":
        return eval(to_source(node))
    else:
        return to_source(node)


def find_previous_response_for_attribute_object(path_to_attribute: list, name_of_test: str) -> list:
    """Check shared_variables.responses for a previous response for this attribute in this test, and return it.
    If one isn't found, then return ["", None, None, None]
    :param path_to_attribute:       path from root of the test to the attribute, formatted as a list of strings
    :param name_of_test:            the name of the test method itself
    """
    # Handle errors
    # path_to_attribute not a list
    if not isinstance(path_to_attribute, list):
        raise TypeError("path_to_attribute must be a list")
    # path_to_attribute contains non-string element
    for element in path_to_attribute:
        if not isinstance(element, str):
            raise TypeError("all elements of path_to_attribute must be strings")
    # name_of_test not a string
    if not isinstance(name_of_test, str):
        raise TypeError("name_of_test must be a string")

    shared_variables.initialize_user_response_for_oracle_checking()
    responses = shared_variables.responses

    shared_variables.initialize_original_test_method_object()
    original_test_name = shared_variables.original_test.test_name

    # If name_of_test is "test_generation_seed", then change it to the name of the original test, because these tests are the same
    if name_of_test == "test_generation_seed":
        name_of_test = original_test_name

    # Search
    for element in responses:
        # If element[3] is "test_generation_seed", then change it to the name of the original test, because these tests are the same
        if element[3] == "test_generation_seed":
            element[3] = original_test_name
        # Check
        if element[1] == path_to_attribute and element[3] == name_of_test:
            return element
    return ["", None, None, None]


def check_if_node_is_oracle(root, node, path_to_node) -> bool:
    """Return whether node is an oracle.
    A node is in an oracle position iff at least one of the following is true...
    CLASS 1: First position is oracle
    ...self.assertEqual(): starting with this node, up [0], up args, down func, check attr leads to an assertEqual attribute (beware that this is not itself a node)
    ...self.assertNotEqual(): as with assertEqual but with this function's name instead
    ...self.assertIs(): as with assertEqual but with this function's name instead
    ...self.assertIsNot(): as with assertEqual but with this function's name instead
    ...self.assertAlmostEqual(): as with assertEqual but with this function's name instead
    ...self.assertNotAlmostEqual(): as with assertEqual but with this function's name instead
    ...self.assertGreater(): as with assertEqual but with this function's name instead
    ...self.assertGreaterEqual(): as with assertEqual but with this function's name instead
    ...self.assertLess(): as with assertEqual but with this function's name instead
    ...self.assertLessEqual(): as with assertEqual but with this function's name instead
    ...self.assertCountEqual(): as with assertEqual but with this function's name instead
    ...self.assertMultiLineEqual(): as with assertEqual but with this function's name instead
    ...self.assertSequenceEqual(): starting with this node, up [any number], up elts or keys or values, up [0], up args, down func, check attr leads to an assertSequenceEqual attribute (beware that this is not itself a node)
    ...self.assertListEqual(): as with assertSequenceEqual but with this function's name instead
    ...self.assertTupleEqual(): as with assertSequenceEqual but with this function's name instead
    ...self.assertSetEqual(): as with assertSequenceEqual but with this function's name instead
    ...self.assertDictEqual(): as with assertSequenceEqual but with this function's name instead
    CLASS 2: Position with fewest variable names is oracle.  In the case of a tie, request a human to determine which is the oracle.
    ...self.assertIn(): whichever of the following has fewer name nodes per element: {up [0], up args, down func, check attr} OR {up [any number], up elts or keys or values, up [1], up args, down func, check attr} leads to an assertIn attribute (beware that this is not itself a node)
    ...self.assertNotIn(): as with assertIn but with this function's name instead
    ...self.assertRegexpMatches(): whichever of the following has fewer name nodes per element: {up [0], up args, down func, check attr} OR {up [1], up args, down func, check attr} leads to an assertRegexpMatches attribute (beware that this is not itself a node)
    ...self.assertNotRegexpMatches(): as with assertNotRegexpMatches but with this function's name instead
    CLASS 3: All positions are oracles
    ...self.assertRaisesRegexp(): starting with this node, {up [any number], up args, down func, check attr} OR {up value, up [any number], up keywords, down func, check attr} leads to an assertRaisesRegexp attribute (beware that this is not itself a node)
    ...self.assertWarnsRegex(): as with assertRaisesRegexp but with this function's name instead
    ...self.assertLogs(): as with assertRaisesRegexp but with this function's name instead
    CLASS 4: No positions are oracles
    ...self.assertTrue()
    ...self.assertFalse()
    ...self.assertIsNone()
    ...self.assertIsNotNone()
    ...self.assertIsInstance()
    ...self.assertNotIsInstance()
    ...self.assertRaises()
    ...self.assertWarns()
    :param root:            the root node of the tree, as an AST object
    :param node:            the node itself, as an AST object
    :param path_to_node:    the path from the true root of the tree to this node, as a list of strings.  For example, [".body", "[0]", ".body", "[1]"]
    """
    is_class_1_oracle = False  # False until found to be True
    is_class_3_oracle = False  # False until found to be True
    is_class_2_oracle = False  # False until found to be True
    might_be_class_2_oracle = False  # Indicates node is argument of class 2; we must then verify whether it's an oracle argument
    # Check if this node is an oracle argument of a CLASS 1 assert
    try:  # First check for most class 1 cases
        # Get path to the node up [0] and up args from this node
        if path_to_node[-1] != "[0]":
            raise IndexError("node does not fit this version of Class 1")
        if path_to_node[-2] != ".args":
            raise AttributeError("node does not fit this version of Class 1")
        path_to_node_above = path_to_node[:-2]
        path_to_node_above_as_string = concatenate_list_to_string(path_to_node_above)
        # Get the node down func from *that* node
        path_to_node_of_interest_as_string = path_to_node_above_as_string + ".func"
        node_of_interest = eval("root" + path_to_node_of_interest_as_string)
        # If that node's attr attribute is one of this subset of Class 1 functions, then this is a Class 1 oracle node
        if node_of_interest.attr in ["assertEqual", "assertNotEqual", "assertIs", "assertIsNot", "assertAlmostEqual", "assertNotAlmostEqual", "assertGreater", "assertGreaterEqual", "assertLess", "assertLessEqual", "assertCountEqual", "assertMultiLineEqual"]:
            is_class_1_oracle = True
    except (AttributeError, IndexError) as err:
        is_class_1_oracle = False
    if not is_class_1_oracle:  # Then check for assertSequenceEqual, assertListEqual, assertTupleEqual, assertSetEqual, and assertDictEqual
        try:
            # Get the path to the node up [any number], up elts or keys or values, up [0], up args from this node
            if not path_to_node[-1][1:-1].isnumeric():
                raise IndexError("node does not fit this version of Class 1")
            if path_to_node[-2] not in [".elts", ".keys", ".values"]:
                raise AttributeError("node does not fit this version of Class 1")
            if path_to_node[-3] != "[0]":
                raise IndexError("node does not fit this version of Class 1")
            if path_to_node[-4] != ".args":
                raise AttributeError("node does not fit this version of Class 1")
            path_to_node_above = path_to_node[:-4]
            path_to_node_above_as_string = concatenate_list_to_string(path_to_node_above)
            # Get the node down from *that* node
            path_to_node_of_interest_as_string = path_to_node_above_as_string + ".func"
            node_of_interest = eval("root" + path_to_node_of_interest_as_string)
            # If that node's attr attribute is one of this subset of Class 1 functions, then this is a Class 1 oracle node
            if node_of_interest.attr in ["assertSequenceEqual", "assertListEqual", "assertTupleEqual", "assertSetEqual", "assertDictEqual"]:
                is_class_1_oracle = True
        except (AttributeError, IndexError) as err:
            is_class_1_oracle = False
    # Check if this node is an oracle argument of a CLASS 3 assert
    if not is_class_1_oracle:
        # First, check for up [any number], up args, down func, check attr
        try:
            # Get path to the node up [any number] and up args from this node
            if not (len(path_to_node[-1]) >= 3 and path_to_node[-1].startswith("[") and path_to_node[-1].endswith("]") and path_to_node[-1][1:-1].isnumeric()):
                raise IndexError("node does not fit this version of Class 3")
            if path_to_node[-2] != ".args":
                raise AttributeError("node does not fit this version of Class 3")
            path_to_node_above = path_to_node[:-2]
            path_to_node_above_as_string = concatenate_list_to_string(path_to_node_above)
            # Get the node down func from *that* node
            path_to_node_of_interest_as_string = path_to_node_above_as_string + ".func"
            node_of_interest = eval("root" + path_to_node_of_interest_as_string)
            # If that node's attr attribute is one of the Class 3 functions, then this is a Class 3 oracle node
            if node_of_interest.attr in ["assertRaisesRegexp", "assertWarnsRegex", "assertLogs"]:
                is_class_3_oracle = True
        except (AttributeError, IndexError) as err:
            is_class_3_oracle = False
        # Second, if that didn't confirm as a Class 3 oracle, check for up value, up [any number], up keywords, down func, check attr
        if not is_class_3_oracle:
            try:
                # Get path to the node up value, up [any number], and up keywords from this node
                if path_to_node[-1] != ".value":
                    raise AttributeError("node cannot be Class 3")
                if not (len(path_to_node[-2]) >= 3 and path_to_node[-2].startswith("[") and path_to_node[-2].endswith("]") and path_to_node[-2][1:-1].isnumeric()):
                    raise IndexError("node cannot be Class 3")
                if path_to_node[-3] != ".keywords":
                    raise AttributeError("node cannot be Class 3")
                path_to_node_above = path_to_node[:-3]
                path_to_node_above_as_string = concatenate_list_to_string(path_to_node_above)
                # Get the node down func from *that* node
                path_to_node_of_interest_as_string = path_to_node_above_as_string + ".func"
                node_of_interest = eval("root" + path_to_node_of_interest_as_string)
                # If that node's attr attribute is one of the Class 3 functions, then this is a Class 3 oracle node
                if node_of_interest.attr in ["assertRaisesRegexp", "assertWarnsRegex", "assertLogs"]:
                    is_class_3_oracle = True
            except (AttributeError, IndexError) as err:
                is_class_3_oracle = False
    # Check if this node is an oracle argument of a CLASS 2 assert
    if not is_class_1_oracle and not is_class_3_oracle:
        # Try to get a path from this node to a Class 2 assert that demonstrates that it's an argument
        which_function_class_2 = None  # String.  If this node is a Class 2 argument, then we'll set this to the name of that Class 2 function
        which_arg_class_2 = None  # Int.  If this node is a Class 2 argument, then we'll set this to indicate whether it's argument 0 or 1
        # Check if it's argument 0 of any of the Class 2 functions
        try:
            # Get the node up [0], up args from this node
            if path_to_node[-1] != "[0]":
                raise IndexError("node cannot be Class 2 argument 0")
            if path_to_node[-2] != ".args":
                raise AttributeError("node cannot be Class 2 argument 0")
            path_to_node_above = path_to_node[:-2]
            path_to_node_above_as_string = concatenate_list_to_string(path_to_node_above)
            # Get the node down func from *that* node
            path_to_node_of_interest = path_to_node_above + [".func"]
            path_to_node_of_interest_as_string = path_to_node_above_as_string + ".func"
            node_of_interest = eval("root" + path_to_node_of_interest_as_string)
            # If that node's attr attribute is one of the Class 2 functions, then this *might be* a Class 2 oracle node
            if node_of_interest.attr in ["assertIn", "assertNotIn", "assertRegexpMatches", "assertNotRegexpMatches"]:
                might_be_class_2_oracle = True
                which_function_class_2 = node_of_interest.attr
                which_arg_class_2 = 0
        except (AttributeError, IndexError) as err:
            might_be_class_2_oracle = False
            is_class_2_oracle = False
        # Check if it's argument 1 of assertIn or assertNotIn -- SPECIFICALLY AN ELEMENT WITHIN THE CONTAINER ARGUMENT
        if not might_be_class_2_oracle:
            try:
                # Get the node up [any number], up elts or keys or values, up [1], up args from this node
                if not (len(path_to_node[-1]) >= 3 and path_to_node[-1].startswith("[") and path_to_node[-1].endswith("]") and path_to_node[-1][1:-1].isnumeric()):
                    raise IndexError("node cannot be Class 2 argument 1 for assertIn or assertNotIn")
                if path_to_node[-2] not in [".elts", ".keys", ".values"]:
                    raise AttributeError("node cannot be Class 2 argument 1 for assertIn or assertNotIn")
                if path_to_node[-3] != "[1]":
                    raise IndexError("node cannot be Class 2 argument 1 for assertIn or assertNotIn")
                if path_to_node[-4] != ".args":
                    raise AttributeError("node cannot be Class 2 argument 1 for assertIn or assertNotIn")
                path_to_node_above = path_to_node[:-4]
                path_to_node_above_as_string = concatenate_list_to_string(path_to_node_above)
                # Get the node down func from *that* node
                path_to_node_of_interest = path_to_node_above + [".func"]
                path_to_node_of_interest_as_string = path_to_node_above_as_string + ".func"
                node_of_interest = eval("root" + path_to_node_of_interest_as_string)
                # If that node's attr attribute is assertIn or assertNotIn, then this *might* be a Class 2 oracle node
                if node_of_interest.attr in ["assertIn", "assertNotIn"]:
                    might_be_class_2_oracle = True
                    which_function_class_2 = node_of_interest.attr
                    which_arg_class_2 = 1
            except (AttributeError, IndexError) as err:
                might_be_class_2_oracle = False
                is_class_2_oracle = False
        # Check if it's argument 1 of assertRegexpMatches or assertNotRegexpMatches
        if not might_be_class_2_oracle:
            try:
                # Get the node up [1], up args from this node
                if path_to_node[-1] != "[1]":
                    raise IndexError("node cannot be Class 2 argument 1 for assertRegexpMatches or assertNotRegexpMatches")
                if path_to_node[-2] != ".args":
                    raise AttributeError("node cannot be Class 2 argument 1 for assertRegexpMatches or assertNotRegexpMatches")
                path_to_node_above = path_to_node[:-2]
                path_to_node_above_as_string = concatenate_list_to_string(path_to_node_above)
                # Get the node down func from *that* node
                path_to_node_of_interest = path_to_node_above + [".func"]
                path_to_node_of_interest_as_string = path_to_node_above_as_string + ".func"
                node_of_interest = eval("root" + path_to_node_of_interest_as_string)
                # If that node's attr attribute is assertRegexpMatches or assertNotRegexpMatches, then this *might* be a Class 2 oracle node
                if node_of_interest.attr in ["assertRegexpMatches", "assertNotRegexpMatches"]:
                    might_be_class_2_oracle = True
                    which_function_class_2 = node_of_interest.attr
                    which_arg_class_2 = 1
            except (AttributeError, IndexError) as err:
                might_be_class_2_oracle = False
                is_class_2_oracle = False
        if might_be_class_2_oracle:  # We've confirmed that it's a Class 2 argument, but we need to check whether it's an oracle argument
            # Get the other argument node
            if which_arg_class_2 == 0:
                if which_function_class_2 in ["assertIn", "assertNotIn"]:
                    path_to_other_node = path_to_node[:-1]
                    path_to_other_node.append("[1]")  # In this case, this is the container, which may itself contain literals
                else:  # Must be in ["assertRegexpMatches", "assertNotRegexpMatches"]
                    path_to_other_node = path_to_node[:-1]
                    path_to_other_node.append("[1]")
            else:  # which_arg_class_2 must equal 1
                if which_function_class_2 in ["assertIn", "assertNotIn"]:  # If this node is an element of the argument 1 container:
                    path_to_other_node = path_to_node[:-3]
                    path_to_other_node.append("[0]")
                else:  # Must be in ["assertRegexpMatches", "assertNotRegexpMatches"]
                    path_to_other_node = path_to_node[:-1]
                    path_to_other_node.append("[0]")
            path_to_other_node_as_string = concatenate_list_to_string(path_to_other_node)
            other_node = eval("root" + path_to_other_node_as_string)
            # Determine how many names and calls are involved in each argument, PER ELEMENT
            counter = NameAndCallCounter()
            if which_arg_class_2 == 0:
                if which_function_class_2 in ["assertIn", "assertNotIn"]:  # node is an element, other_node is a container
                    reset_total()
                    num_names_and_calls_related_to_node_per_element = counter.generic_visit(node)
                    reset_total()
                    num_names_and_calls_related_to_other_node_per_element = counter.generic_visit(other_node)
                    # Divide num_names_and_calls_related_to_other_node_per_element by the number of elements in the container that is that node
                    if type(other_node).__name__ == "Dict":
                        num_elements = len(other_node.keys)
                    else:
                        num_elements = len(other_node.elts)
                    num_names_and_calls_related_to_other_node_per_element /= num_elements
                else:  # Must be in ["assertRegexpMatches", "assertNotRegexpMatches"].  Both nodes are elements
                    reset_total()
                    num_names_and_calls_related_to_node_per_element = counter.generic_visit(node)
                    reset_total()
                    num_names_and_calls_related_to_other_node_per_element = counter.generic_visit(other_node)
            else:  # which_arg_class_2 must equal 1
                if which_function_class_2 in ["assertIn", "assertNotIn"]:  # If this node is an element of the argument 1 container.  node is an element of the argument 1 container, other_node is an element
                    reset_total()
                    num_names_and_calls_related_to_node_per_element = eval(f"counter.generic_visit(root{path_to_node_above_as_string}.args[1])")
                    reset_total()
                    num_names_and_calls_related_to_other_node_per_element = counter.generic_visit(other_node)
                    # Divide num_names_and_calls_related_to_node_per_element by the number of elements in the container above that node
                    path_to_container = path_to_node[:-1]
                    path_to_container_as_string = concatenate_list_to_string(path_to_container)
                    container = eval("root" + path_to_container_as_string)
                    num_elements = len(container)
                    num_names_and_calls_related_to_node_per_element /= num_elements
                else:  # Must be in ["assertRegexpMatches", "assertNotRegexpMatches"].  Both nodes are elements
                    reset_total()
                    num_names_and_calls_related_to_node_per_element = counter.generic_visit(node)
                    reset_total()
                    num_names_and_calls_related_to_other_node_per_element = counter.generic_visit(other_node)
            # Set is_class_2_oracle, getting human help if necessary
            if num_names_and_calls_related_to_node_per_element < num_names_and_calls_related_to_other_node_per_element:
                is_class_2_oracle = True
            elif num_names_and_calls_related_to_node_per_element == num_names_and_calls_related_to_other_node_per_element:  # Need to ask for human help
                response = ""
                previous_user_response = find_previous_response_for_attribute_object(path_to_node_of_interest, root.body[0].name)
                if previous_user_response[1] == path_to_node_of_interest:   # If we've already given an answer for this function
                    if which_arg_class_2 == previous_user_response[2]:  # If the answer is for the same arg:
                        response = previous_user_response[0]
                    else:  # Response must have been for the other arg, so this time make the response opposite
                        if previous_user_response[0].upper() == "Y":
                            response = "N"
                        else:  # previous_user_response[0].upper() must equal "N"
                            response = "Y"
                path_to_line = path_to_node_of_interest[:4]
                path_to_line_as_string = concatenate_list_to_string(path_to_line)
                line_text = eval(f"to_source(root{path_to_line_as_string})")
                while response.upper() not in ["Y", "N"]:
                    line_text_no_trailing_whitespace = strip_custom(line_text, ['\n', '\t', ' '], 'tail')
                    shared_variables.initialize()
                    user_help_skip = shared_variables.user_help_skip
                    if not user_help_skip:
                        response = input(f"HUMAN HELP NEEDED: Is argument {str(which_arg_class_2)} (counting from 0) of {node_of_interest.attr} on the line {line_text_no_trailing_whitespace} an oracle argument? Y/n: ")
                    else:
                        response = "Y"
                    if response.upper() in ["Y", "N"]:
                        previous_user_response = [response, path_to_node_of_interest, which_arg_class_2, root.body[0].name]
                        shared_variables.initialize_user_response_for_oracle_checking(previous_user_response)   # Post to shared variables
                is_class_2_oracle = (response.upper() == "Y")
    # Set node_is_oracle_argument and return
    node_is_oracle_argument = is_class_1_oracle or is_class_3_oracle or is_class_2_oracle
    return node_is_oracle_argument
