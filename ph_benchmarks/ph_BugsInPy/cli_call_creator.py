"""Generate a py_holmes call to be run by snek_detective.sh"""


import os
import argparse
import sys
from ast import parse, NodeVisitor, AST
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(ROOT_DIR)   # So that we can import other files even when this file is called from the command line


class FunctionDefLineFinder(NodeVisitor):
    """Given a name of a function and an AST of the entire content of the file containing it, return the line on which
    that function is defined.
    """

    def __init__(self, funcname: str, root: AST):
        # Handle errors
        # funcname not a string
        if not isinstance(funcname, str):
            raise TypeError("funcname must be a string")
        # root not an AST
        if not isinstance(root, AST):
            raise TypeError("root must be an AST object")

        self.funcname = funcname
        self.root = root

    def get_defline_lineno(self) -> int:
        """Return the line number on which funcname is defined, starting counting at 1."""
        return self.generic_visit(self.root)

    def generic_visit(self, node) -> int:
        """If this node is a FunctionDef and its name equals self.funcname, return the lineno of this node."""
        if type(node).__name__ == "FunctionDef" and node.name == self.funcname:
            return node.lineno

        # Call the base generic_visit so that other nodes are visited
        NodeVisitor.generic_visit(self, node)


if __name__ == "__main__":
    """Given a unittest command, such as
    'python -m unittest -q test.test_InfoExtractor.TestInfoExtractor.test_parse_mpd_formats', generate the py_holmes 
    call to be run on that test.
    This method requires the file to already have been checked out to
    ph_benchmarks/ph_BugsInPy/TEMP/projects/<project_name>
    """
    # Parse arguments
    parser = argparse.ArgumentParser("Given a unittest command, find the line number of the signature of the relevant test method")
    parser.add_argument("--project_name", "-p", action="store", nargs=1, type=str, required=True,help="Name of the project in BugsInPy which was checked out to", dest="project_name")
    parser.add_argument("--unittest_command", "-u", action="store", nargs=1, type=str, required=True,help="Unittest command in bugsinpy_run_test.sh", dest="unittest_command")

    args = parser.parse_args()
    project_name = args.project_name[0]
    unittest_command = args.unittest_command[0]

    # Handle errors
    # project_name not a string
    if not isinstance(project_name, str):
        raise TypeError("project_name must be a string")
    # project_name empty
    if len(project_name) == 0:
        raise ValueError("project_name must not be empty")
    # unittest_command not a string
    if not isinstance(unittest_command, str):
        raise TypeError("unittest_command must be a string")
    # unittest_command isn't a unittest command
    if not unittest_command.startswith("python") or "unittest" not in unittest_command:
        raise ValueError("unittest_command doesn't look like a unittest command")

    # Grab the last word of the command
    last_word = unittest_command.split(" ")[-1]

    # Move to the directory containing the file.  (We're already in the ph_BugsInPy folder in the external folder that was copied to
    old_directory = os.getcwd()
    os.chdir(f"../..")
    # Go into a deeper folder if needed, based on the command
    chunks = last_word.split(".")
    if len(chunks) < 3:
        raise ValueError("the last word of unittest_command must contain at least two periods")
    chunks_before_file_class_and_method = chunks[:-3]
    for chunk in chunks_before_file_class_and_method:
        os.chdir(chunk)

    # Read the file content
    with open(f"{chunks[-3]}.py", "r", encoding="utf-8") as file:
        file_content = file.read()

    # Find entry line into the test method
    tree = parse(file_content)
    finder = FunctionDefLineFinder(funcname=chunks[-1], root=tree)
    method_signature_line = finder.get_defline_lineno()

    # Get filepath to test
    test_filepath = ""
    for chunk in chunks[:-2]:   # For all chunks but the class and test method:
        test_filepath += f"/{chunk}"
    test_filepath += ".py"
    if test_filepath.startswith("/"):
        test_filepath = test_filepath[1:]   # Remove leading slash so we're not mistakenly searching from system root

    # Return to the old directory and print the command to be used
    os.chdir(old_directory)
    print(f"python py_holmes.py -f {test_filepath} -l {method_signature_line} -p")
