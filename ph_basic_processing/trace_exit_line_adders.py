"""Classes and functions for adding exit lines to execution traces.
The following parameters are assumed when the trace.Trace object is produced:
(count=0, trace=1, countfuncs=0, countcallers=0, ignoremods=(), ignoredirs=(), infile=None, outfile=None, timing=False)
"""


from ph_basic_processing.parsers import leading_spaces_of, get_method_name_from_definition_line, get_class_name_from_definition_line, starts_with_one_of, index_of_last_substring_in_string, begins_with_def_or_class, get_modulename_from_functioncall, get_funcname_from_functioncall, is_paren_balanced, strip_file_extension
from ph_basic_processing.stripping import strip_custom
from ph_original_test_result_generation.ph_dir_and_file_finders.pathfinders import FILES_ALREADY_READ, get_absolute_path
from ph_variable_sharing import shared_variables

from warnings import warn


#
# GLOBALED VARIABLES
#
function_stack = []     # For keeping track of the layers of functions we're inside of.  Each entry is a sublist where the first entry is a modulename, and the second is a funcname


#
# CLASSES
#
class ParsedTraceline:
    """Basic container for file and line number information of a traceline.
    Attributes are as follows:
    self.category: str.                     The general meaning of the line in the execution trace, ie blank vs linelog vs function call.
    self.traceline: str.                    The content of the line; what we already had before parsing.
    self.file_no_extension: str.            The file containing the line, if the category of the line is linelog.
    self.file_with_extension: str.          Same as file_no_extension, but with a file extension attached, if the category of the line is linelog.
    self.line_number: int.                  The line in the file on which the line can be found, counting starting at 1, if the category of the line is linelog.
    self.line_content: str.                 The content of the file on line_number, if the category of the line is linelog.
    self.innermost_container: str.          The name of the innermost class, function, or just <module> that contains this line, if the category of the line is linelog.
    self.innermost_container_type: str.     Whether the innermost container is a class, func, or file, if the category of the line is linelog.
    self.modulename: str.                   The modulename mentioned, if the category of the line is functioncall.
    self.funcname: str.                     The funcname mentioned, if the category of the line is functioncall.
    self.file_path: str.                    The absolute path to the file, if the category of this line is linelog.
    """

    def __init__(self, traceline: str) -> None:
        """Build attributes given the content of the traceline we're parsing"""
        # Assign attributes
        # Set category
        self.category = None
        if ":" in traceline:
            if " --- modulename: " in traceline and ", funcname: " in traceline and traceline.index(" --- modulename: ") < index_of_last_substring_in_string(traceline, ", funcname: "):
                self.category = "functioncall"
                # For this category, we also trim everything before " --- modulename: "
                traceline = traceline[traceline.index(" --- modulename: "):]
                # Set important variants and indices
                traceline_until_colon = traceline[:traceline.index(":")]
                traceline_after_colon = traceline[traceline.index(":") + 1:]
            elif ":" in traceline and ".py(" in traceline:
                self.category = "linelog"
                # For this category, we also trim everything before the last space before the last ".py("
                index_last_dotpyparen = index_of_last_substring_in_string(traceline, ".py(")
                index_space_for_cut = None
                for ii in range(index_last_dotpyparen-1, -1, -1):   # Walk backward until we find a space
                    if traceline[ii] == " ":
                        index_space_for_cut = ii
                        break
                if index_space_for_cut == None:
                    index_space_for_cut = -1
                traceline = traceline[index_space_for_cut+1:]
                # Set important variants and indices
                traceline_until_colon = traceline[:traceline.index(":")]
                traceline_after_colon = traceline[traceline.index(":") + 1:]
        else:
            traceline_until_colon = traceline
            traceline_after_colon = ""
            if traceline == "":
                self.category = "blank"
        if self.category is None:
            warn("traceline does not look like an execution trace line (this is okay if it's printed content): " + traceline)
        # Set traceline
        self.traceline = traceline
        # Set file_with_extension and file_no_extension
        if self.category == "blank":
            pass
        elif self.category == "linelog":
            index_period_closest_before_first_colon = len(traceline_until_colon) - traceline_until_colon[::-1].index(".") - 1
            index_open_paren_closest_before_first_colon = len(traceline_until_colon) - traceline_until_colon[::-1].index("(") - 1
            self.file_no_extension = traceline_until_colon[:index_period_closest_before_first_colon]
            self.file_with_extension = traceline_until_colon[:index_open_paren_closest_before_first_colon]
        elif self.category == "functioncall":
            pass
        # Set line_number
        if self.category == "blank":
            pass
        elif self.category == "linelog":
            index_closed_paren_closest_before_first_colon = len(traceline_until_colon) - traceline_until_colon[::-1].index(")") - 1
            self.line_number = int(traceline_until_colon[index_open_paren_closest_before_first_colon + 1: index_closed_paren_closest_before_first_colon])
        elif self.category == "functioncall":
            pass
        # Set line_content
        if self.category == "blank":
            pass
        elif self.category == "linelog":
            if len(traceline_after_colon) > 1:
                self.line_content = traceline_after_colon[1:]
            else:
                self.line_content = ""
        elif self.category == "functioncall":
            pass
        # Set innermost_container
        if self.category == "blank":
            pass
        elif self.category == "linelog":
            self.innermost_container, self.innermost_container_type = self.find_innermost_container()
            self.file_path = FILES_ALREADY_READ[self.file_with_extension][0]
        elif self.category == "functioncall":
            pass
        # Set file_path
        if self.category == "blank":
            pass
        elif self.category == "linelog":
            self.file_path = FILES_ALREADY_READ[self.file_with_extension][0]
        elif self.category == "functioncall":
            pass
        # Set modulename
        if self.category == "blank":
            pass
        elif self.category == "linelog":
            pass
        elif self.category == "functioncall":
            self.modulename = get_modulename_from_functioncall(self.traceline)
        # Set funcname
        if self.category == "blank":
            pass
        elif self.category == "linelog":
            pass
        elif self.category == "functioncall":
            self.funcname = get_funcname_from_functioncall(self.traceline)

    def find_innermost_container(self, count_def_line_as_next_container=False):
        """Find the innermost class or function that contains the line represented by this object, as well as the type
        of that container (class, func, or file).
        If count_def_line_as_next_container == False, then a function definition line ("def ") or class definition line
        ("class ") will show an inner container of itself.  If count_def_line_as_next_container == True, then such a
        line will show an inner container of the next container containing it, possibly <module>
        """
        line_number_as_index = self.line_number - 1

        # Get the content of the file
        # If in the cache, grab it as long as the line matches what's in the cache
        if self.file_with_extension in FILES_ALREADY_READ and len(FILES_ALREADY_READ[self.file_with_extension][1]) >= line_number_as_index + 1 and FILES_ALREADY_READ[self.file_with_extension][1][line_number_as_index] == self.line_content + "\n":
            file_content = FILES_ALREADY_READ[self.file_with_extension][1]
        # Else, read it from the file
        else:
            with open(get_absolute_path(self.file_with_extension, self.line_content, self.line_number), "r", encoding="utf-8") as file:
                file_content = file.readlines()

        # If not count_def_line_as_next_container, and the line is itself a function definition line (starting with def) or a class definition line (starting wtih class), then this is the innermost container
        if not count_def_line_as_next_container:
            line = file_content[line_number_as_index]
            line = strip_custom(line, ["\t", " "], "head")
            if line.startswith("def "):
                container_name = get_method_name_from_definition_line(line)
                return container_name, "func"
            elif line.startswith("class "):
                container_name = get_class_name_from_definition_line(line)
                return container_name, "class"
        # Else, search upward, by beginning at the line just above line_number, then going upward one line at a time until we find a line that starts with "{ , \t}*def " or "{ , \t}*class " and that has fewer leading spaces/tabs than the line at line_number
        leading_spaces_for_line_number = leading_spaces_of(file_content[line_number_as_index])
        container_name = None
        for ii in range(line_number_as_index-1, -1, -1):
            this_line = file_content[ii]
            # If this line has fewer leading spaces/tabs than the line at line number:
            if leading_spaces_of(this_line) < leading_spaces_for_line_number:
                # If, after stripping leading tabs and spaces, this line starts with "def " or "class ":
                this_line_no_leading_whitespace = strip_custom(this_line, ["\t", " "], "head")
                if this_line_no_leading_whitespace[:4] == "def ":
                    # This must be the line that we want.  Get the function name and return.
                    container_name = get_method_name_from_definition_line(this_line)
                    return container_name, "func"
                elif this_line_no_leading_whitespace[:6] == "class ":
                    # This must be the line that we want.  Get the class name and return.
                    container_name = get_class_name_from_definition_line(this_line)
                    return container_name, "class"

        # If we've reached this point, then the line's innermost container is the file itself, so return "<module>"
        if container_name is None:
            return "<module>", "file"


