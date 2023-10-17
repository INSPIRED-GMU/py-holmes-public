"""Classes and functions to fuzz tests"""


from ast import parse, NodeVisitor, NodeTransformer, AST, iter_fields, Name, Store, arg, Constant
from astor import to_source
from os import path, system, remove, getcwd
from random import randint, random, uniform, choice, gauss
from math import pi, atan2, sin, cos, log, ceil
from warnings import warn
import itertools    # DO NOT REMOVE THIS IMPORT; USED IN AN EVAL CALL
import ctypes       # DO NOT REMOVE THIS IMPORT; USED IN AN EVAL CALL
from collections import OrderedDict
import re

from ph_variable_sharing import shared_variables
from ph_causal_testing.unit_test_finders import find_all_test_methods_in_file
from ph_causal_testing.oracle_tools import check_if_node_is_oracle, node_to_meaningful_name, AssignmentGraphCreatorAndOracleNodeLister
from ph_basic_processing.parsers import concatenate_list_to_string, minimize_indents, get_module_level_only_from_file_content, insert_char_in_string_at_index, remove_char_from_string_at_index, replace_char_in_string_at_index, leading_spaces_of, overwrite_list_with_list_at_index
from ph_basic_processing.stripping import strip_custom
from ph_causal_testing.class_for_test_method import TestMethod


#
# GLOBAL VARIABLES
#
shared_variables.initialize()
ROOT_DIR = shared_variables.ROOT_DIR
fuzzed_output_filename = "test_outputs_fuzzed.py"
name_counter = 0    # Globaled by create_fuzzed_test_strings()


#
# CLASSES
#
class FuzzingTargetTypeRangeAndStd:
    """Data class containing a type, range, and (optional) standard deviation for fuzzing.  Used in DL mode.
    """
    def __init__(self, type, min, max, std=None):
        """
        :param type:    eg int, float
        :param min:     minimum value (inclusive).  Should be a float or int.
        :param max:     maximum value (exclusive).  Should be a float or int.
        :param std:     standard deviation.  Should be a float or int.
        """
        self.type = type
        self.min = min
        self.max = max
        self.std = std


class FuzzTargeterDl(NodeVisitor):
    """Guided DL version of FuzzTargeter.
    Creates self.fuzzing_targets, a list of nodes on the tree specified by self.root that are valid targets for fuzzing.
    Also creates fuzzing_target_paths, a list of paths to those nodes.
    """
    def __init__(self, root: AST, source: list):
        """
        :param root:    root node object of an ast
        :param source:  newline-separated list containing the source code that root was made from
        """
        # Handle errors
        # root not an AST
        if not isinstance(root, AST):
            raise TypeError("root must be an AST object")
        # source not a list
        if not isinstance(source, list):
            raise TypeError("source must be a list")
        # source contains non-string element
        for element in source:
            if not isinstance(element, str):
                raise TypeError("all elements of source must be strings")

        self.root = root
        self.source = source

        # Identify lines in source where there's a comment that fits the fuzzing syntax `# !phdl nofuzz!`
        # Get lineno of first line in source
        first_lineno = self.root.body[0].lineno
        # Create a dict mapping line numbers to whether they contain a `# !phdl nofuzz!` comment.
        self.linenos_to_contains_nofuzz = {}
        for ll, line in enumerate(source):
            contains_nofuzz = parse_nofuzz_in_line(line)
            self.linenos_to_contains_nofuzz[ll + first_lineno] = contains_nofuzz

        # Build self.fuzzing_targets and self.fuzzing_target_paths
        self.fuzzing_targets = []
        self.fuzzing_target_paths = []  # Contains the tree path to the fuzzing target node with the same position in self.fuzzing_targets
        self.generic_visit(node=self.root)

    def get_node_from_path(self, path_to_node: list):
        """Given a path to a node (eg [".body", "[0]", ".body", "[1]"]), follow that path from the root node and return.
        """
        path_as_string = ""
        for path_segment in path_to_node:
            path_as_string += path_segment
        return eval(f"self.root{path_as_string}")

    def generic_visit(self, node, path_to_node=None):
        """Search the tree to add all literals to be fuzzed to self.fuzzing_targets, and their paths to
        self.fuzzing_target_paths.
        For the initial call to this function, node should be the root node of the ast.
        :param node:            the node itself
        :param path_to_node:    the path from the true root of the tree to this node, as a list of strings.  For example, [".body", "[0]", ".body", "[1]"]
        """
        if path_to_node is None:
            path_to_node = []
        # Check if this node is SPECIFICALLY A CONSTANT
        node_is_literal = type(node).__name__ in ["Constant"]  # We fuzz the Constants inside JoinedStrs rather than the JoinedStrs themselves.  Similarly, rather than fuzz Lists, Tuples, Sets, and Dicts directly, we fuzz constants within them
        # If it's a literal, determine whether this node is in a docstring immediately after the def line
        # I believe this is the case iff the node is a Constant, its great-great-great-grandparent is the root node,
        # its parent is an Expr, and its great-grandparent is a FunctionDef.
        if node_is_literal:
            try:
                node_is_docstring = False
                if type(node).__name__ == "Constant":  # If node is a constant...
                    if node is self.root.body[0].body[0].value:  # If the node's great-great-great grandparent is the root node...
                        if type(self.root.body[0].body[0]).__name__ == "Expr":  # If the node's parent is an Expr (ie the node isn't a call to anything, or an assignment; it's just sitting there)...
                            if type(self.root.body[0]).__name__ == "FunctionDef":  # If the node's great-grandparent is a FunctionDef...
                                node_is_docstring = True
            except (AttributeError, IndexError) as err:  # Default to false if one of these proving neighbors can't be found
                node_is_docstring = False

        # If it's a literal and not a docstring immediately after the def line and the line isn't marked to not fuzz,
        # check if it's inside an assignment for x (the input to the neural net).
        # It's inside an assignment for x iff it has an `assign` node ancestor whose `targets` attribute is a list with
        # length 1 containing a `name` node with an `id` of "x".
        if node_is_literal:
            if not node_is_docstring:
                if not self.linenos_to_contains_nofuzz[node.lineno]:
                    node_is_part_of_assignment_for_x = False
                    for pp, path_segment in enumerate(path_to_node):
                        node_along_path = self.get_node_from_path(path_to_node[:pp+1])
                        if type(node_along_path).__name__ == "Assign" and node_along_path.targets[0].id == "x":
                            node_is_part_of_assignment_for_x = True
                            break

        # If it's a literal and not a docstring immediately after the def line and the line isn't marked to not fuzz and
        # it's inside an assignment for x, populate self.fuzzing_targets and self.fuzzing_target_paths with information
        # about this node
        if node_is_literal:
            if not node_is_docstring:
                if not self.linenos_to_contains_nofuzz[node.lineno]:
                    if node_is_part_of_assignment_for_x:
                        self.fuzzing_targets.append(node)
                        self.fuzzing_target_paths.append(path_to_node)

        # Call the base generic_visit so that other nodes are visited.
        # Rather than a direct call to generic_visit(), this is a copypaste of the source code for generic_visit(),
        # with modification so that path_to_node is passed along
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for ii in range(len(value)):
                    item = value[ii]
                    if isinstance(item, AST):
                        self.generic_visit(item, path_to_node=path_to_node + [f".{field}", f"[{str(ii)}]"])
            elif isinstance(value, AST):
                self.generic_visit(value, path_to_node=path_to_node + [f".{field}"])


