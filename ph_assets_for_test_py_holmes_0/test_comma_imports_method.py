"""Dummy test for use in certain tests in test_py_holmes.py.
"""


import unittest
from ph_assets_for_test_py_holmes_0.comma_imports_method import compute
from ph_assets_for_test_py_holmes_0.comma_imports_imported import my_sin, my_cos, my_tan


class TestCommaImportsMethod(unittest.TestCase):
    def test_comma_imports_method_with_from(self):
        """Passes"""
        self.assertAlmostEqual(my_sin(my_cos(my_tan(1))), compute())
