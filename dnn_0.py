"""Class for a very small DNN."""

from __future__ import print_function
from __future__ import division

import torch
import torch.nn as nn
import torch.nn.functional as F


torch.manual_seed(17)    # Wren added this per the recommendation here: https://pytorch.org/vision/stable/transforms.html


class DnnModel(nn.Module):
    def __init__(self):
        super(DnnModel, self).__init__()
        self.cl1 = nn.Linear(25, 60)
        self.cl2 = nn.Linear(60, 16)
        self.fc1 = nn.Linear(16, 120)
        self.fc2 = nn.Linear(120, 84)
        self.fc3 = nn.Linear(84, 10)

    def forward(self, x):
        x = F.relu(self.cl1(x))
        x = F.relu(self.cl2(x))
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.log_softmax(self.fc3(x), dim=1)
        return x