class FuzzTargeter(NodeVisitor):
    """Creates self.fuzzing_targets, a list of nodes on the tree specified by self.root that are valid targets for fuzzing.
    Also creates fuzzing_target_paths, a list of paths to those nodes.
    """
    def __init__(self, root):
        """
        :param root:    root node object of an ast
        """
        # Handle errors
        # root not an AST
        if not isinstance(root, AST):
            raise TypeError("root must be an AST object")

        self.root = root

        # Figure out which literals are involved in indirectly determining the value of an oracle
        self.grapher = AssignmentGraphCreatorAndOracleNodeLister(root)
        self.does_literal_lead_to_oracle_dict = self.grapher.does_literal_lead_to_oracle

        # Build self.fuzzing_targets and self.fuzzing_target_paths
        self.fuzzing_targets = []
        self.fuzzing_target_paths = []  # Contains the tree path to the fuzzing target node with the same position in self.fuzzing_targets
        self.generic_visit(node=self.root)

    def generic_visit(self, node, path_to_node=None):
        """Search the tree to add all literals to be fuzzed to self.fuzzing_targets, and their paths to
        self.fuzzing_target_paths.
        For the initial call to this function, node should be the root node of the ast.
        :param node:            the node itself
        :param path_to_node:    the path from the true root of the tree to this node, as a list of strings.  For example, [".body", "[0]", ".body", "[1]"]
        """
        if path_to_node is None:
            path_to_node = []
        # Check if this node is SPECIFICALLY A CONSTANT
        node_is_literal = type(node).__name__ in ["Constant"]  # We fuzz the Constants inside JoinedStrs rather than the JoinedStrs themselves.  Similarly, rather than fuzz Lists, Tuples, Sets, and Dicts directly, we fuzz constants within them
        # If it's a literal, determine whether this node is in a docstring immediately after the def line
        # I believe this is the case iff the node is a Constant, its great-great-great-grandparent is the root node,
        # its parent is an Expr, and its great-grandparent is a FunctionDef.
        if node_is_literal:
            try:
                node_is_docstring = False
                if type(node).__name__ == "Constant":  # If node is a constant...
                    if node is self.root.body[0].body[0].value:  # If the node's great-great-great grandparent is the root node...
                        if type(self.root.body[0].body[0]).__name__ == "Expr":  # If the node's parent is an Expr (ie the node isn't a call to anything, or an assignment; it's just sitting there)...
                            if type(self.root.body[0]).__name__ == "FunctionDef":  # If the node's great-grandparent is a FunctionDef...
                                node_is_docstring = True
            except (AttributeError, IndexError) as err:  # Default to false if one of these proving neighbors can't be found
                node_is_docstring = False
        # If it's a literal and not a docstring immediately after the def line, check whether some oracle's value is
        # indirectly based on it.
        if node_is_literal:
            if not node_is_docstring:
                node_meaningful_name = node_to_meaningful_name(node)
                node_is_indirectly_connected_to_oracle = self.does_literal_lead_to_oracle_dict[node_meaningful_name]
        # If it's a literal and not a docstring immediately after the def line, and no oracle's value is indirectly
        # based on it, then check if it's in an oracle position.
        # There are yet other asserts which have no oracle positions whatsoever, and they aren't covered here,
        # because the behavior of the rest of this program automatically takes care of them
        if node_is_literal:
            if not node_is_docstring:
                if not node_is_indirectly_connected_to_oracle:
                    node_is_oracle_argument = check_if_node_is_oracle(self.root, node, path_to_node)

        # If this node is a literal and not a docstring and not indirectly connected to an oracle and not an oracle
        # itself, add it to self.fuzzing_targets
        if node_is_literal and not node_is_docstring and not node_is_indirectly_connected_to_oracle and not node_is_oracle_argument:
            self.fuzzing_targets.append(node)
            self.fuzzing_target_paths.append(path_to_node)

        # Call the base generic_visit so that other nodes are visited.
        # Rather than a direct call to generic_visit(), this is a copypaste of the source code for generic_visit(),
        # with modification so that path_to_node is passed along
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for ii in range(len(value)):
                    item = value[ii]
                    if isinstance(item, AST):
                        self.generic_visit(item, path_to_node=path_to_node + [f".{field}", f"[{str(ii)}]"])
            elif isinstance(value, AST):
                self.generic_visit(value, path_to_node=path_to_node + [f".{field}"])


class FuzzActuator(NodeTransformer):
    """Given a tree, a list of paths to particular nodes in that tree, and new values to assign those nodes, modifies
    the tree appropriately
    """
    def __init__(self, root, paths_to_change: list, replacement_nodes: list):
        """
        :param root:                    root node object of an ast
        :param paths_to_change:         paths to the nodes in the ast that need to be changed
        :param replacement_nodes:       for each path in paths_to_change, a new node that will be that replacement
        """
        # Handle errors
        # root not an AST
        if not isinstance(root, AST):
            raise TypeError("root must be an AST object")
        # paths_to_change not a list
        if not isinstance(paths_to_change, list):
            raise TypeError("paths_to_change must be a list")
        # paths_to_change contains non-list element
        for element in paths_to_change:
            if not isinstance(element, list):
                raise TypeError("paths_to_change contains non-list element")
        # replacement_nodes not a list
        if not isinstance(replacement_nodes, list):
            raise TypeError("replacement_nodes must be a list")
        # replacement_nodes contains non-AST element
        for element in replacement_nodes:
            if not isinstance(element, AST):
                raise TypeError("replacement_nodes contains non-AST element")
        # different number of elements in paths_to_change and replacement_nodes
        if len(paths_to_change) != len(replacement_nodes):
            raise ValueError("paths_to_change and replacement_nodes must be the same length")

        self.root = root
        self.paths_to_change = paths_to_change
        self.replacement_nodes = replacement_nodes

    def generic_visit(self, node, path_to_node=None):
        """Find all elements in the tree and replace those at any path in self.paths_to_change with the appropriate
        replacement node from self.replacement_nodes.
        :param node:            the node itself
        :param path_to_node:    the path from the true root of the tree to this node, as a list of strings.  For example, [".body", "[0]", ".body", "[1]"]
        """
        if path_to_node is None:
            path_to_node = []

        # Determine whether the node is to be replaced
        is_node_to_be_replaced = path_to_node in self.paths_to_change

        # Unless the node is to be replaced, use the base class's generic_visit() method so that all children are
        # visited too.
        # Rather than a direct call to generic_visit(), this is a copypaste of the source code for generic_visit(), with
        # modification so that path_to_node is passed along
        if not is_node_to_be_replaced:
            for field, old_value in iter_fields(node):
                if isinstance(old_value, list):
                    new_values = []
                    for ii in range(len(old_value)):
                        value = old_value[ii]
                        if isinstance(value, AST):
                            value = self.generic_visit(value, path_to_node=path_to_node + [f".{field}", f"[{str(ii)}]"])
                            if value is None:
                                continue
                            elif not isinstance(value, AST):
                                new_values.extend(value)
                                continue
                        new_values.append(value)
                    old_value[:] = new_values
                elif isinstance(old_value, AST):
                    new_node = self.generic_visit(old_value, path_to_node=path_to_node + [f".{field}"])
                    if new_node is None:
                        delattr(node, field)
                    else:
                        setattr(node, field, new_node)

        # If the node is to be replaced, return the replacement node.  Else return the original node, which will
        # leave it unchanged.
        if is_node_to_be_replaced:
            replacement = self.replacement_nodes[self.paths_to_change.index(path_to_node)]
            return replacement
        else:
            return node  # Leave the node unchanged


#
# HELPER FUNCTIONS
#
def parse_nofuzz_in_line(line: str) -> bool:
    """Given a line of source code, check it for a comment that fits the no-fuzzing syntax `# !phdl nofuzz!`.
    If a comment fitting this syntax exists, return True.  Else return False.
    After the closing `!`, more comment text is allowed.  However, additional comment text is not allowed before the
    opening `!`.
    """
    # Handle errors
    # line not a string
    if not isinstance(line, str):
        raise TypeError("line must be a string")
    # line contains a newline
    if "\n" in line:
        raise ValueError("line must be a single line.  No newlines allowed.")

    # Run
    pattern = """(# !phdl nofuzz!)"""
    matches = re.findall(pattern, line)
    total_match_count = len(matches)
    return total_match_count >= 1


