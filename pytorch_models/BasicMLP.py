import torch.nn as nn

class BasicMLP(nn.Module):
    def __init__(self, input_size=8):
        super(BasicMLP, self).__init__()

        self.fc_layers = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.ReLU(),
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU()
        )

        self.output_layer = nn.Sequential(
            nn.Linear(256, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        fc_output = self.fc_layers(x)
        return self.output_layer(fc_output)
