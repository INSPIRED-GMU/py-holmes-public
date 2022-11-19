# py-holmes
Adaptation of the causal testing tool [Holmes](https://cs.gmu.edu/~johnsonb/docs/Johnson20icse.pdf) for Python unit testing.  Submitted as an artifact along with our paper *Py-holmes: Causal Testing for Python*.

It is not possible to run multiple runtimes of py-holmes in parallel, because of the way it writes and reads temporary files.


# Installation
## Format of your project
Py-holmes has certain requirements for the format of your project.  They are as follows:
1. No user-written function may have its definition line span more than one row in the file.
2. All unit test files must either begin or end with the word "test", and no other files in the project may begin this way.
3. No file should import more than one module on the same line.  For example, `import math, random` is not acceptable, but `from math import sin, cos` is.  This standard is also imposed by [PEP 8](https://peps.python.org/pep-0008/#imports).
4. No file should use relative imports; [PEP 8](https://peps.python.org/pep-0008/#imports) imposes this standard as well.  In addition, py-holmes does not permit explicit relative imports.  Only absolute imports are permitted.
5. Py-holmes requires the user to communicate which arguments in `unittest.TestCase.assert*()` calls are oracles, by using py-holmes's convention for oracle positions discussed in our paper.
6. Your uppermost project folder should not contain or be contained by the default Python install folder for your operating system.  Your uppermost project folder may contain the folder of the Python executable you're using, but your project folder must not be contained by it.
7. Your project should not contain any files with the following name: `test_outputs_fuzzed.py`

The current version of py-holmes is designed for use with the \texttt{unittest} module exclusively, and is therefore not compatible with \texttt{pytest}, another popular unit testing framework for Python.  It also is not completely autonomous, possibly relying on a user to point out which argument is an oracle in certain calls to class 2 assert methods.

The fuzzing process also contains limitations.  Py-holmes cannot fuzz a test that has no literals.  Furthermore, its process of protecting oracle literals from being fuzzed is incomplete.  If the test contains mutator functions which change the value of an oracle variable without using an \texttt{=} operator, then all literal arguments of those mutator functions could play a role in defining the oracle, yet py-holmes will not notice to protect those literals from fuzzing.

## Directory setup
Clone this repository to your local machine.  The root directory of this repository should double as the root directory of your project.

If you're a developer of py-holmes and wish to use BugsInPy to benchmark its behavior, you'll also need to install BugsInPy such that its root directory is at ph_benchmarks/ph_BugsInPy/BugsInPy.

## .holmesignore and .holmessearchextend
If you have any files for which you would like causal testing NOT to be run when these files
are responsible for failing tests, it is recommended that you name these files in a .holmesignore file (just like
you would create a .gitignore).  This file should be in the top level of your project folder.  Causal testing may be
performed without this file but may incur warnings.  Begin a line in .holmesignore with / to create an absolute
filepath.  Your test module will automatically be added to .holmesignore if it is not already covered, but failures
that originate in it will still be caught.

If your project involves any files not found in the project folder, interpreter folder, or default Python install
location for our OS, it is recommended that you name these files in a .holmessearchextend file (same syntax as a
.gitignore).  This file should be in the top level of your project folder.  Begin a lines in .holmessearchextend with /
to create an absolute filepath.

## Dependencies
The following packages must be installed:
* pip install hypothesis
* pip install black
* pip install -U pytest
* pip install astor
* pip install python-Levenshtein
* pip install pylint
* pip install colorama

# Usage and internal process
![PyHolmesFlowchart](ph_readme_images/py-holmes-demo-paper-1-flowchart-1.png)

Py-holmes's procedure is summarized in the figure above.  A user calls py-holmes using its command line interface.  An example of a typical call is `python py_holmes.py -f tests/my_test.py -l 20 25`.  This command would run py-holmes on two tests contained within the file `tests/my_test.py`: one on line 20, and another on line 25.

The full list of CLI options is as follows:

- `-f`/`--file` indicates the file containing the unit test(s) on which to run causal testing
- `-l`/`--lines` indicates the line(s) in that file on which the test(s) appear.  Each test must belong to a `unittest.TestCase` class.  Alternatively `-l all` can be given to run all causal testing on all unit tests in the file. 
- Optional arguments:
    - `-t`/`--tatosp` is followed by a single integer.  It sets how many spaces a tab is equivalent to, in case any project files indent using a mixture of tabs and spaces.  *However, mixing tabs and spaces is discouraged in Python.*  The default value is 4.
    - `-p`/`--passing_tests_include` is a flag.  Without this argument, py-holmes does not run causal testing on unit tests that pass.
    - `-c`/`--character_palette_manual` is a flag.  Without this argument, py-holmes infers what characters it can insert into a fuzzed string by observing which of the following groups of characters are represented in the original string: (1) lowercase letters a-z, (2) uppercase letters A-Z, (3) digits 0-9, (4) punctuation in the set {.!?,}, (5) four-function arithmetic symbols in the set {+-/*}, (5) parentheses, (6) square brackets, (7) curly braces, and (8) angle brackets.  We call each of these groups a *character family*.  Including the `-c`/`--character_palette_manual` flag allows the user to give a palette of characters that py-holmes should choose from instead, given as a string of all those characters.  Py-holmes will request this palette later during its runtime, on a string-by-string basis.
    - `-n`/`--num_test_variants` is followed by a single integer.  It sets the number of fuzzed test variants py-holmes creates.  The default value is 50.
    - `-v`/`--variant\_testing\_time\_limit\_seconds` is followed by a single integer.  It sets the time limit (in seconds) for py-holmes to run fuzzed variants of the user's unit test.  After this much time has elapsed, no more variant tests will be started.  The default value is 60.
    - `-u`/`--user_help_skip` is a flag.  If this argument is given, py-holmes will guess arbitrarily when it's unclear which argument to a class 2 assert function is an oracle, rather than asking the user at runtime.
    - `-d`/`--dev_only_test_mode` is a flag.  If this argument is given, py-holmes will produce additional readouts to assist with testing and debugging, both in the forms of printed content and generated files.

Py-holmes runs each requested test as-is and records its entire execution path.  If the test passes, py-holmes skips further action on that test unless the `-p`/`--passing_tests_include` flag was given.  Otherwise, py-holmes runs causal testing on that test (now referred to as the *original test*).  The remainder of this subsection describes how that causal testing is undertaken.

Py-holmes finds all tests in the project that are both *scope-similar* and *call-similar* to the original test.  We define scope-similarity as using a nonempty subset of the same user-written files, functions, and classes, and call-similarity as making function calls in exactly the same order (ignoring the arguments of those functions).

Py-holmes then produces fuzzed variants of the original test, as well as all tests that are both scope-similar and call-similar.  Fuzzing is performed by identifying all literals in a test which are not involved in defining an oracle argument of a `unittest.TestCase.assert*()` call, where `*` is a wildcard.  Literals are identified by parsing a unit test's body as an abstract syntax tree using Python's built-in `ast` module.  Any literals that are used as oracles, or involved in determining the value of an oracle, are skipped over, to protect them from fuzzing.  This process of identifying literals to protect is discussed further in our paper.  By default, a total of 50 fuzzed variant tests are produced.  If any tests are being fuzzed other than the original test, then roughly half of the fuzzed tests will be variants of the original test, and the remaining tests will be variants of the other tests, in as uniform a distribution across them as possible.  Each fuzzed variant of the original test has only one literal fuzzed, so that if a variant passes, the reason will be easier for the user to interpret.  Fuzzed variants of other tests have all their non-oracle literals fuzzed.

How a particular literal is fuzzed depends on its data type.
- If the literal is **boolean**, it has a 50% chance to have its value flipped.
- If the literal is **numeric** (an int, float, or complex), py-holmes adds or subtracts a value up to 2 times its order of magnitude.  For example, if the value was originally 2050, then an integer in the range [-2000, 2000] will be added.  The number then has a 25% chance to have its value negated.  If the number is complex, it then undergoes a random angle change in the range [-pi/16, pi/16].
- If the literal is a **string**, py-holmes makes a random choice to either remove, insert, or change a character, each option having uniform probability.  This process repeats for a total of 1-3 times, chosen at random with uniform probability.
    - To *remove* a character, a character position is chosen at random, then removed from the string.
    - To *insert* a character, a random position is chosen between two characters, or at the front or end of the string.  Next a character is selected to insert, either by drawing uniformly from a user-provided palette (if the user used the `-c` flag), or by choosing a character in the same family as a *character family* already in the string.
    - To *change* a character, a character is chosen at random, and then replaced with a character as per the insertion operation described previously.

Once fuzzed variant tests have been produced, py-holmes runs as many as possible within the time limit determined by the `-v` parameter.  Py-holmes prioritizes running fuzzed variants of the original test over fuzzed variants of other tests.  Once variant test running is complete, py-holmes finds the 3 passing and 3 failing test variants that had the most similar execution paths to the original test's execution path.

An example of an execution path is shown in the image below.  Lines fitting the form `--- modulename: A, funcname: B` indicate entry into a function `B` contained within a file `A`.  Lines beginning with `||| exiting modulename: A, funcname: B` indicate an exit from that function.  Every line of Python code that is executed produces another sequential line in the execution path.  To calculate the distance between two execution traces, a diff of the text representations of the functions is obtained, using `difflib.ndiff()`.  Each line insertion or removal in this diff contributes 1 distance to the total distance between the execution paths.  If the insertion or removal involves entry into a function, it contributes 10 distance instead.

![ExampleExecutionTrace](ph_readme_images/example-execution-trace.png)

Py-holmes concludes by presenting the user with a report containing the following information for each of the 3 passing and 3 failing test variants whose execution paths are most similar to the original test's execution path:

- Whether the test passed or failed
- A diff of changes made to the test's code
- A diff of the execution path changes, omitting any long stretches of unchanged lines by replacing them with a `(...)`

The figure below shows an example of a report that py-holmes might output for a single test variant.  For brevity, it excludes most of the execution path diff.

![ExampleReport](ph_readme_images/example-report-snippet-cropped-more.png)


# Purpose of each folder
The purposes of this project's subdirectories are as follows:
- `ph_assets_for_test_py_holmes_0` and `ph_assets_for_test_py_holmes_1` contain files that are used by tests contained within the file `test_py_holmes.py`.
- `ph_basic_processing` covers simple tasks like string parsing, some file searching, and post-test cleanup.
- `ph_benchmarks` is only needed by developers building py-holmes itself.  It contains benchmarking datasets and tools for testing and designing py-holmes.
- `ph_causal_testing` contains files for the various subtasks of causal testing, such as identifying oracle literals, fuzzing literals, running tests.
- `ph_log_writing` contains files for transforming py-holmes's console output into log files when desired.
- `ph_original_test_result_generation` contains files for running the user's original test and structuring information about  it.
- `ph_readme_images` contains images for use in this readme file.
- `ph_traceback_dataset` contains a dataset of execution tracebacks used in designing and testing py-holmes.
- `ph_variable_sharing` contains files for conveniently distributing variables that are needed widely across py-holmes.
