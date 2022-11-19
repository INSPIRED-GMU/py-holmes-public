"""Test code used as an example in demo paper 1.
"""


import unittest
from demo_1 import word_to_int


class TestWordToInt(unittest.TestCase):
    def test_direction_of_increase(self):
        """Get word_to_int()'s output on two different words with the same
        number of letters a-z.
        Check that the correct word corresponds to a larger int.
        """
        self.assertTrue(word_to_int("can't") < word_to_int("door"))