#
# HELPER FUNCTIONS
#
def add_exit_lines_to_trace(input_trace: str):
    """Return the following:
    1. A version of input_trace with a line added to indicate each exit of a function
    2. A list of indices of linelog lines that are descended from non-ignored user code.
    3. A list of all user-written and py-holmes modules seen.  Holmesignored user modules are not excluded from this list.
    This function also alters importbootstrap lines and generally makes the trace cleaner and more legible.
    """
    global function_stack

    # Convert input to list
    input_trace = input_trace.split("\n")

    # Create outputs (blank for now)
    output_trace = []
    output_non_ignored_user_descendant_indices = []

    # Parse every line of the input trace
    parsed_lines = [ParsedTraceline(line) for line in input_trace]

    # Looping through all lines:
    function_stack = []     # Contains sublists of length 3, where the first subentry is a modulename, the second is a funcname, and the third is True if non-ignored user code, else False
    ll_including_added_lines = -1    # Gets incremented an extra time each time we add an exit line.  Helps generate output_non_ignored_user_descendant_indices
    for ll in range(len(input_trace)):
        ll_including_added_lines += 1
        line_parsed = parsed_lines[ll]
        # Add the cleaned-up version of the line to the output.  In a moment, we might add an exit line after it
        output_trace.append(line_parsed.traceline)

        # Append to the function stack if appropriate
        if line_parsed.category == "functioncall":
            line_parsed_is_non_ignored_user_file = (line_parsed.modulename + ".py" in FILES_ALREADY_READ and FILES_ALREADY_READ[line_parsed.modulename + ".py"][2])
            function_stack.append([line_parsed.modulename, line_parsed.funcname, line_parsed_is_non_ignored_user_file])

        # If this line is a linelog and is a descendant of non-ignored user code, add its index to output_ignored_user_descendant_indices
        if line_parsed.category == "linelog":
            for this_ancestor in function_stack:
                if this_ancestor[2]:  # If this ancestor is non-ignored user code:
                    output_non_ignored_user_descendant_indices.append(ll_including_added_lines)
                    break

        # If there is a line after this one:
        if ll+1 != len(input_trace):
            next_line_parsed = parsed_lines[ll+1]
            # If both this and the next line are of linelog category and have a different innermost function/class/module container, UNLESS (one is a function or class definition (starting with "def " or "class ") and is immediately contained by the other, OR they are both definition lines), add as many lines as it takes to get back to this module
            # (Handles functions ending in a normal way, including by returns that don't call anything)
            one_is_definition_immediately_contained_by_the_other = None
            both_are_definition_lines = None
            both_are_linelog_with_different_innermost = line_parsed.category == "linelog" and next_line_parsed.category == "linelog" and (next_line_parsed.innermost_container != line_parsed.innermost_container or (next_line_parsed.innermost_container == "<module>" and line_parsed.innermost_container == "<module>" and next_line_parsed.file_path != line_parsed.file_path))
            # Calculate the above booleans in the most efficient order, so that we can skip calculating some of them when it isn't necessary
            if both_are_linelog_with_different_innermost:
                one_is_definition_immediately_contained_by_the_other = ((starts_with_one_of(strip_custom(next_line_parsed.line_content, ["\t", " "], "head"), ["def ", "class "]) and next_line_parsed.find_innermost_container(count_def_line_as_next_container=True)[0] == line_parsed.innermost_container) or (starts_with_one_of(strip_custom(line_parsed.line_content, ["\t", " "], "head"), ["def ", "class "]) and line_parsed.find_innermost_container(count_def_line_as_next_container=True)[0] == next_line_parsed.innermost_container))
                if one_is_definition_immediately_contained_by_the_other == False:
                    both_are_definition_lines = (begins_with_def_or_class(strip_custom(next_line_parsed.line_content, ["\t", " "], "head")) and begins_with_def_or_class(strip_custom(line_parsed.line_content, ["\t", " "], "head")))
            if both_are_linelog_with_different_innermost and not (one_is_definition_immediately_contained_by_the_other or both_are_definition_lines):
                while len(function_stack) > 0 and not (hasattr(next_line_parsed, "innermost_container") and next_line_parsed.innermost_container == function_stack[-1][1]):
                    output_trace.append(exit_line(function_stack[-1][1], function_stack[-1][0] + ".py"))
                    ll_including_added_lines += 1   # Because we've just added an extra line beyond the default
            # Elif this line is a linelog and the next line is a functioncall, and this line's content starts with "return " (after removing whitespace), add an exit line.
            elif line_parsed.category == "linelog" and next_line_parsed.category == "functioncall" and strip_custom(line_parsed.line_content, ["\t", " "], "head").startswith("return ") and is_paren_balanced(line_parsed.line_content):
                if len(function_stack) > 0: # TODO: Questionable if statement
                    output_trace.append(exit_line(function_stack[-1][1], function_stack[-1][0] + ".py"))
                    ll_including_added_lines += 1  # Because we've just added an extra line beyond the default
            # Elif this line is of functioncall category and the next line is of linelog category and does not share a module name and was not called by the prior line, add as many exit lines as it takes to get back to this module
            # (Handles functions beginning and ending without running a single line)
            elif line_parsed.category == "functioncall" and next_line_parsed.category == "linelog" and line_parsed.modulename != next_line_parsed.traceline[:next_line_parsed.traceline.index(".py(")] and not (line_parsed.funcname == next_line_parsed.innermost_container):
                while len(function_stack) > 0 and next_line_parsed.innermost_container != function_stack[-1][1]:
                    output_trace.append(exit_line(function_stack[-1][1], function_stack[-1][0] + ".py"))  # Even if line_parsed isn't a .py file, this doesn't make a difference; exit_line() will just remove the .py extension
                    ll_including_added_lines += 1  # Because we've just added an extra line beyond the default
        # Else, this is the last line of the trace.
        else:
            pass

    # Grab the list of user_modules_seen (holmesignored files are not excluded from this list)
    user_and_py_holmes_modules_seen = []
    for key in FILES_ALREADY_READ:
        if FILES_ALREADY_READ[key][3]:  # If the file is a user file:
            user_and_py_holmes_modules_seen.append(strip_file_extension(key))

    # Convert output to string and return
    output_trace_string = ""
    for entry in output_trace:
        output_trace_string += entry + "\n"
    return output_trace_string, output_non_ignored_user_descendant_indices, user_and_py_holmes_modules_seen


