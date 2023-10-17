"""Tests of the DNN defined in dnn_0.py"""


import unittest
from dnn_0 import DnnModel

import torch


class TestDnn0WithRandomInput(unittest.TestCase):
    def test_0(self):
        """Instantiates the DNN, runs it on an input, and then always fails."""
        torch.manual_seed(0)
        model = DnnModel()
        x = torch.randn(1, 25)
        output = model(x)
        self.assertTrue(False)
