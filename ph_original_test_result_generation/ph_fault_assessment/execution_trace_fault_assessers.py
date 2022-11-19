"""Classes and functions for examining execution traces to assign blame for failures"""


#
# HELPER FUNCTIONS
#
def user_at_fault(post_processed_trace: str, non_ignored_user_descendant_lines, original_test_module: str, user_and_py_holmes_modules) -> bool:
    """Return True if a piece of user code not in .holmesignore is responsible for a failure.
    Else return False.
    post_processed_trace is the full execution trace.
    non_ignored_user_descendant_lines is a list of indices of the linelogs in post_processed_trace that are descendants of user code not in .holmesignore.
    original_test_module is the filename of the user's unit test module, with or without a file extension
    user_and_py_holmes_modules is a list of module names belonging to the user or py-holmes that were used
    """
    # Handle errors
    # post_processed_trace not a string
    if not isinstance(post_processed_trace, str):
        raise TypeError("post_processed_trace must be a string")
    # non_ignored_user_descendant_lines not a list
    if not isinstance(non_ignored_user_descendant_lines, list):
        raise TypeError("non_ignored_user_descendant_lines must be a list")
    # Non-int entry in non_ignored_user_descendant_lines
    if any(not isinstance(entry, int) for entry in non_ignored_user_descendant_lines):
        raise TypeError("all entries in non_ignored_user_descendant_lines must be ints")
    # original_test_module not a string
    if not isinstance(original_test_module, str):
        raise TypeError("original_test_module must be a string")

    # Remove the ".py" file extension from the end of original_test_module if it is there.
    if original_test_module.endswith(".py"):
        original_test_module = original_test_module[:-3]

    # Find the failure (not error) line in the execution trace (Python source code, not a user-written line).
    trace_as_list = post_processed_trace.split("\n")
    index_of_failing_line = find_index_of_failing_line(trace_as_list)

    # Determine whether the user is at fault
    if index_of_failing_line in non_ignored_user_descendant_lines:  # ie if the failing line is a call-descendant of at least one non-ignored user file:
        return True
    else:
        # If the failure happened immediately inside the user's original test file, it's their fault anyway.
        # Else, it's not their fault.
        # To check if the failure happened inside the user's original test file, we work upward from the failing line
        # until we reach a " --- modulename: x" line where x is either the original test file, or some module outside
        # a list of known modules internal to Python, AND where that function was not subsequently exited.
        # Iff it's the original test file, then the user it at fault anyway.
        entry_negations_due_to_having_exited = []   # When we see an exit from a module+function, add it here as a [module, function] sublist.  When we see an entry into a module+function that appears in this list, remove one instance of it from this list
        for ll in range(index_of_failing_line, -1, -1):
            this_line = trace_as_list[ll]
            # If this is an exit, add it to entry_negations_due_to_having_exited
            if this_line.startswith(" ||| exiting modulename: ") and ", funcname: " in this_line:
                modulename_index = this_line.index(" ||| exiting modulename: ")
                funcname_index = this_line.index(", funcname")
                this_module = this_line[25:funcname_index]
                this_funcname = this_line[funcname_index+10:]
                entry_negations_due_to_having_exited.append([this_module, this_funcname])
            # If this is a module entry line:
            if this_line.startswith(" --- modulename: ") and ", funcname: " in this_line:
                # Get the modulename this_module
                modulename_index = this_line.index(" --- modulename: ")
                funcname_index = this_line.index(", funcname")
                this_module = this_line[17:funcname_index]
                this_funcname = this_line[funcname_index + 10:]
                # If we saw a later exit from this function, ignore and remove that entry from
                # entry_negations_due_to_having_exited.  Else, if this_module is the original test file,
                # the user is at fault.  Elif this_module is in a list of known user modules (regardless of whether
                # they're ignored), then the user is not at fault.  Else, keep going.
                if [this_module, this_funcname] in entry_negations_due_to_having_exited:
                    entry_negations_due_to_having_exited.remove([this_module, this_funcname])
                else:
                    if this_module == original_test_module:
                        return True
                    elif this_module in user_and_py_holmes_modules:
                        return False
        # We've gone through the entire portion of the trace above the failing line without finding anything
        raise RuntimeError("Reached top of execution trace without finding a user function.  Perhaps failure happened due to a fundamental Python file?")


def find_index_of_failing_line(trace_list) -> int:
    """Given a post-processed execution trace as a list, get the index of the failing line.
    This line is a *failing* line, not an error line.  It is Python source code, not a user-written line, but it may
    be the call-descendant of one or more user-written code.
    We assume this to be the first line from file case.py with "self._raiseFailure(" or "raise self.failureException("
    in its content.
    trace_list is a list of strings, produced by splitting the post-processed execution trace by newlines.
    """
    # Handle errors
    # trace_list not a list
    if not isinstance(trace_list, list):
        raise TypeError("trace_list must be a list")
    # trace_list contains a non-string element
    if any(not isinstance(entry, str) for entry in trace_list):
        raise TypeError("all entries in trace_list must be strings")

    # Run
    for ii in range(len(trace_list)):
        this_line = trace_list[ii]
        if this_line.startswith("case.py(") and ("self._raiseFailure(" in this_line or "raise self.failureException(" in this_line):
            return ii

    # If we've gotten this far, there is no such line in the execution trace.
    raise ValueError("no failing line found in execution trace")
