import unittest
from ph_assets_for_test_py_holmes_0.bark_method import bark


class TestBarking(unittest.TestCase):
    def test_bark(self):
        """Passes"""
        self.assertEqual("woof!", bark())