def exit_line(func_name: str, module_with_extension: str):
    """Return a formatted string to indicate exit from a function or class.
    Also pop from the function stack and ensure that it matches the exit line.
    container_name:         The name of the function or class being exited.
    module_with_extension:  The name of the file containing the function or class being exited.  Include a file extension, so that unnamed files "eg '.py'" aren't mistaken for a blank input argument.
    """
    global function_stack

    # Handle errors
    # func_name empty
    if func_name == "" or func_name is None:
        raise ValueError("name cannot be empty or null")
    # module empty
    if module_with_extension == "" or module_with_extension is None:
        raise ValueError("module cannot be empty or null")

    # Create module_no_extension from module_with_extension
    index_of_last_period = len(module_with_extension) - module_with_extension[::-1].index(".") - 1
    module_no_extension = module_with_extension[:index_of_last_period]

    # If func_name contains a .py file extension (nonsensical; not even a file), remove it
    if func_name.endswith(".py"):
        func_name = func_name[:-3]

    # Pop from the function stack and ensure that it matches this exit line
    removed_from_function_stack = function_stack.pop()
    if removed_from_function_stack[0] != module_no_extension or removed_from_function_stack[1] != func_name:
        raise RuntimeError("a function was exited that broke that stacklike discipline of function_stack")


    # Return formatted string.
    # We always say funcname, rather than class name or module name, even if the innermost container is a class, because this is what
    # the existing trace syntax does.
    return (" ||| exiting modulename: " + module_no_extension + ", funcname: " + func_name)


