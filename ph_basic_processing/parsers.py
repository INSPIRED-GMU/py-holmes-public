"""Classes and functions for parsing strings."""

import string
from fnmatch import fnmatch
from os import path
from Levenshtein import distance as lev

from ph_variable_sharing import shared_variables
from ph_basic_processing.stripping import strip_custom


def strip_file_extension(input_string: str):
    """Remove the last period and whatever follows from input_string."""
    # Handle errors
    # input_string not a string
    if not isinstance(input_string, str):
        raise TypeError("input_string must be a string")
    # input_string empty
    if len(input_string) == 0:
        raise ValueError("input_string must not be empty")
    # input_string doesn't contain a period
    if "." not in input_string:
        raise ValueError("input_string must contain a period")

    # Run
    last_period_index = index_of_last_substring_in_string(input_string, ".")
    return input_string[:last_period_index]


def leading_spaces_of(input_string: str) -> int:
    """Return the number of leading spaces in input_string.  Tabs count for spaces_per_tab spaces."""
    # Handle errors
    # input_string not a string
    if not isinstance(input_string, str):
        raise TypeError("input_string must be a string")

    # Return the number of leading spaces in input_string
    from ph_variable_sharing import shared_variables
    shared_variables.initialize()
    try:
        spaces_per_tab = shared_variables.tatosp
    except AttributeError:   # TODO: I added this block for easier test running (so that we don't have to call py_holmes.py from the command line to set tatosp).  But it's messy.  Do something about this.
        spaces_per_tab = 4
    leading_spaces = 0
    for char in input_string:
        if char == "\t":
            leading_spaces += spaces_per_tab
        elif char == " ":
            leading_spaces += 1
        else:
            break
    return leading_spaces


def get_method_name_from_definition_line(input_string: str) -> str:
    """Given the entire content of the definition line for some method, return only the method name.
    Tolerate leading whitespace.
    """
    # Handle errors
    # input_string not a string
    if not isinstance(input_string, str):
        raise TypeError("input_string must be a string")
    # Line doesn't start with "def " after arbitrary number of tabs and spaces
    if strip_custom(input_string, ["\t", " "], "head")[:4] != "def ":
        raise ValueError("input_string not a method definition line")

    # Get the method name
    input_string_stripped = strip_custom(input_string, ["\t", " "], "head")[4:]
    method_name = ""
    for ii in range(len(input_string_stripped)):
        this_char = input_string_stripped[ii]
        if this_char != "(":
            method_name = method_name + input_string_stripped[ii]
        else:
            break

    return method_name


def get_class_name_from_definition_line(input_string: str) -> str:
    """Given the entire content of the definition line for some class, return only the class name."""
    # Handle errors
    # input_string not a string
    if not isinstance(input_string, str):
        raise TypeError("input_string must be a string")
    # Line doesn't start with "class " after arbitrary number of tabs and spaces
    if strip_custom(input_string, ["\t", " "], "head")[:6] != "class ":
        raise ValueError("input_string not a class definition line")

    # Get the class name
    input_string_stripped = strip_custom(input_string, ["\t", " "], "head")[6:]
    class_name = ""
    for ii in range(len(input_string_stripped)):
        this_char = input_string_stripped[ii]
        if this_char not in [":", "(", " "]:
            class_name = class_name + input_string_stripped[ii]
        else:
            break
    return class_name


def get_modulename_from_functioncall(functioncall: str) -> str:
    """Given the text of a traceline of category functioncall, or an added exit line, return the modulename for that
    line, no file extension.
    """
    # Get the indices of some important landmarks
    last_modulename_index = index_of_last_substring_in_string(functioncall, " --- modulename: ")
    last_funcname_index = index_of_last_substring_in_string(functioncall, ", funcname: ")

    # Output
    return functioncall[last_modulename_index+17:last_funcname_index]


def get_funcname_from_functioncall(functioncall: str) -> str:
    """Given the text of a traceline of category functioncall, or an added exit line, return the modulename for that
    line, with no file extension.
    """
    # Get the indices of some important landmarks
    last_funcname_index = index_of_last_substring_in_string(functioncall, ", funcname: ")

    # Output
    return functioncall[last_funcname_index+12:]


def begins_with_def_or_class(s_input: str) -> bool:
    """Returns True iff s_input begins with "def " or "class".
    WARNING: STRINGS WITH LEADING SPACES SHOULD BE RUN THROUGH STRIP_CUSTOM() BEFORE PASSING THEM TO THIS FUNCTION.
    """
    return s_input.startswith("def ") or s_input.startswith("class ")