def parse_fuzzing_target_type_range_and_std_in_line(line: str) -> FuzzingTargetTypeRangeAndStd:
    """Given a line of source code, check it for a comment that fits the fuzzing syntax `# !phdl <type> <range> <optionally std>!`.
    For example, `# !phdl int 0:256 5!` or `# !phdl int 0:256!`.
    `<type>` must be either `int` or `float`.  `<range>` must be a expressed as a minimum value (inclusive), followed by
    a colon, followed by a maximum value (exclusive).  `<std>` is optional and must be expressed as a single int or
    float.
    If a comment fitting this syntax exists, return a FuzzingTargetTypeRangeAndStd object that describes it.
    If none exists, return None.
    If a comment contains multiple phrases that fit the syntax, an error will be thrown.
    After the closing `!`, more comment text is allowed.  However, additional comment text is not allowed before the
    opening `!`.
    """
    # Handle errors
    # line not a string
    if not isinstance(line, str):
        raise TypeError("line must be a string")
    # line contains a newline
    if "\n" in line:
        raise ValueError("line must be a single line.  No newlines allowed.")

    # Run
    pattern_minimum = """(# !phdl )[a-z]+( )[0-9.]+(:)[0-9.]+(!)"""
    pattern_with_std = """(# !phdl )[a-z]+( )[0-9.]+(:)[0-9.]+( )[0-9.]+(!)"""
    matches_minimum = re.findall(pattern_minimum, line)
    matches_with_std = re.findall(pattern_with_std, line)
    total_match_count = len(matches_minimum) + len(matches_with_std)
    if total_match_count == 0:
        return None
    elif total_match_count > 1:
        raise ValueError("line contains more than one match")

    # We have exactly one match.
    if len(matches_minimum) == 1:   # If it's without an std:
        # Find the type and range.
        match_object = re.search(pattern_minimum, line)
        phrase = match_object.group().split(" ")
        match_type = phrase[2]
        if match_type not in ["int", "float"]:
            raise ValueError(f"unsupported type: {match_type}")
        match_type = eval(match_type)
        match_range = phrase[3].replace("!", "").split(":")
        match_min = match_type(match_range[0])
        match_max = match_type(match_range[1])
        match_std = None
    elif len(matches_with_std) == 1:    # If it's with an std:
        match_object = re.search(pattern_with_std, line)
        phrase = match_object.group().split(" ")
        match_type = phrase[2]
        if match_type not in ["int", "float"]:
            raise ValueError(f"unsupported type: {match_type}")
        match_type = eval(match_type)
        match_range = phrase[3].replace("!", "").split(":")
        match_min = match_type(match_range[0])
        match_max = match_type(match_range[1])
        match_std = phrase[4][:-1]
        if "." in match_std or "e" in match_std:
            match_std = float(match_std)
        else:
            match_std = int(match_std)

    # Construct an object and return
    return FuzzingTargetTypeRangeAndStd(match_type, match_min, match_max, match_std)


def infer_character_palette(input_string: str) -> str:
    """Given an input_string, infer a string of characters that could reasonably be added to the string via insertions
    or replacements.
    :param input_string:        the string whose palette is to be inferred
    """
    # Handle errors
    # input_string not a str
    if not isinstance(input_string, str):
        raise TypeError("input_string must be a string")

    if len(input_string) == 0:  # If input_string is empty, we shrug and return the lowercase alphabet
        warn("fuzzing an empty string; assuming all lowercase alphabetical characters are okay to add.  If you instead want to enter character palettes manually, re-run py-holmes with the -c flag")
        return "abcdefghijklmnopqrstuvwxyz"

    character_groups = [    # List of strings, where each string is a group of related characters
        "abcdefghijklmnopqrstuvwxyz",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "0123456789",
        ".!?,",
        "+-/*",
        "()",
        "[]",
        "{}",
        "<>",
    ]

    output_palette = ""
    for input_char in input_string:
        # Add input_char to output_palette, along with every character that it shares a group with
        if input_char not in output_palette:
            output_palette += input_char
            for group in character_groups:
                if input_char in group:
                    for group_char in group:
                        if group_char not in output_palette:
                            output_palette += group_char

    return output_palette


def fuzz_literal_node_dl(input_node, type_range_and_std: FuzzingTargetTypeRangeAndStd, dev_only_test_mode: bool, fuzzing_mutants_count=51) -> list:
    """Given an ast node for a literal, return a list of fuzzed versions of that node.
    The quantity and variation of these fuzzed versions are determined by this function's keyword arguments.
    IMPORTANT NOTE: input_node is itself included as an element of the output list.  This is so that in some fuzzed
    tests, some literals can remain unaltered.
    :param input_node:                          an ast node object
    :param type_range_and_std:                  FuzzingTargetTypeRangeAndStd object
    :param dev_only_test_mode:                  whether --dev_only_test_mode was set to True when py-holmes was called from the command line
    :param fuzzing_mutants_count:               the length of the fuzzed list to be returned, including the original value
    :return:                                    a list of ast node objects.  The first element is guaranteed to be input_node
    """
    # Handle errors
    # input_node not an ast node
    if not isinstance(input_node, AST):
        raise TypeError("input_node must be an AST object")
    # input_node not a type of literal that we want to fuzz
    if type(input_node).__name__ not in ["Constant"]:   # We don't fuzz JoinedStrs themselves, because they contain constants which we fuzz instead
        raise ValueError("node is not a node for a fuzzable literal")
    # type_range_and_std not a FuzzingTargetTypeRangeAndStd
    if not isinstance(type_range_and_std, FuzzingTargetTypeRangeAndStd):
        raise TypeError("type_range_and_std must be a FuzzingTargetTypeRangeAndStd")
    # type_range_and_std.max not greater than type_range_and_std.min
    if not (type_range_and_std.max > type_range_and_std.min):
        raise ValueError("type_range_and_std.max must be greater than type_range_and_std.min")
    # type_range_and_std.type not supported
    if type_range_and_std.type not in [int, float]:
        raise ValueError(f"type {type_range_and_std.type} not supported for this operation")
    # input_node's value is the wrong type for type_range_and_std (except it's allowed to be an int if type_range_and_std.type is a float)
    if (type(input_node.value) is not type_range_and_std.type) and not (type(input_node.value) is int and type_range_and_std.type is float):
        raise TypeError("input_node's value is the wrong type for type_range_and_std (except it's allowed to be an int if type_range_and_std.type is a float)")
    # dev_only_test_mode not a bool
    if not isinstance(dev_only_test_mode, bool):
        raise TypeError("dev_only_test_mode must be a bool")
    # fuzzing_mutants_count not an int
    if not isinstance(fuzzing_mutants_count, int):
        raise TypeError("fuzzing_mutants_count must be an int")
    # fuzzing_mutants_count not positive
    if fuzzing_mutants_count <= 0:
        raise ValueError("fuzzing_mutants_count must be positive")

    # Warnings
    # fuzzing_mutants_count equals 1
    if fuzzing_mutants_count == 1:
        warn("fuzzing_mutants_count equals 1.  This means that no fuzzing will take place, because the original value is included as the first element of the returned list")

    output_nodes = [input_node]
    values_in_output_nodes = [input_node.value]

    # Get the size of the fuzz space.
    if type_range_and_std.type == int:
        fuzz_space_size = type_range_and_std.max - type_range_and_std.min
    elif type_range_and_std.type == float:
        fuzz_space_size = float("inf")
    else:
        raise ValueError(f"unsupported type: str({type_range_and_std.type}")

    # Fuzz!
    while (len(output_nodes) < fuzzing_mutants_count) and not (len(output_nodes) == fuzz_space_size):  # The second condition allows us to escape if the fuzzing space is smaller than the number of fuzz operations requested
        # Pick a new value for a new node
        if type_range_and_std.std is None:  # Use a uniform distribution
            if type_range_and_std.type == int:
                new_value = randint(type_range_and_std.min, type_range_and_std.max - 1)
            elif type_range_and_std.type == float:
                new_value = uniform(type_range_and_std.min, type_range_and_std.max)
                if new_value == type_range_and_std.max:     # Force this number to be thrown out
                    new_value = input_node.value
        else:   # Use a gaussian distribution
            if type_range_and_std.type == int:
                new_value = round(gauss(mu=input_node.value, sigma=type_range_and_std.std))
                if not (type_range_and_std.min <= new_value < type_range_and_std.max):     # Force this number to be thrown out
                    new_value = input_node.value
            elif type_range_and_std.type == float:
                new_value = gauss(mu=input_node.value, sigma=type_range_and_std.std)
                if not (type_range_and_std.min <= new_value < type_range_and_std.max):     # Force this number to be thrown out
                    new_value = input_node.value

        # Create a replacement node with the new value instead of the old one
        # If multiple literals on the same line are fuzzed, then that will make col_offset and end_col_offset incorrect.
        # However, this seems not to harm the fuzzed test text.
        new_node = Constant(value=new_value, kind=input_node.kind, lineno=input_node.lineno, col_offset=input_node.col_offset, end_lineno=input_node.end_lineno, end_col_offset=input_node.end_col_offset)

        # Add the new node to output_nodes only if it doesn't match an existing value
        if new_value not in values_in_output_nodes:
            output_nodes.append(new_node)
            values_in_output_nodes.append(new_value)

    # Return!
    return output_nodes