def remove_before_user_runtime(tracer_result_: str) -> str:
    """Return a modified version of tracer_result_ where all lines before the user's runtime are removed."""
    # Handle errors
    # tracer_result_ not a string
    if not isinstance(tracer_result_, str):
        raise TypeError("tracer_result_ must be a string")
    # tracer_result_ empty
    if len(tracer_result_) == 0:
        raise ValueError("tracer_result_ must not be empty")

    # Grab the test filename and method
    shared_variables.initialize()
    test_filename_without_file_extension = shared_variables.filename_no_file_extension
    test_method = shared_variables.test_method

    # Split tracer_result into a list
    tracer_result_ = tracer_result_.split("\n")

    # Get index of first entry into the user's test method
    index_first_entry = None
    for ll in range(len(tracer_result_)):
        this_line = tracer_result_[ll]
        if this_line.startswith(f" --- modulename: {test_filename_without_file_extension}, "):
            if get_funcname_from_functioncall(this_line) == test_method:
                index_first_entry = ll
                break
    if index_first_entry is None:
        raise RuntimeError(f"no entry into user's test file '{test_filename_without_file_extension}' found")

    # Shave everything before
    tracer_result_ = tracer_result_[index_first_entry:]

    # Turn tracer_result into a string again
    new_tracer_result = ""
    for entry in tracer_result_:
        new_tracer_result += entry + "\n"

    # Return
    return new_tracer_result