def get_call_from_traceback(tb: str) -> str:
    """Given a traceback tb, return the call that triggered it."""
    # TODO: In the future, consider making this more robust by getting the call that triggered the traceback from the execution trace

    # Handle errors
    # tb not a string
    if not isinstance(tb, str):
        raise TypeError("tb must be a string")

    # Preprocess the traceback, in case it's formatted differently on a different system
    # If the traceback uses classic Mac returns ("\r" not followed by a "\n"), then replace all "\r" with "\n".
    if "\r" in tb and "\n" not in tb:
        tb = tb.replace("\r", "\n")
    # If the traceback uses "\\n" instead of "\n" for newlines, then replace all instances of "\\n" with "\n".
    if "\\n" in tb and "\n" not in tb:
        tb = tb.replace("\\n", "\n")
    # If the traceback uses 4 spaces instead of newlines, then replace all instances of 4 spaces with newlines.
    if "    " in tb and "\n" not in tb:
        tb = tb.replace("    ", "\n")
    # If the traceback uses 3 spaces instead of newlines, then replace all instances of 3 spaces with newlines.
    if "   " in tb and "\n" not in tb:
        tb = tb.replace("   ", "\n")
    # If the traceback uses 2 spaces instead of newlines, then replace all instances of 2 spaces with newlines.
    if "  " in tb and "\n" not in tb:
        tb = tb.replace("  ", "\n")
    # If there is no "\n" at the end of tb, put one there.
    if tb[-1] != "\n":
        tb = tb + "\n"

    # After splitting with "\n" as delimiter, get the line immediately before the last line that contains "Error"
    lines = tb.split("\n")
    call_line = None
    call = None
    for ll in range(len(lines)-1, 0, -1):
        if "Error" in lines[ll]:
            call_line = ll - 1
            call = lines[call_line]
            break
    # If that didn't work, new strategy: Get the last line that contains the text "raise "
    if call is None:
        for ll in range(len(lines)-1, 0, -1):
            if "raise " in lines[ll]:
                call_line = ll
                call = lines[call_line]
                break
    # If that didn't work, new strategy: Get the line immediately before the last line that contains "timed out"
    if call is None:
        for ll in range(len(lines)-1, 0, -1):
            if "timed out" in lines[ll]:
                call_line = ll - 1
                call = lines[call_line]
                break
    # If that didn't work, new strategy: Get the line before the last line that contains "exceptions."
    if call is None:
        for ll in range(len(lines)-1, 0, -1):
            if "exceptions." in lines[ll]:
                call_line = ll - 1
                call = lines[call_line]
                break
    # If that didn't work, new strategy: Get the last line that contains "[Errno"
    if call is None:
        for ll in range(len(lines)-1, 0, -1):
            if "[Errno" in lines[ll]:
                call_line = ll
                call = lines[call_line]
                break
    # If that didn't work, new strategy: Get the last line that starts with "File"
    if call is None:
        for ll in range(len(lines)-1, 0, -1):
            if strip_custom(lines[ll], ["\t", " "], "head")[:4] == "File":
                call = lines[ll]
                break
    # Nothing has worked.  We've failed to find the triggering line
    if call is None:
        raise ValueError("Given a traceback tb, couldn't discern a line that triggered it")

    # If the only non-whitespace character in call is a single '^', that means we grabbed a caret pointing to the call.  Set call equal to the previous line
    call_without_whitespace = call
    for white_char in string.whitespace:
        call_without_whitespace = call_without_whitespace.replace(white_char, "")
    if call_without_whitespace == "^":
        call_line -= 1
        if call_line < 0:
            raise ValueError("Given a traceback tb, couldn't discern a line that triggered it")
        else:
            call = lines[call_line]

    # Remove leading tabs and spaces
    call = strip_custom(call, ["\t", " "], "head")

    # Remove any trailing comment (ie any "#" that follows an unbalanced quote, along with everything after it)
    call = remove_trailing_comment(call)

    # Remove any trailing tabs and spaces
    call = strip_custom(call, ["\t", " "], "tail")

    # If call starts with 'File "', then it's not actually a call; it's a particular file.  Return nothing.
    if call[:6] == 'File "':
        return ""

    # If the call contains '  File "', strip everything from this point onward
    if '  File "' in call:
        call = call[:call.index('  File "')]

    return call


