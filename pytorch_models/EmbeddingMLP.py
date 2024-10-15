import torch.nn as nn
import torch

# TODO: Document properly
# TODO: add a struct/object for the input arguments?
# TODO: TorchLightning?
# TODO: Embedding sizes?

class EmbeddingMLP(nn.Module):
    def __init__(self, embedding_size_period, embedding_size_strength, embedding_size_shot_type, num_numeric_features=5, num_periods=8, num_strengths=17, num_shot_types=8):
        super(EmbeddingMLP, self).__init__()
        self.embedding_size_period = embedding_size_period
        self.embedding_size_strength = embedding_size_strength
        self.embedding_size_shot_type = embedding_size_shot_type
        
        self.num_periods = num_periods
        self.num_strengths = num_strengths
        self.num_shot_types = num_shot_types

        self.embedding_period = nn.Embedding(num_periods, embedding_size_period)
        self.embedding_strength = nn.Embedding(num_strengths, embedding_size_strength)
        self.embedding_type = nn.Embedding(num_shot_types, embedding_size_shot_type)

        self.fc_numeric = nn.Sequential(
            nn.Linear(num_numeric_features, 16),
            nn.ReLU()
        )

        self.fc_output = nn.Sequential(
            nn.Linear(embedding_size_period + embedding_size_strength + embedding_size_shot_type + 16, 1),
            nn.Sigmoid()  # Remove sigmoid if using BCEWithLogitsLoss
        )

    def forward(self, numeric_features, categorical_features):
        # Separate categorical variables from input.
        period_data = categorical_features[:, 0]
        strength_data = categorical_features[:, 1]
        shot_type_data = categorical_features[:, 2]

        # Embedding lookup for each categorical variable
        embedded_period = self.embedding_period(period_data)
        embedded_strength = self.embedding_strength(strength_data)
        embedded_type = self.embedding_type(shot_type_data)

        # Concatenate the embeddings
        concatenated_embeddings = torch.cat((embedded_period, embedded_strength, embedded_type), dim=1)

        # Pass numeric features through linear layer
        numeric_output = self.fc_numeric(numeric_features)

        # Concatenate the embeddings and numeric features
        concatenated_input = torch.cat((concatenated_embeddings, numeric_output), dim=1)

        # Pass through output layer
        output = self.fc_output(concatenated_input)

        return output