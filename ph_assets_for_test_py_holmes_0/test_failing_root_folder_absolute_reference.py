"""For use by test_py_holmes.TestWhenOriginalFileInDeeperFolder"""


import unittest
from failing_root_folder import give_one


class TestClass(unittest.TestCase):
    def test_method(self):
        pointless_literal = 42
        self.assertEqual(0, give_one())
