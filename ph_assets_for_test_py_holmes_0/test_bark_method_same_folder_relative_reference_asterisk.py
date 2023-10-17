import unittest
from bark_method import *


class TestBarking(unittest.TestCase):
    def test_bark(self):
        """Passes"""
        self.assertEqual("woof!", bark())
