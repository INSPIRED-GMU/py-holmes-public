"""Dummy test for use in certain tests in test_py_holmes.py.
"""


import unittest


class TestAllLiterals(unittest.TestCase):
    def test_all_literals(self):
        """Failing test which involves all categories of literal node for Python's ast module.
        These categories are: Constant, JoinedStr, List, Tuple, Set, Dict
        """
        my_const = 3
        my_joined_str = f"here's a number: {my_const}"
        my_list = ["hi", "bye", "yo"]
        my_tuple = ("hi", "bye", "yo")
        my_set = {"hi", "bye", "yo"}
        my_dict = {
            "zero": 0,
            "one": 1,
            "two": 2,
            "three": 3
        }
        self.assertEqual(my_const, len(my_dict))
