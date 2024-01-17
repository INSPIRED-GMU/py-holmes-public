"""Tests of the DNN defined in dnn_0.py"""


import unittest
from dnn_0 import DnnModel
import torch
import torch.nn as nn
from torch import optim

class TestDnn0WithHandmadeInput(unittest.TestCase):
    def test_0(self):
        """Instantiates the DNN, runs it on an input, and checks for maximum likelihood class in the response."""
        model = DnnModel()
        optimizer = optim.Adam(model.parameters(), lr=0.001, eps=1e-8)
        loss_fn = nn.CrossEntropyLoss()
        xmin = 0
        xmax = 255
        adjustment_rate = 8
        indices_to_protect_from_fuzzing = [(0, 2)]
        x = torch.tensor([[0, 1, 2, 3, 4,
                           5, 6, 7,
                           8,
                           9, 10, 11,
                           12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]], dtype=torch.float32)
        output = model(x)
        label = torch.Tensor([[1, 0, 0, 0, 0, 0, 0, 0, 0, 0]])
        self.assertTrue(label.argmax().item() == output.argmax().item())