def fuzz_literal_node(input_node, dev_only_test_mode: bool, manual_fuzzing_characters=False, fuzzing_mutants_count=51, fuzzing_max_string_changes=3, fuzzing_max_num_added=2, fuzzing_num_chance_to_negate=0.25, fuzzing_max_complex_angle_change=pi/16, fuzzing_bool_chance_to_flip=0.5) -> list:
    """Given an ast node for a literal, return a list of fuzzed versions of that node.
    The quantity and variation of these fuzzed versions are determined by this function's keyword arguments.
    IMPORTANT NOTE: input_node is itself included as an element of the output list.  This is so that in some fuzzed
    tests, some literals can remain unaltered.
    :param input_node:                          an ast node object
    :param dev_only_test_mode:                  whether --dev_only_test_mode was set to True when py-holmes was called from the command line
    :param manual_fuzzing_characters:           whether --character_palette_manual was set to True when py-holmes was called from the command line
    :param fuzzing_mutants_count:               the length of the fuzzed list to be returned, including the original value
    :param fuzzing_max_string_changes:          the maximum number of character insertions/removals/deletions to be made if the node represents a string
    :param fuzzing_max_num_added:               the maximum magnitude added or subtracted if the node is a number, after multiplying by the nearest power of ten to the node
    :param fuzzing_num_chance_to_negate:        chance (out of 1) that a number will be multiplied by -1 if it's an int or float (does not affect complex numbers; see fuzzing_max_complex_angle_change instead
    :param fuzzing_max_complex_angle_change:    the maximum angle change in the complex plane that will be made if the node represents a bool
    :param fuzzing_bool_chance_to_flip:         the chance that a bool will be flipped to its opposite if the node represents a bool
    :return:                                    a list of ast node objects.  The first element is guaranteed to be input_node
    """
    # Handle errors
    # input_node not an ast node
    if not isinstance(input_node, AST):
        raise TypeError("input_node must be an AST object")
    # input_node not a type of literal that we want to fuzz
    if type(input_node).__name__ not in ["Constant"]:   # We don't fuzz JoinedStrs themselves, because they contain constants which we fuzz instead
        raise ValueError("node is not a node for a fuzzable literal")
    # dev_only_test_mode not a bool
    if not isinstance(dev_only_test_mode, bool):
        raise TypeError("dev_only_test_mode must be a bool")
    # manual_fuzzing_characters not a bool
    if not isinstance(manual_fuzzing_characters, bool):
        raise TypeError("manual_fuzzing_characters must be a bool")
    # fuzzing_mutants_count not an int
    if not isinstance(fuzzing_mutants_count, int):
        raise TypeError("fuzzing_mutants_count must be an int")
    # fuzzing_mutants_count not positive
    if fuzzing_mutants_count <= 0:
        raise ValueError("fuzzing_mutants_count must be positive")
    # fuzzing_max_string_changes not an int
    if not isinstance(fuzzing_max_string_changes, int):
        raise TypeError("fuzzing_max_string_changes must be an int")
    # fuzzing_max_string_changes not positive
    if fuzzing_max_string_changes <= 0:
        raise ValueError("fuzzing_max_string_changes must be positive")
    # fuzzing_max_num_added not an int
    if not isinstance(fuzzing_max_num_added, int):
        raise TypeError("fuzzing_max_num_added must be an int")
    # fuzzing_max_num_added negative
    if fuzzing_max_num_added < 0:
        raise ValueError("fuzzing_max_num_added must be nonnegative")
    # fuzzing_num_chance_to_negate not a float or int
    if type(fuzzing_num_chance_to_negate) not in [float, int]:
        raise TypeError("fuzzing_num_chance_to_negate must be a float or int")
    # fuzzing_num_chance_to_negate outside the range [0, 1)
    if not (0 <= fuzzing_num_chance_to_negate < 1):
        raise ValueError("fuzzing_num_chance_to_negate must be in the range [0, 1)")
    # fuzzing_max_complex_angle_change not a float or int
    if type(fuzzing_max_complex_angle_change) not in [float, int]:
        raise TypeError("fuzzing_max_complex_angle_change must be a float or int")
    # fuzzing_max_complex_angle_change outside the range [0, pi]
    if not (0 <= fuzzing_max_complex_angle_change <= pi):
        raise ValueError("fuzzing_max_complex_angle_change must be in the range [0, pi], inclusive")
    # fuzzing_bool_chance_to_flip not a float or int
    if type(fuzzing_bool_chance_to_flip) not in [float, int]:
        raise TypeError("fuzzing_bool_chance_to_flip must be a float or int")
    # fuzzing_bool_chance_to_flip outside the range [0, 1)
    if not (0 <= fuzzing_bool_chance_to_flip < 1):
        raise ValueError("fuzzing_bool_chance_to_flip must be in the range [0, 1)")

    # Warnings
    # fuzzing_mutants_count equals 1
    if fuzzing_mutants_count == 1:
        warn("fuzzing_mutants_count equals 1.  This means that no fuzzing will take place, because the original value is included as the first element of the returned list")

    output_nodes = [input_node]
    values_in_output_nodes = [input_node.value]

    # Get the nearest power of ten if the node is numeric
    if type(input_node.value) in [int, float, complex]:
        if input_node.value == 0:
            nearest_power_of_ten = 0    # shrug and assume we're working close to unit (1)
        else:
            nearest_power_of_ten = round(log(abs(input_node.value), 10))

    # Get the size of the fuzz space
    input_node_type = type(input_node.value)
    if input_node_type == int:  # In this case, we just calculate a lower bound for fuzz_space_size
        fuzz_space_size = 1 + ((2*fuzzing_max_num_added) * 10 ** nearest_power_of_ten)
        if 0 < fuzzing_num_chance_to_negate < 1:
            fuzz_space_size *= 2
            if fuzzing_max_num_added * 10 ** nearest_power_of_ten >= abs(input_node.value):
                fuzz_space_size -= 1 + 2 * ((fuzzing_max_num_added * 10 ** nearest_power_of_ten) - abs(input_node.value))    # Account for redundancy between adding/subtracting vs flipping
        fuzz_space_size = max(fuzz_space_size, 0)   # Apply floor
    elif input_node_type == float:
        if fuzzing_max_num_added == 0:
            if fuzzing_num_chance_to_negate == 0:
                fuzz_space_size = 1
            else:
                fuzz_space_size = 2
        else:
            fuzz_space_size = float("inf")
    elif input_node_type == complex:
        if fuzzing_max_num_added == 0 and fuzzing_max_complex_angle_change == 0:
            fuzz_space_size = 1
        else:
            fuzz_space_size = float("inf")
    elif input_node_type == str:    # In this case, we just calculate a lower bound for fuzz_space_size
        if input_node.value == "":
            fuzz_space_size = 26 ** fuzzing_max_string_changes    # TODO: If we change our character palette for empty strings, change this calculation
        else:
            unique_chars = infer_character_palette(input_node.value)
            fuzz_space_size = max(len(unique_chars) ** fuzzing_max_string_changes, len(unique_chars) * fuzzing_max_string_changes + min(fuzzing_max_string_changes, len(input_node.value) + 1))
    elif input_node_type == bool:
        if fuzzing_bool_chance_to_flip == 0:
            fuzz_space_size = 1
        else:
            fuzz_space_size = 2
    else:
        raise RuntimeError(f"don't know how to handle value of type {input_node_type}")

    # If this node represents a string, determine character palette for modifications
    if input_node_type == str:
        if manual_fuzzing_characters:
            unique_chars = input(f"HUMAN HELP NEEDED: Enter a palette of characters for fuzzing '{input_node.value}': ")  # TODO: Currently this doesn't support special characters such as \n and \t.  Include support?
        else:
            unique_chars = infer_character_palette(input_node.value)

    # Fuzz!
    old_value = input_node.value
    while (len(output_nodes) < fuzzing_mutants_count) and not (len(output_nodes) == fuzz_space_size):  # The second condition allows us to escape if the fuzzing space is smaller than the number of fuzz operations requested
        # Pick a new value for a new node
        if type(old_value) == int:
            new_value = old_value + randint(-fuzzing_max_num_added * 10**nearest_power_of_ten, fuzzing_max_num_added * 10**nearest_power_of_ten)
            if random() < fuzzing_num_chance_to_negate:
                new_value *= -1
        elif type(old_value) == float:
            new_value = old_value + uniform(-fuzzing_max_num_added * 10**nearest_power_of_ten, fuzzing_max_num_added * 10**nearest_power_of_ten)
            if random() < fuzzing_num_chance_to_negate:
                new_value *= -1
        elif type(old_value) == complex:
            # Get magnitude and direction
            old_magnitude = abs(old_value)
            old_direction = atan2(old_value.imag, old_value.real)   # Yes, imaginary component is the first argument, because atan2() expects the y component first
            # Fuzz both and generate the corresponding complex number
            new_magnitude = old_magnitude + uniform(-fuzzing_max_num_added * 10**nearest_power_of_ten, fuzzing_max_num_added * 10**nearest_power_of_ten)
            new_magnitude = max(0, new_magnitude)   # Set negative magnitudes to 0
            new_direction = old_direction + uniform(-fuzzing_max_complex_angle_change, fuzzing_max_complex_angle_change)
            new_value = complex(new_magnitude*cos(new_direction), new_magnitude*sin(new_direction))
        elif type(old_value) == str:
            operations = ["insert", "remove", "change"]
            # Determine how many times to perform an operation
            num_operations = randint(1, fuzzing_max_string_changes)
            new_value = old_value
            for _ in range(num_operations):
                operation = choice(operations)
                if operation == "insert":  # Add a character of a kind that was already there.  If no characters were there, add a random lowercase alphabetical character
                    split_index = randint(0, len(new_value))
                    new_char = choice(unique_chars)
                    new_value = insert_char_in_string_at_index(new_char, new_value, split_index)
                elif operation == "remove":     # Remove a random character
                    removal_index = randint(0, max(len(new_value)-1, 0))
                    new_value = remove_char_from_string_at_index(new_value, removal_index)
                elif operation == "change" and old_value != "":     # Change a random character to another character that was in the original string
                    change_index = randint(0, max(len(new_value)-1, 0))
                    new_char = choice(unique_chars)
                    new_value = replace_char_in_string_at_index(new_char, new_value, change_index)
        elif type(old_value) == bool:
            new_value = old_value
            if random() < fuzzing_bool_chance_to_flip:
                new_value = not new_value
        else:
            raise RuntimeError(f"don't know how to handle value of type {str(type(old_value))}")

        # Create a replacement node with the new value instead of the old one
        # If multiple literals on the same line are fuzzed, then that will make col_offset and end_col_offset incorrect.
        # However, this seems not to harm the fuzzed test text.
        new_node = Constant(value=new_value, kind=input_node.kind, lineno=input_node.lineno, col_offset=input_node.col_offset, end_lineno=input_node.end_lineno, end_col_offset=input_node.end_col_offset)

        # Add the new node to output_nodes only if it doesn't match an existing value
        if new_value not in values_in_output_nodes:
            output_nodes.append(new_node)
            values_in_output_nodes.append(new_value)

    # Return!
    return output_nodes


