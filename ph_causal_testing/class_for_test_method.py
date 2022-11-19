"""The TestMethod class, which is used to contain the details of a found or fuzzed test method."""


from ph_variable_sharing import shared_variables
from ph_basic_processing.parsers import strip_trailing_newline, get_method_name_from_definition_line, find_class_containing_method, leading_spaces_of, is_just_whitespace, get_module_level_only_from_file_content, strip_custom, remove_trailing_comment, get_class_name_from_definition_line, token_appears_in_method, strip_file_extension

from _warnings import warn
from os import path, listdir
from sys import platform


#
# GLOBAL VARIABLES
#
shared_variables.initialize()
ROOT_DIR = shared_variables.ROOT_DIR


#
# CLASSES
#
class TestMethod:
    """Container for information about a test method found in the user's project.
    Attributes are as follows:
    test_filepath: str.                         absolute path to the file containing the found test method
    test_class: str.                            name of the unittest.TestCase class containing the found test method
    class_content: list.                        newline-separated list of strings comprising the content of the class containing the test.  Should include leading whitespace.
    test_name: str.                             name of the found test method
    test_content: list.                         newline-separated list of strings comprising the content of the test.  Should include leading whitespace.
    all_imports: set.                           set of strings: filenames, method names, and class names that this function references.  Entries are aboslute.  Within each entry, a dot is used as a separator.
    files_methods_and_classes_testing: set.     all_imports except only containing content from user-written files.
    requisite_import_lines: set.                all_imports except every entry has been rephrased from "foo.bar.baz" to "from foo.bar import baz"
    starting_test_lineno: int.                  first line of the test (the definition line), starting counting at 1
    starting_test_lineno_as_index: int.         like starting_test_lineno, but starting counting at 0
    ending_test_lineno: int.                    last line of the test (exclusive; really the line after the last line), starting counting at 1
    ending_test_lineno_as_index: int.           like ending_test_lineno, but starting counting at 0
    starting_class_lineno: int.                 definition line of the class containing the test method, starting counting at 1
    starting_class_lineno_as_index: int.        like starting_class_lineno, but starting counting at 0
    ending_class_lineno: int.                   last line of the class containing the test (exclusive; really the line after the last line), starting counting at 1
    ending_class_lineno_as_index: int.          like ending_class_lineno, but starting counting at 0
    origin: str.                                "found" or "fuzzed".  Indicates whether the method was found in a user-written file or produced by py-holmes's fuzzing.  The original user-written test's origin should equal "found".
    is_fuzzed: bool.                            true iff this test was produced through a fuzzing process
    is_original: bool.                          true iff this test is the original test that was referenced by the user when py_holmes.py was first called from the command line
    is_dummy: bool.                             should only be enabled for debugging/testing py-holmes itself.  Renders the object mostly inert by bypassing most of self.__init__()
    """

    def __init__(self, origin: str, test_filepath: str, starting_test_lineno: int, is_fuzzed: bool, is_original=False, is_dummy=False) -> None:
        """For parameters, see docstring for class TestMethod."""
        # Handle errors
        if not isinstance(is_dummy, bool):
            raise TypeError("is_dummy must be a bool")
        if not is_dummy:
            # Handle errors
            # origin not a string
            if not isinstance(origin, str):
                raise TypeError("origin must be a string")
            # origin not a valid string
            if origin not in ["found", "fuzzed"]:
                raise ValueError("origin must equal either 'found' or 'fuzzed'")
            # test_filepath not a string
            if not isinstance(test_filepath, str):
                raise TypeError("test_filepath must be a string")
            # test_filepath empty
            if len(test_filepath) == 0:
                raise ValueError("test_filepath must not be empty")
            # test_filepath not absolute
            if test_filepath != path.abspath(test_filepath):
                raise ValueError("test_filepath must be an absolute filepath")
            # starting_test_lineno not an int
            if not isinstance(starting_test_lineno, int):
                raise TypeError("starting_test_lineno must be an int")
            # starting_test_lineno not positive
            if starting_test_lineno <= 0:
                raise ValueError("starting_test_lineno must be positive")
            # is_fuzzed not a bool
            if not isinstance(is_fuzzed, bool):
                raise TypeError("is_fuzzed must be a bool")
            # is_original not a bool
            if not isinstance(is_original, bool):
                raise TypeError("is_original must be a bool")

            # Run
            self.test_filepath = test_filepath
            self.starting_test_lineno = starting_test_lineno
            self.starting_test_lineno_as_index = self.starting_test_lineno - 1
            self.is_fuzzed = is_fuzzed
            self.is_original = is_original

            # Get the content of the entire file
            with open(test_filepath, "r", encoding="utf-8") as file:
                file_content = file.readlines()
            for ii in range(len(file_content)):
                file_content[ii] = strip_trailing_newline(file_content[ii])

            # Set self.origin
            self.origin = origin

            # Set self.test_name
            def_line = file_content[self.starting_test_lineno_as_index]
            self.test_name = get_method_name_from_definition_line(def_line)

            # Set self.test_class, self.starting_class_lineno, and self.starting_class_lineno_as_index
            self.test_class, self.starting_class_lineno = find_class_containing_method(self.starting_test_lineno, file_content)
            self.starting_class_lineno_as_index = self.starting_class_lineno - 1

            # Set self.ending_test_lineno and self.ending_test_lineno_as_index
            # Get the number of indentations on the definition line
            num_method_definition_indents = leading_spaces_of(def_line)
            # Search downward from starting_test_lineno_as_index until a nonempty line is found that's <= indented than the definition
            # line.  When this occurs, set self.ending_test_lineno accordingly
            for ll in range(self.starting_test_lineno_as_index + 1, len(file_content) + 1):
                if ll == len(file_content):     # If we've already checked the last line in the file:
                    break
                this_line = file_content[ll]
                if leading_spaces_of(this_line) <= num_method_definition_indents and not is_just_whitespace(this_line):
                    break
            self.ending_test_lineno_as_index = ll
            self.ending_test_lineno = ll + 1

            # Set self.test_content
            self.test_content = file_content[self.starting_test_lineno_as_index:self.ending_test_lineno_as_index]

            # Set self.ending_class_lineno and self.ending_class_lineno_as_index
            num_class_definition_indents = leading_spaces_of(file_content[self.starting_class_lineno_as_index])
            for ll in range(self.ending_test_lineno_as_index, len(file_content) + 1):
                if ll == len(file_content):     # If we've already checked the last line in the file:
                    break
                this_line = file_content[ll]
                if leading_spaces_of(this_line) <= num_class_definition_indents and not is_just_whitespace(this_line):
                    break
            self.ending_class_lineno_as_index = ll
            self.ending_class_lineno = ll + 1

            # Set self.class_content
            self.class_content = file_content[self.starting_class_lineno_as_index:self.ending_class_lineno_as_index]

            # Set self.files_methods_and_classes_testing and self.requisite_import_lines, unless this is a fuzzed test method
            if self.origin != "fuzzed":
                self.all_imports, self.files_methods_and_classes_testing = self.calculate_all_imports_and_files_methods_and_classes_testing(file_content)
                self.requisite_import_lines = self.calculate_requisite_import_lines()

    def calculate_all_imports_and_files_methods_and_classes_testing(self, file_content_in) -> list:
        """Return the set that is to become self.all_imports, followed by the set that is to become self.files_methods_and_classes_testing.
        :param file_content_in: list.   newline-separated list of strings comprising the content of the test.  Should include leading whitespace.
        """
        # Get all_import_lines, a list of all import lines that occur at the module level, at the level of the class
        # containing the method, or at the level of the method in question.
        all_import_lines = []
        module_lines = get_module_level_only_from_file_content(file_content_in)
        class_lines = self.class_content
        method_lines = self.test_content
        for these_lines in [module_lines, class_lines, method_lines]:
            for this_line in these_lines:
                this_line_no_whitespace = strip_custom(this_line, ["\t", " "], "head")
                # TODO: Make the below robust to docstringed lines that begin with "from" or "import"
                this_line_no_whitespace_no_trailing_comment = strip_custom(remove_trailing_comment(this_line_no_whitespace), ["\t", " "], "tail")
                if this_line_no_whitespace_no_trailing_comment.startswith("import ") or (this_line_no_whitespace_no_trailing_comment.startswith("from ") and " import " in remove_trailing_comment(this_line_no_whitespace_no_trailing_comment)):
                    all_import_lines.append(this_line_no_whitespace_no_trailing_comment)

        # Get all_imported_vars_classes_functions_verbatim, a list of all imported vars, classes, and functions that *could* be
        # used by the method, verbatim to the way that the method would use them.
        all_imported_vars_classes_functions_verbatim = []
        verbatim_to_absolute_for_asterisk_imports = {}  # Keys are verbatim references for asterisked imports, values are absolute expressions for them
        alias_to_aliased = {}  # Keys are aliases established using the "as" keyword, values are the actual thing being referred to by the alias in non-absolute terms
        verbatim_to_import_line = {}    # Keys are verbatim references to an import, values are import lines from all_import_lines
        for element in all_import_lines:
            if element.startswith("import "):
                # Append each thing afterward, shaving trailing commas, handling "as" aliases as appropriate
                after_imports = element[7:].split(" ")
                for ii in range(len(after_imports)):
                    this_after_import = after_imports[ii]
                    this_after_import_no_comma = strip_custom(this_after_import, [","], "tail")
                    # Handle an import that's about to be aliased
                    if len(after_imports) > ii + 2 and after_imports[ii+1] == "as":
                        alias = strip_custom(after_imports[ii+2], [","], "tail")
                        all_imported_vars_classes_functions_verbatim.append(strip_custom(after_imports[ii+2], [","], "tail"))
                        alias_to_aliased[alias] = this_after_import_no_comma
                        verbatim_to_import_line[alias] = element
                    # Ignore commaless "as" and any entry following a commaless "as"
                    elif this_after_import == "as" or (ii > 0 and after_imports[ii-1] == "as"):
                        pass
                    # Default case
                    else:
                        all_imported_vars_classes_functions_verbatim.append(this_after_import_no_comma)
                        verbatim_to_import_line[this_after_import_no_comma] = element
            else:   # element must start with "from "
                if "*" in element:  # Handle asterisk imports by searching that file for all outermost classes and functions
                    between_from_and_import = element[element.index("from ")+5:element.index(" import ")]
                    # Get results from top-level directory
                    leads_from_top_of_project = self.python_files_and_folders_in_directory_matching_name(ROOT_DIR, between_from_and_import, files_only=True)
                    # Get results from this file's folder if it's not the project directory
                    if path.dirname(self.test_filepath) != ROOT_DIR:
                        leads_from_file_directory = self.python_files_and_folders_in_directory_matching_name(path.dirname(self.test_filepath), between_from_and_import, files_only=True)
                    else:
                        leads_from_file_directory = []
                    # Combine these results
                    combined_results = leads_from_top_of_project + leads_from_file_directory
                    # Search each file in combined_results for classes and functions, and add all of them to all_imported_vars_classes_functions_verbatim
                    for result in combined_results:
                        if result[0] == "file":
                            with open(result[1], "r", encoding="utf-8") as result_wrapper:
                                result_content = result_wrapper.readlines()
                            for line in result_content:
                                # If begins with no whitespace (indicating outermost) and is a class or function definition, add it, and store both the verbatim and absolute reference in verbatim_to_absolute_for_asterisk_imports
                                if len(line) > 0 and line[0] not in ["\t", " ", "\n"]:
                                    if line.startswith("class "):   # TODO: Make robust to docstringed "class " with no leading whitespace
                                        all_imported_vars_classes_functions_verbatim.append(get_class_name_from_definition_line(line))
                                        verbatim_to_absolute_for_asterisk_imports[all_imported_vars_classes_functions_verbatim[-1]] = between_from_and_import + "." + all_imported_vars_classes_functions_verbatim[-1]
                                    elif line.startswith("def "):   # TODO: Make robust to docstringed "def " with no leading whitespace
                                        all_imported_vars_classes_functions_verbatim.append(get_method_name_from_definition_line(line))
                                        verbatim_to_absolute_for_asterisk_imports[all_imported_vars_classes_functions_verbatim[-1]] = between_from_and_import + "." + all_imported_vars_classes_functions_verbatim[-1]
                else:   # "from" import with no asterisk; append each thing imported after the first " import " on the line, shaving trailing commas, handling "as" aliases as appropriate
                    index_first_import = element.index(" import ")
                    after_imports = element[index_first_import+8:].split(" ")
                    for ii in range(len(after_imports)):
                        this_after_import = after_imports[ii]
                        this_after_import_no_comma = strip_custom(this_after_import, [","], "tail")
                        # Handle an import that's about to be aliased
                        if len(after_imports) > ii + 2 and after_imports[ii + 1] == "as":
                            alias = strip_custom(after_imports[ii + 2], [","], "tail")
                            all_imported_vars_classes_functions_verbatim.append(
                                strip_custom(after_imports[ii + 2], [","], "tail"))
                            alias_to_aliased[alias] = this_after_import_no_comma
                            verbatim_to_import_line[alias] = element
                        # Ignore commaless "as" and any entry following a commaless "as"
                        elif this_after_import == "as" or (ii > 0 and after_imports[ii - 1] == "as"):
                            pass
                        # Default case
                        else:
                            all_imported_vars_classes_functions_verbatim.append(this_after_import_no_comma)
                            verbatim_to_import_line[this_after_import_no_comma] = element
        # Remove duplicates
        all_imported_vars_classes_functions_verbatim = list(set(all_imported_vars_classes_functions_verbatim))

        # Create imports_used, the subset of all_imported_vars_classes_functions_verbatim that actually appears in the test content
        imports_used = [element for element in all_imported_vars_classes_functions_verbatim if token_appears_in_method(element, method_lines)]

        # Create imports_used_absolute, which matches imports_used except each import is named in absolute terms.  Within each entry, "." is used as a separator.
        imports_used_absolute = []
        for this_import_used in imports_used:
            # De-alias this_import_used if it's an alias
            if this_import_used in alias_to_aliased:
                this_import_used_dealiased = alias_to_aliased[this_import_used]
            else:
                this_import_used_dealiased = this_import_used
            # Build the absolute version of this import by seeing how it's introduced in its import line
            # If it's from an asterisk import, just grab from the dictionary
            if this_import_used_dealiased in verbatim_to_absolute_for_asterisk_imports:
                this_import_used_absolute = verbatim_to_absolute_for_asterisk_imports[this_import_used_dealiased]
            # If it's not an asterisk import, figure out the absolute version the hard way:
            else:
                relevant_import_line = verbatim_to_import_line[this_import_used]
                chunks = []     # All chunks will be joined by dots to create this_import_used_absolute
                relevant_import_line_no_leading_whitespace = strip_custom(relevant_import_line, ["\t", " "], "head")
                relevant_import_line_space_separated = relevant_import_line_no_leading_whitespace.split(" ")
                # If the import line starts with "from", grab whatever is after it
                if relevant_import_line_no_leading_whitespace.startswith("from "):
                    chunks.append(relevant_import_line_space_separated[1])
                # Remove all portions of relevant_import_line_space_separated before and including the first "import" entry
                first_import_index = relevant_import_line_space_separated.index("import")
                relevant_import_line_space_separated = relevant_import_line_space_separated[first_import_index+1:]
                # Remove trailing commas from entries of relevant_import_line_space_separated
                for ii in range(len(relevant_import_line_space_separated)):
                    relevant_import_line_space_separated[ii] = strip_custom(relevant_import_line_space_separated[ii], [","], "tail")
                # Add the element of relevant_import_line_space_separated that ends with this_import_used_dealiased
                element_ending_with_this_import_used_dealiased = None
                for element in relevant_import_line_space_separated:
                    if element.endswith(this_import_used_dealiased):
                        element_ending_with_this_import_used_dealiased = element
                        break
                if element_ending_with_this_import_used_dealiased is None:
                    raise RuntimeError("couldn't find an element ending with this_import_used_dealiased")
                chunks.append(element_ending_with_this_import_used_dealiased)

                # Combine chunks, separating with dots
                this_import_used_absolute = ""
                for this_chunk in chunks:
                    this_import_used_absolute += this_chunk + "."
                this_import_used_absolute = this_import_used_absolute[:-1]

            # Append to imports_used_absolute
            imports_used_absolute.append(this_import_used_absolute)

        # Convert to set
        imports_used_absolute = set(imports_used_absolute)

        # Create user_written_imports_used_absolute, which is a subset of imports_used_absolute.
        # Filter imports_used_absolute so that user_written_imports_used_absolute only includes user-written imports
        # (for example, not math.pi).
        # For each entry in imports_used_absolute, check if user written:
        user_written_imports_used_absolute = set()
        user_written_files_to_absolute_locations = {}  # keys are elements of user_written_imports_used_absolute, values are absolute filepaths to the file being referenced for the import
        for this_import in imports_used_absolute:
            is_user_written = False     # Assume this_import isn't user-written until we find evidence otherwise

            # Get chunks
            chunks = this_import.split(".")

            # Initialize leads (possible things this import could be pointing to).
            # leads is a list of tuples (henceforth called "lead tuples"), each of which has the following elements:
            # [0]: category of lead: ["dir", "file", "class", "function"]
            # [1]: path to lead (or just the name of the class or function in the case of class or function category
            # [2]: absolute filepath
            # dirs are searched for dir leads and file leads.  files are searched for an outermost class or function
            leads = []

            # Follow the chunks for this import
            for cc in range(len(chunks)):
                this_chunk = chunks[cc]

                is_first_chunk = (cc == 0)
                is_last_chunk = (cc == len(chunks) - 1)

                if is_first_chunk:
                    # Load up leads with the files/directories at the uppermost directory that match the chunk.
                    # If the test isn't at the uppermost directory, then also check the test's directory
                    folders_to_check = [ROOT_DIR]
                    if path.dirname(self.test_filepath) != ROOT_DIR:
                        folders_to_check.append(path.dirname(self.test_filepath))
                    for folder_to_check in folders_to_check:
                        leads += self.python_files_and_folders_in_directory_matching_name(folder_to_check, this_chunk)

                elif not is_first_chunk:
                    # Expand forward from leads, replacing the old leads
                    old_leads = leads.copy()
                    leads = []
                    for this_old_lead in old_leads:
                        if this_old_lead[0] == "dir":   # If previous lead was a directory:
                            # Find files/directories matching this chunk
                            to_append = self.python_files_and_folders_in_directory_matching_name(this_old_lead[1], this_chunk)
                            for element in to_append:
                                leads.append(element)
                        elif this_old_lead[0] == "file":    # If previous lead was a file:
                            # Find outermost classes/functions matching this chunk
                            with open(this_old_lead[1], "r", encoding="utf-8") as lead_file:
                                lead_file_content = lead_file.readlines()
                            for this_line in lead_file_content:
                                # If this line doesn't begin with whitespace and is a class or function def line whose
                                # name matches this_chunk, then it's an outermost class or function,
                                # so append it as a lead.
                                if len(this_line) > 0 and this_line[0] not in ["\t", " ", "\n"]:
                                    if this_line.startswith("class ") and get_class_name_from_definition_line(this_line) == this_chunk:
                                        leads.append(("class", this_chunk, this_old_lead[2]))
                                    elif this_line.startswith("def ") and get_method_name_from_definition_line(this_line) == this_chunk:
                                        leads.append(("function", this_chunk, this_old_lead[2]))
                        elif this_old_lead[0] == "class":   # If previous lead was a class:
                            # Dead end; append nothing
                            pass
                        elif this_old_lead[0] == "function":    # If previous lead was a function:
                            # Dead end; append nothing
                            pass
                        else:
                            raise RuntimeError(f"lead category {str(this_old_lead[0])} not a valid lead category")

                if is_last_chunk:
                    # Check if any of the current leads match the last chunk and are a file, class, or function.
                    # If so, we've found a user-written file/class/function that matches the import statement, so set
                    # is_user_written to True!  Also log the absolute filepath of the file being
                    # referenced in the import
                    for this_lead in leads:
                        if this_lead[0] in ["file"]:
                            if path.basename(this_lead[1]) == this_chunk + ".py":
                                is_user_written = True
                                user_written_files_to_absolute_locations[this_import] = this_lead[2]
                                break
                        elif this_lead[0] in ["class", "function"]:
                            if this_lead[1] == this_chunk:
                                is_user_written = True
                                user_written_files_to_absolute_locations[this_import] = this_lead[2]
                                break

            # If user-written, append to the set!
            if is_user_written:
                user_written_imports_used_absolute.add(this_import)

        # Make imports_used_absolute_folder_normalized and user_written_imports_used_absolute_folder_normalized, which
        # are versions of imports_used_absolute and user_written_imports_used_absolute in which imports include chunks
        # representing the path from the top-level project directory down to the file
        # used in the import.
        user_written_imports_used_absolute_folder_normalized = set()
        imports_used_absolute_folder_normalized = set()
        for this_import in user_written_imports_used_absolute:  # Handle user-written imports
            chunks = this_import.split(".")

            # To the beginning of this_import, add chunks for the directories that need to be opened, in
            # order, to get from the topmost project directory to the file being imported.
            # Get the filepath from the topmost project directory to the file being imported
            this_import_absolute_filepath = user_written_files_to_absolute_locations[this_import]
            this_import_relative_filepath = path.dirname(path.relpath(this_import_absolute_filepath, ROOT_DIR))

            # Working from the bottom up through these folders, add each one to the front of the chunks if it isn't
            # already somewhere in this_import.
            if platform in ["win32", "win64"]:
                this_import_relative_filepath_chunked = this_import_relative_filepath.split("\\")
            elif platform in ["darwin", "linux"]:
                this_import_relative_filepath_chunked = this_import_relative_filepath.split("/")
            else:
                raise RuntimeError("Unfamiliar operating system. Don't know the default folder separation character (eg /, \\)for this OS")
            if this_import_relative_filepath_chunked == [""]:   # Cleanup from some strangeness of how split() on an empty string works
                this_import_relative_filepath_chunked = []
            for ii in range(len(this_import_relative_filepath_chunked)-1, -1, -1):
                this_folder = this_import_relative_filepath_chunked[ii]
                if this_folder not in chunks:
                    # Add this folder and all folders above it, then break
                    chunks = this_import_relative_filepath_chunked[0:ii+1] + chunks
                    break

            # Assemble this_import_folder_normalized from the chunks
            this_import_folder_normalized = ""
            for chunk in chunks:
                this_import_folder_normalized += chunk + "."
            if this_import_folder_normalized.endswith("."):
                this_import_folder_normalized = this_import_folder_normalized[:-1]

            # Add to both output sets
            imports_used_absolute_folder_normalized.add(this_import_folder_normalized)
            user_written_imports_used_absolute_folder_normalized.add(this_import_folder_normalized)

        for this_import in imports_used_absolute:   # Handle imports of files that aren't user-written
            if this_import not in user_written_imports_used_absolute:
                imports_used_absolute_folder_normalized.add(this_import)

        # Return!
        return [imports_used_absolute_folder_normalized, user_written_imports_used_absolute_folder_normalized]

    def calculate_requisite_import_lines(self) -> set:
        """Convert each absolute import from self.all_imports to actual import commands
        (eg 'import foo', 'from foo import bar', or 'from foo.bar import baz')
        """
        imports_out = set()
        for import_in in self.all_imports:
            import_in_split = import_in.split(".")
            # Handle adding the "import foo" bit at the end
            import_out = f"import {import_in_split[-1]}"
            # If a "from" and additional components is needed, add those
            if len(import_in_split) >= 2:
                import_out = " " + import_out
                for ii in range(len(import_in_split)-2, -1, -1):
                    import_out = "." + import_in_split[ii] + import_out
                import_out = "from " + import_out[1:]

            imports_out.add(import_out)

        return imports_out

    def python_files_and_folders_in_directory_matching_name(self, directory: str, name: str, files_only=False):
        """Return a list of all folders and .py files in directory matching name, after removing .py file extension.
        Each is formatted as a lead tuple (described in TestMethod.calculate_all_imports_and_files_methods_and_classes_testing()).
        :param directory        absolute filepath to a directory
        :param name             filename with no file extension.  MAY ALSO BE A SERIES OF CHUNKS CONNECTED BY DOTS, BUT SHOULD STILL HAVE NO FILE EXTENSIONS.
        :param files_only       set to true to only get files, not directories
        """
        # Handle errors
        # directory not a string
        if not isinstance(directory, str):
            raise TypeError("directory must be a string")
        # directory empty
        if len(directory) == 0:
            raise ValueError("directory must not be an empty string")
        # name not a string
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        # name empty
        if len(name) == 0:
            raise ValueError("name must not be an empty string")
        # name ends in .py
        if name.endswith(".py"):
            warn("name should not have a file extension, but ends with '.py'")

        # Run!
        matches = []
        if "." not in name:
            folder_contents = listdir(directory)
            for contained in folder_contents:
                # Check for contained being a matching file
                if contained.endswith(".py"):
                    contained_no_file_extension = strip_file_extension(contained)
                    if contained_no_file_extension == name:
                        matches.append(("file", path.join(directory, contained), path.join(directory, contained)))
                # check for contained being a matching directory
                elif contained == name:
                    matches.append(("dir", path.join(directory, contained), path.join(directory, contained)))
        elif "." in name and files_only:
            chunks = name.split(".")
            for cc in range(len(chunks)):
                this_chunk = chunks[cc]
                is_first_chunk = (cc == 0)
                is_last_chunk = (cc == len(chunks) - 1)
                if is_first_chunk:
                    if is_last_chunk:
                        # Add all files with the chunk name to matches
                        for contained in listdir(directory):
                            if contained.endswith(".py") and strip_file_extension(contained) == this_chunk:
                                matches.append(("file", path.join(directory, contained), path.join(directory, contained)))
                    else:   # Not the last chunk:
                        # Add all directories with the chunk name to matches
                        for contained in listdir(directory):
                            if contained == this_chunk:
                                matches.append(("dir", path.join(directory, contained), path.join(directory, contained)))
                else:   # elif not is_first_chunk:
                    old_matches = matches.copy()
                    matches = []
                    if is_last_chunk:
                        # Search all directories in old_matches for one or more files with the chunk name
                        for old_match in old_matches:
                            if old_match[0] == "dir":
                                for contained in listdir(old_match[1]):
                                    if contained.endswith(".py") and strip_file_extension(contained) == this_chunk:
                                        matches.append(("file", path.join(old_match[1], contained), path.join(old_match[1], contained)))
                    else:   # Not the last chunk:
                        # Search all directories in old_matches for one or more directories with the chunk name
                        for old_match in old_matches:
                            if old_match[0] == "dir":
                                for contained in listdir(old_match[1]):
                                    if contained == this_chunk:
                                        matches.append(("dir", path.join(old_match[1], contained), path.join(old_match[1], contained)))
        else:
            raise NotImplementedError("not yet designed to handle names with '.'s when directories are desired in addition to files")

        return matches
