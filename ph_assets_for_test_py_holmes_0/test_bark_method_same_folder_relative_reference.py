import unittest
from bark_method import bark


class TestBarking(unittest.TestCase):
    def test_bark(self):
        """Passes"""
        self.assertEqual("woof!", bark())