def insert_fuzzed_variant_finding(original_test_content: list, dev_only_test_mode: bool, num_variants_to_find) -> list:
    """Return a version of original_test_content which repeatedly finds fuzzed inputs and shows results.
    Uses an altered version of adversarial sample generation, descending the gradient (d*loss)/(d*input) rather than
    ascending.
    :param original_test_content: newline-separated list containing the source code to the original test method (not the rest of the file)
    """
    # Handle errors (basic)
    # original_test_content not a list
    if not isinstance(original_test_content, list):
        raise TypeError("original_test_content must be a list")
    # original_test_content empty
    if len(original_test_content) == 0:
        raise ValueError("original_test_content must not be empty")
    # First line of original_test_content isn't a function definition line
    if not strip_custom(original_test_content[0], [" ", "\t"], "head").startswith("def "):
        raise ValueError("the first element of original_test_content must be the function definition line")
    # dev_only_test_mode not a bool
    if not isinstance(dev_only_test_mode, bool):
        raise TypeError("dev_only_test_mode must be a bool")
    # num_variants_to_find not an int
    if not isinstance(num_variants_to_find, int):
        raise TypeError("num_variants_to_find must be an int")
    # num_variants_to_find not positive
    if num_variants_to_find <= 0:
        raise ValueError("num_variants_to_find must be positive")

    # Handle errors in how the user's test is written
    original_test_content_as_string = concatenate_list_to_string(original_test_content, "\n")
    # required variable not declared
    for required_variable in ["loss_fn", "x", "label", "model", "indices_to_protect_from_fuzzing", "xmin", "xmax", "adjustment_rate"]:
        if f"{required_variable} =" not in original_test_content_as_string and f"{required_variable}=" not in original_test_content_as_string:
            raise ValueError(f"the user's original test must assign a value for {required_variable}")
    # Not exactly one occurrence of "...self.assert*..."
    if original_test_content_as_string.count("self.assert") != 1:
        raise ValueError("the user's original test must contain exactly one call to a self.assert* function, such as self.assertTrue")
    # tabs used as indentation
    for line in original_test_content:
        if strip_custom(line, [" "], "head").startswith("\t"):
            raise ValueError("the user's original test must use spaces for indentation, not tabs")

    # Defensive copying
    test_content = original_test_content.copy()

    # Define ph_get_activation() at the top of the test method
    definition_line_whitespace_count = leading_spaces_of(test_content[0])
    test_content = [test_content[0]] +\
                   [f"{' ' * (definition_line_whitespace_count + 4)}def ph_get_activation(name):",
                    f"{' ' * (definition_line_whitespace_count + 4)}    def hook(model, input, output):",
                    f"{' ' * (definition_line_whitespace_count + 4)}        ph_activation[name] = output.detach()",
                    f"{' ' * (definition_line_whitespace_count + 4)}    return hook",] + test_content[1:]

    # Make the test method import additional modules as needed
    test_content = [test_content[0]] + [f"{' ' * (definition_line_whitespace_count + 4)}from ph_causal_testing.variant_test_runners import distance_between_neuron_activations"] + test_content[1:]
    test_content = [test_content[0]] + [f"{' ' * (definition_line_whitespace_count + 4)}from colorama import Fore, Style"] + test_content[1:]
    test_content = [test_content[0]] + [f"{' ' * (definition_line_whitespace_count + 4)}import numpy as np"] + test_content[1:]

    # Replace the assert line with a loop which generates fuzzed inputs
    assert_line_index = None
    for ll, line in enumerate(test_content):
        if "self.assert" in line:
            assert_line_index = ll
            assert_line_whitespace_count = leading_spaces_of(line)
            break
    if assert_line_index is None:
        raise RuntimeError("couldn't find a self.assert* call")
    fuzzed_xs_filename = "fuzzed_xs.jsonl"
    loop = []
    # TODO: Could turn this into one append() call to improve speed (probably not by more than a few milliseconds though)
    loop.append(f"{' ' * (assert_line_whitespace_count)}all_xs = []")
    loop.append(f"{' ' * (assert_line_whitespace_count)}all_activation_distances = []")
    loop.append(f"{' ' * (assert_line_whitespace_count)}all_did_pass = []")
    loop.append(f"{' ' * (assert_line_whitespace_count)}all_losses = []")
    loop.append(f"{' ' * (assert_line_whitespace_count)}")
    loop.append(f"{' ' * (assert_line_whitespace_count)}x_original = x.clone()")
    loop.append(f"{' ' * (assert_line_whitespace_count)}")
    loop.append(f"{' ' * (assert_line_whitespace_count)}for modulename in model._modules:")
    loop.append(' ' * (assert_line_whitespace_count) + '''    eval(f"model.{modulename}.register_forward_hook(ph_get_activation('{modulename}'))")''')
    loop.append(f"{' ' * (assert_line_whitespace_count)}ph_activation = dict()")
    loop.append(f"{' ' * (assert_line_whitespace_count)}")
    loop.append(f"{' ' * (assert_line_whitespace_count)}output = model(x)")
    loop.append(f"{' ' * (assert_line_whitespace_count)}loss_original = loss_fn(output, label).item()")
    loop.append(f"{' ' * (assert_line_whitespace_count)}")
    loop.append(f"{' ' * (assert_line_whitespace_count)}ph_activation_original = ph_activation.copy()")
    loop.append(f"{' ' * (assert_line_whitespace_count)}")
    loop.append(f"{' ' * (assert_line_whitespace_count)}optimizer_for_input = torch.optim.Adam([x], lr=adjustment_rate)")
    loop.append(f"{' ' * (assert_line_whitespace_count)}")
    loop.append(f"{' ' * (assert_line_whitespace_count)}# Keep track of the values that the user wishes to protect from fuzzing, if any")
    loop.append(' ' * (assert_line_whitespace_count) + '''protection_indices_to_initial_values = {el: x[el].item() for el in indices_to_protect_from_fuzzing}''')
    loop.append(f"{' ' * (assert_line_whitespace_count)}")
    loop.append(f"{' ' * (assert_line_whitespace_count)}for ii in range({num_variants_to_find}):")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    all_xs.append(x.clone())")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    if not x.requires_grad:")
    loop.append(f"{' ' * (assert_line_whitespace_count)}        x.requires_grad = True")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    optimizer.zero_grad()")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    optimizer_for_input.zero_grad()")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    # Reset activations")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    ph_activation = dict()")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    ")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    output = model(x)")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    loss = loss_fn(output, label)")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    ")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    # Get activation distance from the original and store for future reference")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    activation_distance = distance_between_neuron_activations(ph_activation, ph_activation_original)")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    all_activation_distances.append(activation_distance)")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    ")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    # Get whether passed and store for future reference")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    try:")
    loop.append(f"{' ' * (assert_line_whitespace_count)}        assert output.argmax().item() == label.argmax().item()")
    loop.append(f"{' ' * (assert_line_whitespace_count)}        did_pass = True")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    except AssertionError as err:")
    loop.append(f"{' ' * (assert_line_whitespace_count)}        did_pass = False")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    all_did_pass.append(did_pass)")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    ")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    # Store loss for future reference")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    all_losses.append(loss.item())")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    ")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    loss.backward()")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    optimizer_for_input.step()")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    x.requires_grad = False")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    x[x<xmin] = xmin")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    x[x>xmax] = xmax")
    loop.append(f"{' ' * (assert_line_whitespace_count)}")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    # Enforce any fuzzing protections desired by the user")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    for protection_indices in protection_indices_to_initial_values:")
    loop.append(f"{' ' * (assert_line_whitespace_count)}        x[protection_indices] = protection_indices_to_initial_values[protection_indices]")
    loop.append(f"{' ' * (assert_line_whitespace_count)}")
    loop.append(f"{' ' * (assert_line_whitespace_count)}# Remove the first run from certain lists, since the first run was just the input as-is.")
    loop.append(f"{' ' * (assert_line_whitespace_count)}all_activation_distances = all_activation_distances[1:]")
    loop.append(f"{' ' * (assert_line_whitespace_count)}all_did_pass = all_did_pass[1:]")
    loop.append(f"{' ' * (assert_line_whitespace_count)}all_losses = all_losses[1:]")
    loop.append(f"{' ' * (assert_line_whitespace_count)}all_xs = all_xs[1:]")
    loop.append(f"{' ' * (assert_line_whitespace_count)}# Display a report")
    loop.append(f"{' ' * (assert_line_whitespace_count)}# Get the 3 most similar passing inputs and 3 most similar failing inputs")
    loop.append(f"{' ' * (assert_line_whitespace_count)}most_similar_passing_indices = []")
    loop.append(f"{' ' * (assert_line_whitespace_count)}most_similar_passing_distances = []")
    loop.append(f"{' ' * (assert_line_whitespace_count)}most_similar_failing_indices = []")
    loop.append(f"{' ' * (assert_line_whitespace_count)}most_similar_failing_distances = []")
    loop.append(f"{' ' * (assert_line_whitespace_count)}")
    loop.append(f"{' ' * (assert_line_whitespace_count)}for ii, did_pass in enumerate(all_did_pass):")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    if did_pass:")
    loop.append(f"{' ' * (assert_line_whitespace_count)}        appropriate_indices_list = most_similar_passing_indices")
    loop.append(f"{' ' * (assert_line_whitespace_count)}        appropriate_distances_list = most_similar_passing_distances")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    else:")
    loop.append(f"{' ' * (assert_line_whitespace_count)}        appropriate_indices_list = most_similar_failing_indices")
    loop.append(f"{' ' * (assert_line_whitespace_count)}        appropriate_distances_list = most_similar_failing_distances")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    if len(appropriate_distances_list) < 3:")
    loop.append(f"{' ' * (assert_line_whitespace_count)}        appropriate_indices_list.append(ii)")
    loop.append(f"{' ' * (assert_line_whitespace_count)}        appropriate_distances_list.append(all_activation_distances[ii])")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    elif all_activation_distances[ii] < min(appropriate_distances_list):")
    loop.append(f"{' ' * (assert_line_whitespace_count)}        position_to_replace = np.argmax(appropriate_distances_list)")
    loop.append(f"{' ' * (assert_line_whitespace_count)}        appropriate_indices_list[position_to_replace] = ii")
    loop.append(f"{' ' * (assert_line_whitespace_count)}        appropriate_distances_list[position_to_replace] = all_activation_distances[ii]")
    loop.append(f"{' ' * (assert_line_whitespace_count)}# Create indices_for_showing")
    loop.append(f"{' ' * (assert_line_whitespace_count)}indices_for_showing = most_similar_passing_indices + most_similar_failing_indices")
    loop.append(f"{' ' * (assert_line_whitespace_count)}# Print the original loss")
    loop.append(' ' * (assert_line_whitespace_count) + '''print(f"Original loss: {loss_original}")''')
    loop.append(f"{' ' * (assert_line_whitespace_count)}for index_for_showing in indices_for_showing:")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    # Print whether this result passed or failed, including a color code")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    if all_did_pass[index_for_showing]:")
    loop.append(' ' * (assert_line_whitespace_count) + '''        print(f"{Fore.GREEN}{'/'*24} PASSING TEST {'/'*24}{Style.RESET_ALL}")''')
    loop.append(f"{' ' * (assert_line_whitespace_count)}    else:")
    loop.append(' ' * (assert_line_whitespace_count) + '''        print(f"{Fore.RED}{'/'*24} FAILING TEST {'/'*24}{Style.RESET_ALL}")''')
    loop.append(f"{' ' * (assert_line_whitespace_count)}")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    # Print the loss")
    loop.append(' ' * (assert_line_whitespace_count) + '''    print(f"{Fore.BLUE}{'~' * 16} Loss {'~' * 16}{Style.RESET_ALL}")''')
    loop.append(f"{' ' * (assert_line_whitespace_count)}    print(all_losses[index_for_showing])")
    loop.append(f"{' ' * (assert_line_whitespace_count)}")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    # Print the neuron activation difference")
    loop.append(' ' * (assert_line_whitespace_count) + '''    print(f"{Fore.BLUE}{'~' * 16} Neuron Activation Distance from Original Input {'~' * 16}{Style.RESET_ALL}")''')
    loop.append(f"{' ' * (assert_line_whitespace_count)}    print(all_activation_distances[index_for_showing])")
    loop.append(f"{' ' * (assert_line_whitespace_count)}")
    loop.append(f"{' ' * (assert_line_whitespace_count)}    # Print the new input.  There would be little point highlighting the elements that were changed, because almost always, all elements will be changed.")
    loop.append(' ' * (assert_line_whitespace_count) + '''    print(f"{Fore.BLUE}{'~' * 16} New Input x {'~' * 16}{Style.RESET_ALL}")''')
    loop.append(f"{' ' * (assert_line_whitespace_count)}    print(all_xs[index_for_showing])")

    test_content = overwrite_list_with_list_at_index(loop, test_content, assert_line_index)
    return test_content