def remove_trailing_comment(s: str) -> str:
    """Return a version of s such that the first unquoted # is removed, along with any characters after it"""
    string_opened_by = None  # Iff None, we aren't in stringquotes.  Else, tells us what character (' or ") the string was opened by
    for cc in range(len(s)):
        this_character = s[cc]
        if string_opened_by is None:
            if this_character in ["'", '"']:
                string_opened_by = this_character
            elif this_character == "#":
                s = s[:cc]  # We've reached a comment.  Remove it and return what's left
                return s
        elif string_opened_by == "'":
            if this_character == "'":
                string_opened_by = None  # We've reached the closing single quote.  The string has been closed.
        elif string_opened_by == '"':
            if this_character == '"':
                string_opened_by = None  # We've reached the closing double quote.  The string has been closed.
    # We've made it all the way through s without encountering an unquoted #.
    return s


def starts_with_one_of(s: str, starters) -> bool:
    """If s starts with any of the strings in the list starters, return True.  Else return False."""
    # Handle errors
    if not isinstance(s, str):
        raise TypeError("s must be a string")

    # Run
    for starter in starters:
        if s.startswith(starter):
            return True
    return False


def index_of_last_substring_in_string(s_input: str, substring: str) -> int:
    """Return the index of the last instance of substring in s_input."""
    # Handle errors
    # substring not in s_input
    if substring not in s_input:
        raise ValueError("substring not found")

    # Handle special case: substring is empty
    if substring == "":
        return 0

    # Run
    s_input_rev = s_input[::-1]
    substring_rev = substring[::-1]
    return len(s_input_rev) - s_input_rev.index(substring_rev) - len(substring_rev)


def string_until(s_input: str, until) -> str:
    """Return the portion of s_input that comes before any character in until, which is a list of substrings."""
    # Handle errors
    # s_input not a string
    if not isinstance(s_input, str):
        raise TypeError("s_input must be a string")
    # until not a list
    if not isinstance(until, list):
        raise TypeError("until must be a list")

    # Run
    earliest_index = 1e15    # Initialize +BIG
    for this_substring in until:
        try:
            this_index = s_input.index(this_substring)
            earliest_index = min(earliest_index, this_index)
        except ValueError:  # If this_substring doesn't appear in s_input:
            pass
    if earliest_index == 1e15:  # If none of the substrings appeared inside s_input:
        return s_input
    else:
        return s_input[:earliest_index]


def matches_an_ignore_pattern(input_string: str, optional_ignore_patterns=None) -> bool:
    """Return True if the file with name input_string matches any of the patterns in ignore_patterns, which is a list
    of strings representing UNIX-like patterns.
    input_string must be an absolute path.
    If you wish to use a set of custom ignore patterns, make it the argument for optional_ignore_patterns.  It should
    be a list of UNIX-like pattern strings.
    """
    # Handle errors
    # input_string not a string
    if not isinstance(input_string, str):
        raise TypeError("input_string must be a string")
    # input_string empty
    if input_string == "":
        raise ValueError("input_string cannot be empty")
    # input_string not an absolute path
    if path.abspath(input_string) != input_string:
        raise ValueError("input_string must be an absolute filepath: " + input_string)

    # Grab the patterns to use
    if optional_ignore_patterns is None:
        from ph_variable_sharing.shared_variables import get_ignore_patterns
        patterns = get_ignore_patterns()
    else:
        patterns = optional_ignore_patterns

    # Compare input_string to patterns
    for this_pattern in patterns:
        if fnmatch(input_string, this_pattern):
            return True
    return False


def find_class_containing_method(line_number: int, module_content: list):
    """Return the name of the class that contains the method on line_number in the module, as well as the index of its
    definition line, starting counting at 1.
    :param line_number:     line number of the definition line of the method, starting counting at 1.
    :param module_content:  newline-separated list containing the entire content of the file containing the method
    """
    # Handle errors
    # line_number not an int
    if not isinstance(line_number, int):
        raise TypeError("line_number must be an int")
    # line_number not positive
    if line_number <= 0:
        raise ValueError("line_number must be positive")
    # module_content not a list
    if not isinstance(module_content, list):
        raise TypeError("module_content must be a list")
    # module_content contains non-string element
    for element in module_content:
        if not isinstance(element, str):
            raise TypeError("module_content must only contain strings")

    # Search upward to find the containing class
    class_containing = None
    line_number_as_index = line_number - 1
    leading_spaces_for_line_number = leading_spaces_of(module_content[line_number_as_index])
    for ii in range(line_number_as_index - 1, -1, -1):
        # If this line has fewer leading spaces/tabs than the line at line_number:
        if leading_spaces_of(module_content[ii]) < leading_spaces_for_line_number:
            # If, after stripping leading tabs and spaces, this line starts with "class ":
            if strip_custom(module_content[ii], ["\t", " "], "head").startswith("class "):
                # This must be the class containing the test case method that we want to run.  Get the name of this class
                class_containing = get_class_name_from_definition_line(module_content[ii])
                break

    # Handle error if no class found containing line
    if class_containing is None:
        raise ValueError("No class found containing line " + str(line_number))

    # Return!
    return class_containing, ii + 1


