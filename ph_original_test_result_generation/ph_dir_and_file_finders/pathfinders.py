"""Classes and functions for finding the absolute filepath of a file or directory, given its name."""
from ph_original_test_result_generation.ph_dir_and_file_finders.default_python_install_for_os_finders import get_python_path_for_platform
from ph_variable_sharing import shared_variables
from ph_basic_processing.parsers import strip_custom, matches_an_ignore_pattern

from os import walk, path
from sys import executable


#
# GLOBAL VARIABLES
#
# TODO: Take steps to avoid running out of memory when caching extremely large files.  But beware that currently other parts of the code assume that every file will end up in FILES_ALREADY_READ; this should no longer be an assumption if we sometimes prevent files from being stored in it.
FILES_ALREADY_READ = {}     # For caching results.  Keys are filenames (with file extension).  Values are a tuple containing (an absolute filepath, a line-by-line list of the file's contents, whether the file is user-written and non-ignored, whether the file is a user or py-holmes file (holmesignored files not excluded)))

shared_variables.initialize()
ROOT_DIR = shared_variables.ROOT_DIR

# Get the default installation location for Python based on the operating system
PLATFORM_PYTHON_PATH = get_python_path_for_platform()


#
# HELPER FUNCTIONS
#
def get_absolute_path(name, check_line, check_num):
    """Return the absolute path to filename name (including file extension).
    To help ensure the file is the correct one (and not just some other file with the same name), the caller must
    also provide check_line (the content of one line of the file being searched for), and check_num (the row of that
    line in the file, starting from 1).
    This method draws heavily from this StackOverflow thread: https://stackoverflow.com/questions/1724693/find-a-file-in-python
    """
    output = None
    visited_directories_absolute = []   # Builds up directories we've already visited during this call of get_absolute_path() so that we don't do so again

    # First, check the cache for the file.  If it's there, validate that it's not just another file with a different name, then return it
    if name in FILES_ALREADY_READ:
        if file_contains_content_on_line(FILES_ALREADY_READ[name][0], name, check_line, check_num, cached=True):
            return FILES_ALREADY_READ[name][0]

    # Get the list of all dirs to search, including holmessearchextend_dirs, the list of dirs to search based on .holmessearchextend.
    shared_variables.initialize_all_dirs_to_search()
    dirs_to_search = shared_variables.all_dirs_to_search.copy()

    # The file wasn't found in the cache.  Search all folders where we can reasonably expect it to be.  file_contains_content_on_line adds a found file to the cache as a side-effect
    for this_root_dir in dirs_to_search:    # First check the project directory.  Failing that, check the directory of the Python interpreter being used.  Failing that, check the default Python install location for this operating system
        searched_dirs_within_this_root_dir = []     # Appended to visited_directories_absolute at the end of a cycle
        for root, dirs, files in walk(this_root_dir):
            # Remove already-searched directories from dirs, so that we don't search them
            for this_dir in dirs:
                if path.join(root, this_dir) in visited_directories_absolute:
                    dirs.remove(this_dir)
            # Search
            searched_dirs_within_this_root_dir.append(root)
            if name in files:
                candidate = path.join(root, name)
                if file_contains_content_on_line(candidate, name, check_line, check_num, cached=False, root_directory=this_root_dir):
                    output = candidate
                    return output
        visited_directories_absolute.extend(searched_dirs_within_this_root_dir)

    # We've failed to find the file
    if output is None:
        raise ValueError("could not find file in project directory or other likely folders: " + name)


def file_contains_content_on_line(filepath: str, filename: str, line_content: str, line_num: int, cached: bool, root_directory=None) -> bool:
    """Return true if the file at filepath's line_num'th line equals line_content, ignoring leading whitespace
    filepath is an absolute path to the file.
    filename is the name of the file, with an extension
    line_num starts counting at 1.
    cached indicates whether the file has already been placed in the FILES_ALREADY_READ cache.  If already cached, this
    function checks the cache instead of reading the file anew.  If not cached, this function adds the file to the
    cache.
    root_directory is a string -- the absolute path of the directory being searched when the file was found.  It influences whether the file is categorized as to be ignored
    """
    # Handle errors
    # File not cached and root_directory not given
    if not cached and root_directory is None:
        raise ValueError("because cached is false, root_directory must be given")

    # Run!
    line_num_as_index = line_num - 1

    # If already cached, check cache instead of reading file anew.
    # For an already-cached file, we don't need to redetermine if it's a non-ignored user file
    if cached:
        if len(FILES_ALREADY_READ[filename][1]) >= line_num_as_index + 1:
            return line_content == FILES_ALREADY_READ[filename][1][line_num_as_index]
        else:
            return False

    # If not cached:
    # Read the file
    with open(filepath, "r", encoding="utf-8") as file:
        file_content = file.readlines()
    # Check if it's the correct file
    if len(file_content) - 1 >= line_num_as_index:
        file_line = file_content[line_num_as_index]
    else:
        return False    # The file at filepath is too short to contain the line we're looking for, so it can't be the file we're looking for
    file_line = strip_custom(file_line, ["\t", " "], "head")
    file_line = strip_custom(file_line, ["\n"], "tail")
    line_content = strip_custom(line_content, ["\t", " "], "head")
    # If the correct file, cache it and flag whether the file is a non-ignored user file, as well as whether it's a user file.
    if file_line == line_content:
        # Flag whether the file is a user file.
        file_in_executable = filepath.startswith(path.dirname(path.dirname(executable)))
        file_in_platform_python_path = filepath.startswith(PLATFORM_PYTHON_PATH)
        is_user_or_py_holmes_file = root_directory == ROOT_DIR and not (file_in_executable or file_in_platform_python_path)
        # Flag whether the file is a non-ignored user file.
        file_in_a_holmesignore_dir = matches_an_ignore_pattern(filepath)
        non_ignored_user_file = is_user_or_py_holmes_file and not file_in_a_holmesignore_dir
        FILES_ALREADY_READ[filename] = (filepath, file_content, non_ignored_user_file, is_user_or_py_holmes_file)  # Cache the file
        return True
    else:
        return False