def remove_after_user_runtime(tracer_result_: str, non_ignored_user_code_indices_):
    """Remove tracelines after the user's runtime, and adjust non_ignored_user_code_indices_ accordingly.
    Then return the new values for tracer_result_ and non_ignored_user_code_indices_.
    """
    # Handle errors
    # tracer_result_ not a string
    if not isinstance(tracer_result_, str):
        raise TypeError("tracer_result_ must be a string")
    # tracer_result_ empty
    if len(tracer_result_) == 0:
        raise ValueError("tracer_result_ must not be empty")
    # non_ignored_user_code_indices_ not a list
    if not isinstance(non_ignored_user_code_indices_, list):
        raise TypeError("non_ignored_user_code_indices_ must be a list")
    # non_ignored_user_code_indices_ contains non-int element
    for element in non_ignored_user_code_indices_:
        if not isinstance(element, int):
            raise TypeError("all elements in non_ignored_user_code_indices_ must be ints")

    # Grab the test filename and method
    shared_variables.initialize()
    test_filename_without_file_extension = shared_variables.filename_no_file_extension
    test_method = shared_variables.test_method

    # Split tracer_result into a list
    tracer_result_ = tracer_result_.split("\n")

    # Get index of last exit out of the user's test method
    index_last_exit = None
    for ll in range(len(tracer_result_)-1, -1, -1):
        this_line = tracer_result_[ll]
        if this_line.startswith(f" ||| exiting modulename: {test_filename_without_file_extension}, "):
            if get_funcname_from_functioncall(this_line) == test_method:
                index_last_exit = ll
                break
    if index_last_exit is None:
        raise RuntimeError(f"no exit from user's test file '{test_filename_without_file_extension}' found")

    # Shave everything after
    tracer_result_ = tracer_result_[:index_last_exit+1]

    # Remove elements of non_ignored_user_code_indices_ that go beyond the list
    new_non_ignored_user_code_indices = [element for element in non_ignored_user_code_indices_ if element < len(tracer_result_)]

    # Turn tracer_result into a string again
    new_tracer_result = ""
    for entry in tracer_result_:
        new_tracer_result += entry + "\n"

    # Return all
    return new_tracer_result, new_non_ignored_user_code_indices


