import unittest     # We must import the unittest module.
from circle_method import circle_area    # We must import whatever we want to test.
from math import pi

# There are many, many other assert methods for unit testing that we do not cover here, but you can find them in the
# documentation for the unittest module.

# To run this entire unit circle test class, type this in the terminal: python -m unittest circle_method_test
# Or, to use unit tests for the whole folder, run python -m unittest

class TestCircleArea(unittest.TestCase):    # Each test method within this class must start with the word "test".  Each method here constitutes 1 test, and is caled a "test case".
    def test_area(self):
        """Tests areas when radius >= 0
        If any of these tests fail, then Python will register that test_area failed.
        """
        self.assertAlmostEqual(pi, circle_area(1))  # Checks to see if circle_area(1) returns a value almost equal to pi.
        self.assertAlmostEqual(0, circle_area(0))
        self.assertAlmostEqual(pi * 2.1 ** 2, circle_area(2.1))

    def test_values(self):
        """Tests for correct triggering of value errors when inappropriate inputs are given to circle_area."""
        self.assertRaises(ValueError, circle_area, -2)     # Checks to see if ValueError is raised when circle_area(-2) is run.

    def test_types(self):
        """Makes sure type errors are raised when necessary."""
        self.assertRaises(TypeError, circle_area, 2+5j)
        self.assertRaises(TypeError, circle_area, True)
        self.assertRaises(TypeError, circle_area, "Hello")

    def test_that_provokes_request_for_human_help(self):
        """Failing test that involves an assertIn() call that has the same number of variable names in both arguments,
        to provoke py-holmes to request human help.
        """
        self.assertIn(5, [0, 10])