def get_module_level_only_from_file_content(file_content_in: list) -> list:
    """Return a version of file_content_in in which all lines that aren't at the module level have been removed.
    :param file_content_in: list.   newline-separated list of strings comprising the content of a file.  Should include leading whitespace.
    """
    file_content_out = []

    at_module_level = True
    indentation_level_of_module_breaker = None  # Whenever we leave the module level, this value is set to the number of indentations of the definition line that removed us from it.

    for this_line in file_content_in:
        # If this is a definition line and we've been at the module level, then leave the module level.
        # Update at_the_module_level and indentation_level_of_module_breaker.
        if begins_with_def_or_class(strip_custom(this_line, ["\t", " "], "head")):
            if at_module_level:
                at_module_level = False
                indentation_level_of_module_breaker = leading_spaces_of(this_line)

        # If this isn't a definition line and we haven't been at the module level, and this line is equally or less
        # indented than the initial module breaker, then reenter the module level
        else:
            if not at_module_level:
                if leading_spaces_of(this_line) <= indentation_level_of_module_breaker:
                    at_module_level = True

        # If we're at the module level, add this line to file_content_out
        if at_module_level:
            file_content_out.append(this_line)

    return file_content_out


def strip_trailing_newline(s: str) -> str:
    """Remove any trailing '\n' or '\r\n' from the end of s, if any"""
    # Handle errors
    # s not a string
    if not isinstance(s, str):
        raise TypeError("s must be a string")

    # Strip trailing newline
    if s.endswith("\r\n"):
        s = s[:-2]
    elif s.endswith("\n"):
        s = s[:-1]
    return s


def is_just_whitespace(s: str) -> bool:
    """Return True if s is just made of whitespace characters, else return False."""
    # Handle errors
    # s not a string
    if not isinstance(s, str):
        raise TypeError("s must be a string")

    # Run!
    for this_char in s:
        if this_char not in [" ", "\t", "\n", "\r"]:
            return False
    return True


def first_line_in_file_beginning_with_ignoring_whitespace(filepath: str, s: str) -> int:
    """Return the line number of the first line in filepath that begins with substring s, ignoring whitespace.
    Line numbers start counting at 1.
    """
    with open(filepath, "r", encoding="utf-8") as file:
        file_content = file.readlines()

    for ll in range(len(file_content)):
        if strip_custom(file_content[ll], ["\t", " "], "head").startswith(s):
            return ll + 1

    raise ValueError("no line in the file at filepath begins with s after removing whitespace")


def strip_comments_and_docstring_from_method(method):
    """Return version of method without the below-def docstring and without comments.
    :param method: The entire content of the method being searched, including the definition line, as a newline-separated list.
    """
    # Handle errors
    # method not a list
    if not isinstance(method, list):
        raise TypeError("method must be a list")
    # non-string entry in method
    for element in method:
        if not isinstance(element, str):
            raise TypeError("all of method's elements must be strings")
    # method empty
    if len(method) == 0:
        raise ValueError("method must not be empty")
    # method does not start with a def line
    if not strip_custom(method[0], ["\t", " "], "head").startswith("def "):
        raise ValueError("the first entry of method is not a method definition line")

    # Strip docstring from the method
    method_no_docstring = method.copy()
    # Find the first non-whitespace line under the def line
    index_first_non_whitespace_line_under_def = None
    for ll in range(len(method)):
        if ll > 0:
            this_line = method[ll]
            if not is_just_whitespace(this_line):
                index_first_non_whitespace_line_under_def = ll
                break
    if index_first_non_whitespace_line_under_def is None:
        raise ValueError("method does not contain any lines after the definition line that aren't just whitespace")
    # If the first non-whitespace line under the def line starts with triple quotes, we have to remove a docstring.
    first_non_whitespace_line_under_def = method[index_first_non_whitespace_line_under_def]
    stripped = strip_custom(first_non_whitespace_line_under_def, ["\t", " "], "head")
    if starts_with_one_of(stripped, ['"""', "'''"]):
        starter = stripped[:3]
        # Find next_index_of_starter
        next_index_of_starter = None
        if len(stripped) > 3 and starter in stripped[3:]:   # Handle the closing triple quote being on the same line as the opening one
            next_index_of_starter = index_first_non_whitespace_line_under_def
        else:   # Handle the closing triple quote being on some other line instead
            for ll in range(index_first_non_whitespace_line_under_def + 1, len(method)):
                if starter in method[ll]:
                    next_index_of_starter = ll
        if next_index_of_starter is None:
            raise ValueError("method never closes its opening triple-quote for the first docstring under the def line")
        # Remove all lines from index_first_non_whitespace_line_under_def THROUGH next_index_of_starter
        del method_no_docstring[index_first_non_whitespace_line_under_def:next_index_of_starter+1]

    # Strip comments from the method
    method_no_comments = []
    for line in method_no_docstring:
        if not strip_custom(line, [" ", "\t"], "head").startswith("#"):  # Filter out leading comments
            method_no_comments.append(remove_trailing_comment(line))

    # Return!
    return method_no_comments


