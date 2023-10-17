"""For use by
test_py_holmes.TestWhenOriginalFileInDeeperFolder.test_file_creation_in_correct_folder_for_original_file_in_deeper_folder
"""


import unittest
from ph_assets_for_test_py_holmes_0.dummy_file_creator import create_dummy_file


class TestClass(unittest.TestCase):
    def test_method(self):
        """Failing test method that calls a function that creates a dummy file."""
        create_dummy_file()
        pointless_literal = 42
        self.assertEqual(0, 1)