"""A DNN architecture, loss function, optimizer, and choice of hyperparameters for the MNIST dataset.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import optim
from torch.autograd import variable
from datetime import datetime


class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()

        self.fc1 = nn.Linear(784, 300)
        self.fc2 = nn.Linear(300, 100)
        self.fc3 = nn.Linear(100, 10)  # Final fully connected layer that outputs our 10 labels

    def forward(self, x):
        if x.dim() == 4 and x.size()[1:4] == torch.Size([1, 28, 28]):
            # Reshape from [*, 1, 28, 28] to [*, 784]
            x = x.view(x.size()[0], x.size()[1] * x.size()[2] * x.size()[3])
        elif x.dim() == 2 and x.size() == torch.Size([28, 28]):
            # Reshape from [28, 28] to [1, 784]
            x = x.view(1, 784)
        else:
            raise ValueError(f"can't handle this shape of x: {x.size()}")
        # Forward pass
        x = self.fc1(x)
        x = F.relu(x)
        x = self.fc2(x)
        x = F.relu(x)
        x = self.fc3(x)
        x = F.relu(x)

        x = F.softmax(x, dim=1)  # Convert to probabilities
        return x


# Set hyperparameters
EPOCHS = 50
LR = 0.001
EPS = 1e-8
BATCH_SIZE = 100

# Select device
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(device)
print(f"cuda device 0 is {torch.cuda.get_device_name(0)}")

# Instantiate the model
model = Net().to(device)
print(model)

# Define a loss function
loss_func = nn.CrossEntropyLoss()

# Define an optimizer
optimizer = optim.Adam(model.parameters(), lr=LR, eps=EPS)
print(optimizer)

# Load the model
model.load_state_dict(torch.load('ph_models/mnist/modeldate2023-03-01,01_15_07.141405_bs100_lr0.001_eps1e-08_epochs20.pth'))