def token_appears_in_method(token: str, method) -> bool:
    """Return whether token appears in method, ignoring the docstring immediately below the definition line, as well as
    comments.
    This function is not fooled by tokens that are substrings of other tokens.
    For example, it does not count "foo" as a hit if searching for "fo".
    :param token: The token being searched for
    :param method: The entire content of the method being searched, including the definition line, as a newline-separated list.
    """
    permitted_adjacents = [None, " ", "\n", "\r", "\t", "~", "!", "@", "%", "^", "&", "*", "(", ")", "-", "+", "=", "{", "}", "[", "]", "|", "\\", ":", ";", '"', "'", "<", ">", ",", ".", "/", "?"]

    # Handle errors
    # token not a string
    if not isinstance(token, str):
        raise TypeError("token must be a string")
    # token empty
    if len(token) == 0:
        raise ValueError("token must not be empty")
    # method not a list
    if not isinstance(method, list):
        raise TypeError("method must be a list")
    # non-string entry in method
    for element in method:
        if not isinstance(element, str):
            raise TypeError("all of method's elements must be strings")
    # method empty
    if len(method) == 0:
        raise ValueError("method must not be empty")
    # method does not start with a def line
    if not strip_custom(method[0], ["\t", " "], "head").startswith("def "):
        raise ValueError("the first entry of method is not a method definition line")

    # Remove any docstring immediately under the def line, as well as all comments
    method = strip_comments_and_docstring_from_method(method)

    # Create method_as_string
    method_as_string = ""
    for element in method:
        method_as_string += element + "\n"
    method_as_string = method_as_string[:-1]

    # Get the indices of all appearances of the token in the method
    indices = [ii for ii in range(len(method_as_string)) if method_as_string.startswith(token, ii)]

    # If a single entry in indices is both preceded and succeeded by a permitted adjacent or by nothing, return True.
    for index in indices:
        token_end = index + len(token)  # 1 + the token's last character's index
        # Get predecessor
        if index > 0:
            predecessor = method_as_string[index-1]
        else:
            predecessor = None
        # Get successor
        if token_end < len(method_as_string):
            successor = method_as_string[token_end]
        else:
            successor = None
        # Check
        if predecessor in permitted_adjacents and successor in permitted_adjacents:
            return True

    # We didn't find a token
    return False


def minimize_indents(body_text):
    """Given Python body text in list form, return a version of it in which all lines are uniformly de-indented
    until no more de-indentations can be made.
    :param body_text:       newline-separated list of representing body code
    """
    # Handle errors
    # body_text not a list
    if not isinstance(body_text, list):
        raise TypeError("body_text must be a list")
    # body_text contains non-string element
    for element in body_text:
        if not isinstance(element, str):
            raise TypeError("body_text contains non-string element")

    # Determine whether the file uses tabs or spaces by majority vote of the lines that begin with whitespace
    tab_beginner_count = 0
    space_beginner_count = 0
    for this_line in body_text:
        if this_line.startswith("\t"):
            tab_beginner_count += 1
        if this_line.startswith(" "):
            space_beginner_count += 1
    if space_beginner_count >= tab_beginner_count:
        indentation_char = " "
    else:
        indentation_char = "\t"

    # Uniformly de-indent from all nonempty lines until no more de-indentation can occur
    while True:
        # If there's an unindented nonempty line, break
        unindented_nonempty_line = False
        for this_line in body_text:
            if len(this_line) > 0 and this_line[0] != indentation_char:
                unindented_nonempty_line = True
        if unindented_nonempty_line:
            break

        # De-indent all nonempty lines by one more
        for ll in range(len(body_text)):
            this_line = body_text[ll]
            if len(this_line) > 0:
                body_text[ll] = body_text[ll][1:]

    # Return!
    return body_text


