"""Dummy test for use in certain tests in test_py_holmes.py.
"""


import unittest
from math import sin, cos, tan


class TestAsImportsMethods(unittest.TestCase):
    def test_using_import_foo_as_bar(self):
        """Passes"""
        import ph_assets_for_test_py_holmes_0.as_imports_methods as methods
        self.assertEqual(methods.compute0(), sin(cos(tan(0))))

    def test_using_from_foo_import_bar_as_baz(self):
        """Passes"""
        from ph_assets_for_test_py_holmes_0.as_imports_methods import compute0 as method
        self.assertEqual(method(), sin(cos(tan(0))))

    def test_using_from_foo_import_bar_as_baz_comma_car_as_caz(self):
        """Passes"""
        from ph_assets_for_test_py_holmes_0.as_imports_methods import compute0 as method0, compute1 as method1
        self.assertNotEqual(method0(), method1())
