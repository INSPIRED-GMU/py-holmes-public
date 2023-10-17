"""Dummy test for use in certain tests in test_py_holmes.py.
"""


import unittest


class TestLiteralsIndirectlyLinkedToOracles(unittest.TestCase):
    def test_literals_indirectly_linked_to_oracles(self):
        """Failing test which involves literals that influence the values of oracle variables, even though those
        literals are not in oracle positions themselves
        """
        my_const_desired = 3
        my_const_result = 4
        my_joined_str_desired = f"here's a number: {6}"
        my_joined_str_result = f"here's another number: {8}"
        self.assertEqual(my_const_desired, my_const_result)
        self.assertEqual(my_joined_str_desired, my_joined_str_result)