def remove_before_function_runtime(tracer_result_: str, function_to_crop_to: str, function_filename_no_extension: str) -> str:
    """Return a modified version of tracer_result_ where all lines before the first entry of function_to_crop_to are
    removed.
    :param tracer_result_:                      string representing the execution trace
    :param function_to_crop_to:                 the name of the function before which all execution trace lines should be removed
    :param function_filename_no_extension:      the filename of the aforementioned function.  This should not be a path; it should not include mention of the folders containing this file.
    """
    # Handle errors
    # tracer_result_ not a string
    if not isinstance(tracer_result_, str):
        raise TypeError("tracer_result_ must be a string")
    # tracer_result_ empty
    if len(tracer_result_) == 0:
        raise ValueError("tracer_result_ must not be empty")
    # function_to_crop_to not a string
    if not isinstance(function_to_crop_to, str):
        raise TypeError("function_to_crop_to must be a string")
    # function_to_crop_to empty
    if len(function_to_crop_to) == 0:
        raise ValueError("function_to_crop_to must not be empty")
    # function_filename_no_extension not a string
    if not isinstance(function_filename_no_extension, str):
        raise TypeError("function_filename_no_extension must be a string")
    # function_filename_no_extension empty
    if len(function_filename_no_extension) == 0:
        raise ValueError("function_filename_no_extension must not be empty")

    # Split tracer_result into a list
    tracer_result_ = tracer_result_.split("\n")

    # Get index of first entry into function_to_crop_to
    index_first_entry = None
    for ll in range(len(tracer_result_)):
        this_line = tracer_result_[ll]
        if this_line.startswith(f" --- modulename: {function_filename_no_extension}, "):
            if get_funcname_from_functioncall(this_line) == function_to_crop_to:
                index_first_entry = ll
                break
    if index_first_entry is None:
        raise RuntimeError("no entry into this function found")

    # Shave everything before
    tracer_result_ = tracer_result_[index_first_entry:]

    # Turn tracer_result into a string again
    new_tracer_result = ""
    for entry in tracer_result_:
        new_tracer_result += entry + "\n"

    # Return
    return new_tracer_result


def remove_after_function_runtime(tracer_result_: str, function_to_crop_to: str, function_filename_no_extension: str) -> str:
    """Return a modified version of tracer_result_ where all lines after the final exit of function_to_crop_to are
    removed.
    :param tracer_result_:                      string representing the execution trace
    :param function_to_crop_to:                 the name of the function before which all execution trace lines should be removed
    :param function_filename_no_extension:      the filename of the aforementioned function.  This should not be a path; it should not include mention of the folders containing this file.
    """
    # Handle errors
    # tracer_result_ not a string
    if not isinstance(tracer_result_, str):
        raise TypeError("tracer_result_ must be a string")
    # tracer_result_ empty
    if len(tracer_result_) == 0:
        raise ValueError("tracer_result_ must not be empty")
    # function_to_crop_to not a string
    if not isinstance(function_to_crop_to, str):
        raise TypeError("function_to_crop_to must be a string")
    # function_to_crop_to empty
    if len(function_to_crop_to) == 0:
        raise ValueError("function_to_crop_to must not be empty")
    # function_filename_no_extension not a string
    if not isinstance(function_filename_no_extension, str):
        raise TypeError("function_filename_no_extension must be a string")
    # function_filename_no_extension empty
    if len(function_filename_no_extension) == 0:
        raise ValueError("function_filename_no_extension must not be empty")

    # Split tracer_result into a list
    tracer_result_ = tracer_result_.split("\n")

    # Get index of last exit out of the user's test method
    index_last_exit = None
    for ll in range(len(tracer_result_)-1, -1, -1):
        this_line = tracer_result_[ll]
        if this_line.startswith(f" ||| exiting modulename: {function_filename_no_extension}, "):
            if get_funcname_from_functioncall(this_line) == function_to_crop_to:
                index_last_exit = ll
                break
    if index_last_exit is None:
        raise RuntimeError("no exit from this function found")

    # Shave everything after
    tracer_result_ = tracer_result_[:index_last_exit+1]

    # Turn tracer_result into a string again
    new_tracer_result = ""
    for entry in tracer_result_:
        new_tracer_result += entry + "\n"

    # Return all
    return new_tracer_result