def create_fuzzed_test_strings_dl(input_test: TestMethod, dev_only_test_mode: bool, num_tests_to_create=20) -> None:
    """Given a single test of a PyTorch neural network, create a variant of it that finds variant inputs and reports
    results in the style of traditional py-holmes.  Write this new test to a file.
    Only elements of the input to the model are fuzzed.
    :param input_test:              TestMethod object representing the test to be fuzzed
    :param dev_only_test_mode:      whether --dev_only_test_mode was set to True when py-holmes was called from the command line
    :param num_tests_to_create:     the number of fuzzed variants to create from this particular test
    """
    # TODO: If we get stuck (such as if the gradient is flat), detect this, throw a warning, and return early?  Only if this is a realistic concern.
    # Handle errors
    # input_test not a TestMethod object
    if not isinstance(input_test, TestMethod):
        raise TypeError("input_test must be a TestMethod object")
    # dev_only_test_mode not a bool
    if not isinstance(dev_only_test_mode, bool):
        raise TypeError("dev_only_test_mode must be a boolean")
    # num_tests_to_create not an int
    if not isinstance(num_tests_to_create, int):
        raise TypeError("num_tests_to_create must be an int")
    # num_tests_to_create not positive
    if num_tests_to_create <= 0:
        raise ValueError("num_tests_to_create must be positive")

    global name_counter

    # Get ast for input_test
    test_ast = parse(concatenate_list_to_string(minimize_indents(input_test.test_content), between="\n"))

    # Identify nodes for fuzzing and the path through the ast to reach them
    targeter = FuzzTargeterDl(test_ast, minimize_indents(input_test.test_content))
    nodes_for_fuzzing = targeter.fuzzing_targets
    paths_to_nodes_for_fuzzing = targeter.fuzzing_target_paths

    # Build a copy of the test file except the test method in question also repeatedly adjusts the input and finishes by
    # writing a report.  A total of num_tests_to_create tests must be
    # created, if possible
    with open(input_test.test_filepath, "r", encoding="utf-8") as file:
        file_content = file.read().split("\n")
    # Find the stretch that is the test in question
    test_start_index, test_end_index = None, None
    for ll, line in enumerate(file_content):
        if strip_custom(line, [" ", "\t"], "head").startswith(f"def {input_test.test_name}("):
            test_start_whitespace_count = leading_spaces_of(line)
            test_start_index = ll
            break
    if test_start_index is None:
        raise RuntimeError(f"couldn't find definition line for function {input_test.test_name}")
    for ll, line in enumerate(file_content[test_start_index+1:]):
        this_whitespace_count = leading_spaces_of(line)
        if this_whitespace_count <= test_start_whitespace_count:
            test_end_index = ll + test_start_index + 1
            break
    if test_end_index is None:
        test_end_index = len(file_content)

    # Alter the test in question
    test_with_fuzzed_variant_finding = insert_fuzzed_variant_finding(file_content[test_start_index:test_end_index], dev_only_test_mode, num_tests_to_create)
    file_content = overwrite_list_with_list_at_index(test_with_fuzzed_variant_finding, file_content, test_start_index, test_end_index)

    # Write to a file
    fuzzed_output_filename = "test_outputs_fuzzed.py"
    file_content_as_string = concatenate_list_to_string(file_content, between="\n")
    with open(fuzzed_output_filename, "w", encoding="utf-8") as file:
        file.write(file_content_as_string)

    # Tell shared_variables where the file is
    shared_variables.initialize_fuzzed_test_file(fuzzed_output_filename, path.join(getcwd(), fuzzed_output_filename))


