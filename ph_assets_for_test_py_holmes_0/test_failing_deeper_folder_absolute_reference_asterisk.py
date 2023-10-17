"""For use by test_py_holmes.TestWhenOriginalFileInDeeperFolder"""


import unittest
from ph_assets_for_test_py_holmes_0.deeper_folder.failing_deeper_folder import *


class TestClass(unittest.TestCase):
    def test_method(self):
        pointless_literal = 42
        self.assertEqual(0, give_one())