def concatenate_list_to_string(input_list, between="") -> str:
    """Given a list of only strings, return the string produced by concatenating all its elements in order.
    :param input_list       the list to be concatenated
    :param between          str. Inserted between elements of input_list.
    """
    # Handle errors
    # input_list not a list
    if not isinstance(input_list, list):
        raise TypeError("input_list must be a list")
    # input_list contains non-string element
    for element in input_list:
        if not isinstance(element, str):
            raise TypeError("element must be a string")
    # between not a string
    if not isinstance(between, str):
        raise TypeError("between must be either None or a string")

    # Handle empty input_list
    if len(input_list) == 0:
        return ""

    # Run
    output_string = ""
    for element in input_list:
        output_string += element
        output_string += between
    if len(between) > 0:
        output_string = output_string[:-len(between)]
    return output_string


def remove_duplicates_from_list(input_list: list) -> list:
    """Remove duplicate entries from a list while preserving order."""
    output = []
    for element in input_list:
        if element not in output:
            output.append(element)
    return output


def hamming_distance(s0: str, s1: str) -> int:
    """Return the Hamming distance between two strings"""
    # Handle errors
    # s0 not a string
    if not isinstance(s0, str):
        raise TypeError("s0 must be a string")
    # s1 not a string
    if not isinstance(s1, str):
        raise TypeError("s1 must be a string")

    # Convert to unicode binary representation (matches ASCII binary representation for ASCII-compatible characters)
    s0_bits = ''.join(format(ord(char), 'b') for char in s0)
    s1_bits = ''.join(format(ord(char), 'b') for char in s1)

    # Pad the shorter string with 2s.  Since these won't occur anywhere else, they'll always count towards total
    # If one string has more bits than the other, then each new bit will count as an unseen bit
    if len(s0_bits) < len(s1_bits):
        s0_bits += "2" * abs(len(s0_bits) - len(s1_bits))
    elif len(s0_bits) > len(s1_bits):
        s1_bits += "2" * abs(len(s0_bits) - len(s1_bits))

    # Count differing positions.
    total = 0
    for ii in range(len(s0_bits)):
        if s0_bits[ii] != s1_bits[ii]:
            total += 1

    return total


def levenshtein_distance(s0: str, s1: str) -> int:
    """Return the Levenshtein distance between two strings"""
    # Handle errors
    # s0 not a string
    if not isinstance(s0, str):
        raise TypeError("s0 must be a string")
    # s1 not a string
    if not isinstance(s1, str):
        raise TypeError("s1 must be a string")

    return lev(s0, s1)


def indices_of_all_occurrences_of_character_in_string(c: str, s: str) -> list:
    """Given a character c and a string s, return a list with the index of every occurrence of c in s.
    :param c:           the character to look for
    :param s:           the string to search for occurrences of the character
    :return:            list of ints, where each int is the index of an occurrence of c in s
    """
    # Handle errors
    # c not a string
    if not isinstance(c, str):
        raise TypeError("c must be a string")
    # c not a single character
    if len(c) != 1:
        raise ValueError("c must be a single character")
    # s not a string
    if not isinstance(s, str):
        raise TypeError("s must be a string")

    counter = 0
    output = []
    while len(s) > 0:
        if s.startswith(c):
            output.append(counter)
        s = s[1:]
        counter += 1

    return output


def is_linelog(s: str) -> bool:
    """Return whether s is a linelog line"""
    # Handle errors
    # s not a string
    if not isinstance(s, str):
        raise TypeError("s must be a string")

    # Strip leading and trailing whitespace
    s = strip_custom(s, [" ", "\t", "\n", "\r"], "head")
    s = strip_custom(s, [" ", "\t", "\n", "\r"], "tail")

    # Now we return whether line fits the form '*.*(numbers): *'

    # Check that there is a period and get the index of the first occurrence
    if "." not in s:
        return False
    index_period = s.index(".")
    # Check that there are no forbidden filename characters before that period
    characters_before_period = s[:index_period]
    for this_forbidden_character in "#%&{}\\<>*?/ $!'\":@+`|=":
        if this_forbidden_character in characters_before_period:
            return False
    # Check that there is an open parenthesis after that period and get the index of the first occurrence
    characters_after_period = s[index_period+1:]
    if "(" not in characters_after_period:
        return False
    index_open_paren = characters_after_period.index("(") + len(characters_before_period) + 1
    # Check that there is a close parenthesis after that period and get the index of the first occurrence
    characters_after_open_paren = s[index_open_paren+1:]
    if ")" not in characters_after_open_paren:
        return False
    index_close_paren = characters_after_open_paren.index(")") + index_open_paren + 1
    # Check that there's at least one character inside these parentheses
    if index_close_paren - index_open_paren == 1:
        return False
    # Check that all characters between these parentheses are digits
    characters_between_parens = s[index_open_paren+1:index_close_paren]
    for char in characters_between_parens:
        if char not in "0123456789":
            return False
    # Check that there is a colon and a space immediately after that close parenthesis.
    if s[index_close_paren+1:index_close_paren+3] != ": ":
        return False

    return True


