import unittest     # We must import the unittest module.
from circle_method import circle_area    # We must import whatever we want to test.
from math import pi

import logging

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

    def test_create_failure_in_test_method(self):
        """Produce a failure (not an error) in this test method itself."""
        self.assertEqual(1, 2)

    def test_create_failure_on_assertEqual(self):
        self.assertEqual(1, 2)

    def test_create_failure_on_assertNotEqual(self):
        self.assertNotEqual(1, 1)

    def test_create_failure_on_assertTrue(self):
        self.assertTrue(False)

    def test_create_failure_on_assertFalse(self):
        self.assertFalse(True)

    def test_create_failure_on_assertIs(self):
        self.assertIs("hi", "bye")

    def test_create_failure_on_assertIsNot(self):
        self.assertIsNot("hi", "hi")

    def test_create_failure_on_assertIsNone(self):
        self.assertIsNone("hi")

    def test_create_failure_on_assertIsNotNone(self):
        self.assertIsNotNone(None)

    def test_create_failure_on_assertIn(self):
        self.assertIn("beans", ["eggs", "fish"])

    def test_create_failure_on_assertNotIn(self):
        self.assertNotIn("beans", ["beans", "eggs", "fish"])

    def test_create_failure_on_assertIsInstance(self):
        self.assertIsInstance("hi", int)

    def test_create_failure_on_assertNotIsInstance(self):
        self.assertNotIsInstance("hi", str)

    def test_create_failure_on_assertRaises(self):
        with self.assertRaises(ValueError):
            my_var = 2 + 2

    def test_create_failure_on_assertRaisesRegexp(self):
        with self.assertRaisesRegexp(ValueError, "foo"):
            raise ValueError("bar")

    def test_create_failure_on_assertAlmostEqual(self):
        self.assertAlmostEqual(3, 4)

    def test_create_failure_on_assertNotAlmostEqual(self):
        self.assertNotAlmostEqual(3, 3.0000000000000000000000000000000000000000000000001)

    def test_create_failure_on_assertGreater(self):
        self.assertGreater(0, 1)

    def test_create_failure_on_assertGreaterEqual(self):
        self.assertGreaterEqual(0, 1)

    def test_create_failure_on_assertLess(self):
        self.assertLess(1, 0)

    def test_create_failure_on_assertLessEqual(self):
        self.assertLessEqual(1, 0)

    def test_create_failure_on_assertRegexpMatches(self):
        self.assertRegexpMatches("bot", "bat")

    def test_create_failure_on_assertNotRegexpMatches(self):
        self.assertNotRegexpMatches("bot", "bot")

    def test_create_failure_on_assertCountEqual(self):
        self.assertCountEqual(["foo", "bar"], ["foo", "bees"])

    def test_create_failure_on_assertWarns(self):
        with self.assertWarns(UserWarning):
            my_var = 2 + 2

    def test_create_failure_on_assertWarnsRegex(self):
        with self.assertWarnsRegex(RuntimeWarning, "oh no"):
            my_var = 2 + 2

    def test_create_failure_on_assertLogs(self):
        with self.assertLogs("foo", level="INFO") as cm:
            my_var = 2 + 2

    def test_create_failure_on_assertMultiLineEqual(self):
        a = """this
        is
        a
        string"""
        b = """here's
        a
        different
        string"""
        self.assertMultiLineEqual(a, b)

    def test_create_failure_on_assertSequenceEqual(self):
        self.assertSequenceEqual([0, 5, 10], [0, 10, 20])

    def test_create_failure_on_assertListEqual(self):
        self.assertListEqual([0, 5, 10], [0, 10, 20])

    def test_create_failure_on_assertTupleEqual(self):
        self.assertTupleEqual((0, 5, 10), (0, 10, 20))

    def test_create_failure_on_assertSetEqual(self):
        a = {0, 5, 10}
        b = {0, 10, 20}
        self.assertSetEqual(a, b)

    def test_create_failure_on_assertDictEqual(self):
        a = {
            "foo": "bar"
        }
        b = {
            "fuzz": "buzz"
        }
        self.assertDictEqual(a, b)
