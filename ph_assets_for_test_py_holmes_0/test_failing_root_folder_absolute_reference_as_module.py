"""For use by test_py_holmes.TestWhenOriginalFileInDeeperFolder"""


import unittest
import failing_root_folder


class TestClass(unittest.TestCase):
    def test_method(self):
        pointless_literal = 42
        self.assertEqual(0, failing_root_folder.give_one())
