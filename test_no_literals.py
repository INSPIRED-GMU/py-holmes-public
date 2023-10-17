"""Dummy test for use in certain tests in test_py_holmes.py.
"""


import unittest
from math import pi, e


class TestNoLiterals(unittest.TestCase):
    def test_no_literals(self):
        """Failing test which involves no literals.
        """
        self.assertEqual(pi, e)
