"""For use by test_py_holmes.py"""


import unittest
from ph_assets_for_test_py_holmes_0.time_staller import stall_for_time


class TestStallingForTime(unittest.TestCase):
    def test_stall_for_time_short(self):
        """Run stall_for_time for a short period and ensure that it returns 5 (it won't).
        """
        pointless_var = 1.1     # So that py-holmes bothers to fuzz this test at all
        self.assertEqual(5, stall_for_time())

