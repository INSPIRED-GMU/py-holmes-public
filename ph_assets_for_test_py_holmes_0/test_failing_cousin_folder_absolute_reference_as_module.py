"""For use by test_py_holmes.TestWhenOriginalFileInDeeperFolder"""


import unittest
from ph_assets_for_test_py_holmes_1 import failing_cousin_folder


class TestClass(unittest.TestCase):
    def test_method(self):
        pointless_literal = 42
        self.assertEqual(0, failing_cousin_folder.give_one())