def create_fuzzed_test_strings(input_test: TestMethod, dev_only_test_mode: bool, manual_fuzzing_characters: bool, num_tests_to_create=20) -> list:
    """Given a single test, create strings representing fuzzed tests, including the definition line.
    If the test is the original test, then each fuzzed test will alter only one literal.
    The returned list is guaranteed to be free of duplicates.
    :param input_test:                  TestMethod object representing the test to be fuzzed
    :param dev_only_test_mode:          whether --dev_only_test_mode was set to True when py-holmes was called from the command line
    :param manual_fuzzing_characters:   whether --character_palette_manual was set to True when py-holmes was called from the command line
    :param num_tests_to_create:         the number of fuzzed variants to create from this particular test
    :return:                            a list of strings, each representing a fuzzed test
    """
    # Handle errors
    # input_test not a TestMethod object
    if not isinstance(input_test, TestMethod):
        raise TypeError("input_test must be a TestMethod object")
    # dev_only_test_mode not a bool
    if not isinstance(dev_only_test_mode, bool):
        raise TypeError("dev_only_test_mode must be a boolean")
    # manual_fuzzing_characters not a bool
    if not isinstance(manual_fuzzing_characters, bool):
        raise TypeError("manual_fuzzing_characters must be a bool")
    # num_tests_to_create not an int
    if not isinstance(num_tests_to_create, int):
        raise TypeError("num_tests_to_create must be an int")
    # num_tests_to_create not positive
    if num_tests_to_create <= 0:
        raise ValueError("num_tests_to_create must be positive")

    global name_counter

    # Get ast for input_test
    test_ast = parse(concatenate_list_to_string(minimize_indents(input_test.test_content), between="\n"))

    # Identify nodes that are not in [definition line, leading docstring (if any), oracle arguments, and literals that
    # indirectly affect an oracle]
    targeter = FuzzTargeter(test_ast)
    nodes_for_fuzzing = targeter.fuzzing_targets
    paths_to_nodes_for_fuzzing = targeter.fuzzing_target_paths

    # Create a list of new fuzzed values for each of these nodes
    node_to_new_dict = OrderedDict()   # each key is a node from nodes_for_fuzzing; each value is a list of new fuzzed versions of that node.  Keys match the same order as nodes_for_fuzzing
    for this_node in nodes_for_fuzzing:
        node_to_new_dict[this_node] = fuzz_literal_node(this_node, dev_only_test_mode, manual_fuzzing_characters, fuzzing_mutants_count=num_tests_to_create)

    # Repeatedly pick a random combination of fuzzed values, apply it to the tree, and also rename the function
    # using name_counter (globaled), then increment name_counter.  Append the corresponding string to output_strings.
    # Reduce num_tests_to_create if it's currently unrealistically large for these nodes
    if len(node_to_new_dict) == 0:
        num_tests_possible = 0
    else:
        if input_test.is_original:
            num_tests_possible = 0
            for key in node_to_new_dict:
                num_tests_possible += len(node_to_new_dict[key]) - 1
        else:
            num_tests_possible = 1
            for key in node_to_new_dict:
                num_tests_possible *= len(node_to_new_dict[key])
    num_tests_to_create = min(num_tests_to_create, num_tests_possible)
    if num_tests_to_create == 0:
        raise RuntimeError("no valid literals to fuzz in this test")
    # Build combinations to write...
    combinations_to_write = []
    # ...if this is the original test, alter only one literal in each fuzzed variant
    if input_test.is_original:
        while len(combinations_to_write) < num_tests_to_create:
            node_to_alter = choice([key for key in node_to_new_dict])
            tentative_combination = []
            for key in node_to_new_dict:
                if key is node_to_alter:
                    tentative_combination.append(choice(node_to_new_dict[key][1:]))     # We use 1: to force alteration
                else:
                    tentative_combination.append(node_to_new_dict[key][0])
            if tentative_combination not in combinations_to_write:
                combinations_to_write.append(tentative_combination)
    # ...if this is NOT the original test, fuzz all nodes freely
    else:
        while len(combinations_to_write) < num_tests_to_create:
            # TODO: Ensure the original test is never added (ie that we never use the exact combination of literals that was in the original test)
            tentative_combination = [choice(node_to_new_dict[key]) for key in node_to_new_dict]
            if tentative_combination not in combinations_to_write:
                combinations_to_write.append(tentative_combination)
    # Write the combinations that we've chosen
    output_strings = []
    for combination in combinations_to_write:   # combination is a list replacing one fuzzed replacement node per node to be fuzzed
        # Create a shallow copy of the original ast
        shallow_ast = parse(to_source(test_ast))
        # Create shallow copies of each node in combination
        as_source_combination = []
        for element in combination:
            element_as_source = to_source(element)
            if element_as_source.endswith("\n"):
                element_as_source = element_as_source[:-1]
            as_source_combination.append(element_as_source)
        shallow_combination = [parse(element).body[0].value for element in as_source_combination]   # Using .body[0].value breaks through the module wrapper that parse() creates
        # For each replacement node in shallow_combination, set its match in shallow_ast to that node instead
        actuator = FuzzActuator(root=shallow_ast, paths_to_change=paths_to_nodes_for_fuzzing, replacement_nodes=shallow_combination)
        shallow_ast = actuator.generic_visit(shallow_ast, path_to_node=None)
        # Rename the function name in the ast and increment name_counter.  Use slightly different names for fuzzed
        # variants of the original test vs fuzzed variants of found tests, so that they can be distinguished.
        if input_test.is_original:
            shallow_ast.body[0].name = f"test_fuzzed_{str(name_counter)}_from_original"
        else:
            shallow_ast.body[0].name = f"test_fuzzed_{str(name_counter)}_from_found"
        name_counter += 1
        # Create a string and append it to output_strings
        shallow_ast_as_string = to_source(shallow_ast)
        output_strings.append(shallow_ast_as_string + "\n\n")
    # Return!
    return output_strings