def remove_whitespace_only_lines_from_extremes_of_list(l: list) -> list:
    """Return a version of l in which all leading or trailing elements that are only whitespace are removed,
    :param l:       list of strings
    """
    # Handle errors
    # l not a list
    if not isinstance(l, list):
        raise TypeError("l must be a list")
    # l empty
    if len(l) == 0:
        raise ValueError("l must not be empty")
    # l contains non-string element
    for element in l:
        if not isinstance(element, str):
            raise TypeError("l contains non-string element")

    # Remove from end
    for ii in range(len(l)-1, -1, -1):
        line = l[ii]
        if is_just_whitespace(line):
            l.pop(ii)
        else:
            break

    # Remove from beginning
    ii = 0
    while ii < len(l):
        if not is_just_whitespace(l[ii]):
            break
        ii += 1
    l = l[ii:]

    return l


def get_folder_delimiter(path: str) -> str:
    """Given a filepath, return the folder delimiter: either '/' or '\\'
    :param path:        filepath to find the delimiter of
    """
    # Handle errors
    # path not a string
    if not isinstance(path, str):
        raise TypeError("path must be a string")

    # Handle path empty
    if len(path) == 0:
        return "/"

    folder_delimiter = "/"
    if "\\" in path:
        if "/" in path:
            raise ValueError("path contains both / and \\.  Only one is permitted")
        else:
            folder_delimiter = "\\"

    return folder_delimiter


def remove_leading_substring(substring: str, s: str) -> str:
    """Return a version of s that lacks the leading substring substring.
    If s does not begin with substring, throw an error
    """
    # Handle errors
    # substring not a string
    if not isinstance(substring, str):
        raise TypeError("substring must be a string")
    # s not a string
    if not isinstance(s, str):
        raise TypeError("s must be a string")
    # substring longer than s
    if len(substring) > len(s):
        raise ValueError("substring must not be longer than s")

    if s.startswith(substring):
        return s[len(substring):]
    else:
        raise ValueError("s does not start with substring")


def count_leading_occurrences_of_character(s: str, c: str) -> int:
    """Count how long of an uninterrupted chain of c appears at the beginning of s.
    """
    # Handle errors
    # s not a string
    if not isinstance(s, str):
        raise TypeError("s must be a string")
    # c not a string
    if not isinstance(c, str):
        raise TypeError("c must be a string")
    # c not a single character
    if len(c) != 1:
        raise ValueError("c must be one character long")

    counter = 0
    while len(s) > 0 and s[0] == c:
        counter += 1
        s = s[1:]
    return counter


def is_paren_balanced(s: str) -> bool:
    """Return whether s has a valid set of parentheses.
    This method only works on parentheses.  It doesn't work on other braces or brackets.
    Does not adapt to escaped parentheses, such as parenthesis fragments in strings etc.
    """
    # Handle errors
    # s not a string
    if not isinstance(s, str):
        raise TypeError("s must be a string")

    if len(s) == 0:
        return True

    paren_nest_count = 0
    for c in s:
        if c == "(":
            paren_nest_count += 1
        elif c == ")":
            paren_nest_count -= 1
            if paren_nest_count < 0:
                return False
    return paren_nest_count == 0


def insert_char_in_string_at_index(c, s, ind):
    """Insert character c into string s at index ind."""
    before_insertion = s[:ind]
    after_insertion = s[ind:]
    return before_insertion + c + after_insertion


def remove_char_from_string_at_index(s, ind):
    """Remove the character at index ind in s."""
    before_char = s[:ind]
    after_char = s[ind+1:]
    return before_char + after_char


def replace_char_in_string_at_index(c, s, ind):
    """Change the character at index ind in s to c."""
    before_char = s[:ind]
    after_char = s[ind+1:]
    return before_char + c + after_char


