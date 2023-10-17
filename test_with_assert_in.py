"""Dummy test for use in certain tests in test_py_holmes.py
"""


import unittest


class TestWithAssertIn(unittest.TestCase):
    def test_with_assert_in(self):
        """Failing test in which self.assertIn() is used
        """
        self.assertIn("beans", ["eggs", "fish"])