def fuzz_tests(input_test_list: list, original_absolute_path: str, dev_only_test_mode: bool, manual_fuzzing_characters: bool, num_tests=50):
    """Return a list of fuzzed tests based off of input_test_list.  Also post the name and filepath of the file
    containing these tests to shared_variables.  The returned list might contain duplicates if two separate tests
    happened to be fuzzed in a way that produced the same test.
    Roughly half of the returned tests will be variants of the original test.  If no tests are provided other than the
    original test, then all of the returned tests will be variants of the original test.
    :param input_test_list:             list of TestMethod objects, containing *exactly one* original test
    :param original_absolute_path:      absolute filepath to the original test; the output file is written to the same directory
    :param dev_only_test_mode:          whether --dev_only_test_mode was set to True when py-holmes was called from the command line
    :param manual_fuzzing_characters:   whether --character_palette_manual was set to True when py-holmes was called from the command line
    :param num_tests:                   how many tests to provide
    :return:                            If in dl mode, returns None.  Else, returns (list of TestMethod objects for fuzzed variants of original test, list of TestMethod objects for fuzzed variants of other found tests)
    """
    # Handle errors
    # input_test_list not a list
    if not isinstance(input_test_list, list):
        raise TypeError("input_test_list must be a list")
    # input_test_list contains non-TestMethod element
    for element in input_test_list:
        if not isinstance(element, TestMethod):
            raise TypeError("all elements in input_test_list must be TestMethod objects")
    # input_test_list empty
    if len(input_test_list) == 0:
        raise ValueError("input_test_list must not be empty")
    # original_absolute_path not a string
    if not isinstance(original_absolute_path, str):
        raise TypeError("original_absolute_path must be a string")
    # original_absolute_path not an absolute path
    if original_absolute_path != path.abspath(original_absolute_path):
        raise ValueError("original_absolute_path must be an absolute path")
    # dev_only_test_mode not a bool
    if not isinstance(dev_only_test_mode, bool):
        raise TypeError("dev_only_test_mode must be a boolean")
    # manual_fuzzing_characters not a bool
    if not isinstance(manual_fuzzing_characters, bool):
        raise TypeError("manual_fuzzing_characters must be a bool")
    # num_tests not an int
    if not isinstance(num_tests, int):
        raise TypeError("num_tests must be an int")
    # num_tests not positive
    if num_tests <= 0:
        raise ValueError("num_tests must be positive")
    # number of original tests does not equal one
    original_test_counter = 0
    for test in input_test_list:
        if test.is_original:
            original_test_counter += 1
    if original_test_counter != 1:
        raise ValueError("exactly one test in input_test_list must be an input test")

    # Reset name_counter
    global name_counter
    name_counter = 0

    # Determine how many tests to create from each input test.  We prioritize tests earlier in the list.
    # Additionally, for each test, we either fuzz that test once or throw it out
    # Identify the original test
    for ii in range(len(input_test_list)):
        this_test = input_test_list[ii]
        if this_test.is_original:
            original_test_index = ii
            break
    # If this is the only test...
    if len(input_test_list) == 1:
        num_by_test = [num_tests]
    # If there are other tests...
    else:
        num_by_test = [0 for _ in range(len(input_test_list))]
        num_original_tests_to_make = ceil(num_tests/2)
        num_by_test[original_test_index] = num_original_tests_to_make
        assigned = num_original_tests_to_make
        index_of_interest = 0
        while assigned < num_tests:
            if index_of_interest != original_test_index:
                num_by_test[index_of_interest] += 1
                assigned += 1
            index_of_interest = (index_of_interest + 1) % len(num_by_test)

    # If in dev-only test mode, print how many fuzz variants we're going to make of each test
    if dev_only_test_mode:
        print("BEGIN FUZZ VARIANT TALLY")
        print("Is original\t\tTestMethod\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tNumber of variants")
        for ii in range(len(input_test_list)):
            this_test = input_test_list[ii]
            this_num = num_by_test[ii]
            print(f"{this_test.is_original}\t\t\t{this_test}\t\t{this_num}")
        print("END FUZZ VARIANT TALLY")

    # Check whether in dl mode
    shared_variables.initialize()
    dl = shared_variables.dl
    if dl and len(input_test_list) > 1:
        raise ValueError("input_test_list must not be more than 1 when running in dl mode")

    # Create fuzzed tests
    if dl:
        create_fuzzed_test_strings_dl(input_test_list[0], dev_only_test_mode, num_tests_to_create=num_tests)
        return
    all_tests_string = ""
    for tt in range(len(input_test_list)):
        if num_by_test[tt] > 0:
            this_input_test = input_test_list[tt]
            fuzzed_from_this_input_test = create_fuzzed_test_strings(this_input_test, dev_only_test_mode, manual_fuzzing_characters, num_tests_to_create=num_by_test[tt])
            for test_string in fuzzed_from_this_input_test:
                all_tests_string += test_string

    # Indent every line
    all_tests_list = all_tests_string.split("\n")
    for ii in range(len(all_tests_list)):
        all_tests_list[ii] = "    " + all_tests_list[ii]
    # Encase in unittest class
    all_tests_list.insert(0, "class TestFuzzed(unittest.TestCase):")
    # For each input test method, add all its requisite imports to the top of this new file, in absolute form.  Also add
    # "import unittest\n" if not already a top-of-file import
    all_tests_list.insert(0, "")
    imports_list = ["import unittest"]     # The trailing "\n" is inserted later
    for this_input_test in input_test_list:
        for this_requisite_import in this_input_test.requisite_import_lines:
            if this_requisite_import not in imports_list:
                imports_list.append(this_requisite_import)
    for this_module_level_import in imports_list:
        all_tests_list.insert(0, this_module_level_import)

    # Finally convert back to string
    all_tests_string = concatenate_list_to_string(all_tests_list, between="\n")

    # Write to a file (test_outputs_fuzzed.py)
    fuzzed_output_path = path.join(path.dirname(original_absolute_path), fuzzed_output_filename)
    with open(fuzzed_output_path, "w", encoding="utf-8") as file:
        file.write(all_tests_string)

    # Create TestMethod objects for all fuzzed tests, then separate fuzzed variants of the original test from fuzzed
    # variants of other found tests.
    fuzzed_test_method_objects = find_all_test_methods_in_file(fuzzed_output_path, origin="fuzzed")
    fuzzed_from_original = [element for element in fuzzed_test_method_objects if "from_original" in element.test_name]
    fuzzed_from_found = [element for element in fuzzed_test_method_objects if "from_original" not in element.test_name]
    output = fuzzed_from_original, fuzzed_from_found

    # Post file name and path to shared_variables
    shared_variables.initialize_fuzzed_test_file(fuzzed_output_filename, fuzzed_output_path)

    # Return!
    return output