def get_indices_containing_function_body_and_indentation_of_definition(file_as_list: list, function_name: str) -> tuple:
    """Given the content of a python file as a newline-separated list, and the name of a particular function, return
    the indices where the function starts (inclusive) and ends (exclusive), excluding its definition line and docstring.
    Also return the indentation level in spaces of the definition line.
    """
    # Handle errors
    # file_as_list not a list
    if not isinstance(file_as_list, list):
        raise TypeError("file_as_list must be a list")
    # file_as_list contains non-string element
    for element in file_as_list:
        if not isinstance(element, str):
            raise TypeError("file_as_list contains non-string element")
    # function_name not a string
    if not isinstance(function_name, str):
        raise TypeError("function_name must be a string")

    # Get the index of the first occurrence of f"def function_name(" after removing newlines, and make note of its
    # indentation level.
    index_function_start = None
    for ll, line in enumerate(file_as_list):
        if strip_custom(line, [" ", "\t"], "head").startswith(f"def {function_name}("):
            index_function_start = ll
            indentation_function_start = count_indentation_in_spaces(line)
            break
    if index_function_start is None:
        raise ValueError(f"couldn't find declaration of function {function_name} in file_as_list")

    # Get the first line of the function that isn't a definition line or docstring
    index_body_start = None
    if not starts_with_one_of(strip_custom(file_as_list[index_function_start + 1], ["\t", " "], "head"), ["'''", '"""']):
        index_body_start = index_function_start + 1
    else:
        for ll, line in enumerate(file_as_list):    # TODO: Make robust to commented-out docstrings
            if ll <= index_function_start:
                continue
            if ll == index_function_start + 1 and (line.count("'''") == 2 or line.count('"""') == 2):
                index_body_start = ll + 1
                break
            elif ll >= index_function_start + 2 and (line.cont("'''") == 1 or line.count('"""') == 2):
                index_body_start = ll + 1
                break
    if index_body_start is None:
        raise ValueError(f"couldn't find start of body after function declaration for function {function_name} in file_as_list")

    # Get the index of the first line after the definition which is <= indented and isn't just whitespace
    index_function_end = None
    for ll, line in enumerate(file_as_list):
        if ll <= index_function_start:
            continue
        if not is_just_whitespace(line) and count_indentation_in_spaces(line) <= indentation_function_start:
            index_function_end = ll
            break

    # Return!
    return (index_body_start, index_function_end, indentation_function_start)


def count_indentation_in_spaces(s: str) -> int:
    """Return the indentation level of s.  Tabs count for tatosp spaces."""
    # Handle errors
    # s not a string
    if not isinstance(s, str):
        raise TypeError("s must be a string")
    # s contains \n
    if "\n" in s:
        raise ValueError("s must not contain \\n")
    # s is just whitespace
    if is_just_whitespace(s):
        raise ValueError("s is just whitespace")

    shared_variables.initialize()
    tatosp = shared_variables.tatosp

    indentation_counter = 0

    for cc, char in enumerate(s):
        if char == " ":
            indentation_counter += 1
        elif char == "\t":
            indentation_counter += tatosp
        else:
            return indentation_counter


def overwrite_list_with_list_at_index(source: list, destination: list, index_start: int, index_end=None) -> list:
    """Examples:
    overwrite_list_with_list_at_index([5], [0, 1, 2], 1) = [0, 5, 2]
    overwrite_list_with_list_at_index([5], [0, 1, 2, 3, 4], 2, 4) = [0, 1, 5, 4]
    """
    # Handle errors
    # source not a list
    if not isinstance(source, list):
        raise TypeError("source must be a list")
    # source empty
    if len(source) == 0:
        raise ValueError("source must not be empty")
    # destination not a list
    if not isinstance(destination, list):
        raise TypeError("destination must be a list")
    # destination empty
    if len(destination) == 0:
        raise ValueError("destination must not be empty")
    # index_start not an int
    if not isinstance(index_start, int):
        raise TypeError("index_start must be an int")
    # index_start negative
    if index_start < 0:
        raise ValueError("index_start must not be negative")
    # index_end not None or an int
    if not (index_end is None) and not (isinstance(index_end, int)):
        raise TypeError("index_end must be None or an int")
    # index_end is int but negative
    if isinstance(index_end, int) and index_end < 0:
        raise ValueError("index_end must not be negative")

    # Defensive copying
    s = source.copy()
    d = destination.copy()

    # Run!
    if index_end is None:
        index_end = index_start + 1
    out = d[:index_start]
    out.extend(s)
    out.extend(d[index_end:])

    return out
