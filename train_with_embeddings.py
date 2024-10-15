import argparse
from datetime import datetime
import torch
from torch.utils.data import DataLoader
from sklearn.model_selection import train_test_split
import pandas as pd
import matplotlib.pyplot as plt
from imblearn.over_sampling import SMOTENC, SMOTE
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, f1_score, roc_auc_score
from pytorch_models.EmbeddingMLP import EmbeddingMLP
from pytorch_datasets.CategoricalDataset import CategoricalDataset


def train(n_epochs, optimizer, model, loss_fn, train_loader, test_loader, device, plot_file, save_file):
    print('Training...')
    model.to(device)
    model.train()
    losses_train = []

    for epoch in range(1, n_epochs + 1):
        loss_train = 0.0

        for numeric_features, categorical_features, labels in train_loader:
            # TODO: Send labels + features to device
            labels = labels.unsqueeze(1)
            outputs = model(numeric_features, categorical_features)
            loss = loss_fn(outputs, labels)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()


            loss_train += loss.item()

        losses_train += [loss_train / len(train_loader.dataset)]

        print('{} Epoch {}, Training loss {}'.format(
            datetime.now(), epoch, loss_train / len(train_loader.dataset)))

    
    if plot_file is not None:
        plt.figure(2, figsize=(12, 7))
        plt.clf()
        plt.plot(losses_train, label='train')
        plt.xlabel('Epoch')
        plt.ylabel('BCE Loss')
        plt.legend(loc=1)
        plt.savefig(plot_file)

    if save_file:
        torch.save(model.state_dict(), save_file)    

    # NOTE: If using BCEWithLogits, then need to take Sigmoid of output
    loss_test = 0.0
    model.eval()
    correct_predictions = 0
    with torch.no_grad():
        for numeric_features, categorical_features, labels in test_loader:
            # TODO: Send labels + features to device
            labels = labels.unsqueeze(1)
            outputs = model(numeric_features, categorical_features)
            # TODO: calculate metrics from outputs and labels
            loss = loss_fn(outputs, labels)
            loss_test += loss.item()
            correct_predictions += (torch.round(outputs) == labels).sum().item()

    print("\nscikit-learn Classification Report: \n", classification_report(y_pred=torch.round(outputs), y_true=labels, zero_division=0))
    print("\nConfusion Matrix: \n", confusion_matrix(y_pred=torch.round(outputs), y_true=labels))
    print("Test Loss: ", loss_test/len(test_loader.dataset))
    print("Test Accuracy: ", correct_predictions/len(test_loader.dataset))
    print("Test F1 Score: ", f1_score(y_pred=torch.round(outputs), y_true=labels, zero_division=0))
    # TODO: Cohen's Kappa?

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='NHL Expected Goals Training Function')
    parser.add_argument('-e', type=int, default=10, help='Number of epochs (default: 10)')
    parser.add_argument('-s', type=str, default="model_weights/MLP.Embeddings.pth",
                        help='PyTorch model state save location name')
    parser.add_argument('-p', type=str, default="plots/loss.MLP.Embeddings.png",
                        help='PyTorch loss graph save location name')

    arguments = parser.parse_args()
    
    df = pd.read_csv('data/2022_2023/2022_2023_cleaned.csv', index_col=False)

    resample = True

    # TODO: SMOTE FOR TRAIN SET ONLY?
    if resample == True: # Resample with categorical variables using SMOTENC, then fill X_numeric, X_categorical, and y tensors.
        X = df.loc[:, df.columns != "Event"]
        y = df.loc[:, df.columns == "Event"]
        # smote = SMOTENC(random_state=42, categorical_features=[0, 2, 3]) # Period, strength, type are at index 0, 2, 3 of X
        smote = SMOTE(random_state=42) # Period, strength, type are at index 0, 2, 3 of X
        X_resampled, y_resampled = smote.fit_resample(X, y)

        X_tensor_numeric = torch.tensor(X_resampled.loc[:, X_resampled.columns.isin(['Seconds_Elapsed', 'xC', 'yC', 'Score_For', 'Score_Against'])].values).to(torch.float32)
        X_tensor_categorical = torch.tensor(X_resampled.loc[:, X_resampled.columns.isin(['Period', 'Strength', 'Type'])].values).to(torch.int32)
        y_tensor = torch.tensor(y_resampled['Event'].values).to(torch.float32)

    else:  # Fill tensors without SMOTE
        X_tensor_numeric = torch.tensor(df.loc[:, df.columns.isin(['Seconds_Elapsed', 'xC', 'yC', 'Score_For', 'Score_Against'])].values).to(torch.float32)
        X_tensor_categorical = torch.tensor(df.loc[:, df.columns.isin(['Period', 'Strength', 'Type'])].values).to(torch.int32) # Categorical variables to ints
        # Shows max shows how many values are in each categorical feature. (Need +1)
        # cat_df = (df.loc[:, df.columns.isin(['Period', 'Strength', 'Type'])])
        # hold1 = cat_df.max()
        y_tensor = torch.tensor(df['Event'].values).to(torch.float32)


    scale = True
    # Scale numeric values to mean 0 and variance 1, then split data with stratified and shuffled train/test split.
    if scale:
        # TODO: Where should normalization be? Should it be applied separately for train and test?
        mean = X_tensor_numeric.mean(dim=0, keepdim=True)
        std = X_tensor_numeric.std(dim=0, keepdim=True)
        X_numeric_scaled = (X_tensor_numeric - mean)/std  # Mean 0 and Variance 1 for numeric values.
        """
        # Verifying mean and std in the tensor
        normalized_mean = X_numeric_scaled.mean(dim=0)
        normalized_std = X_numeric_scaled.std(dim=0)
        print("Normalized Mean: ", normalized_mean)
        print("Normalized Std: ", normalized_std)
        """
        
        X_numeric_train, X_numeric_test, X_categorical_train, X_categorical_test, y_train, y_test = train_test_split(
        X_numeric_scaled.numpy(), X_tensor_categorical.numpy(), y_tensor.numpy(), test_size=0.2, random_state=42, shuffle=True, stratify=y_tensor.numpy())
    
    else:
        X_numeric_train, X_numeric_test, X_categorical_train, X_categorical_test, y_train, y_test = train_test_split(
        X_tensor_numeric.numpy(), X_tensor_categorical.numpy(), y_tensor.numpy(), test_size=0.2, random_state=42, shuffle=True, stratify=y_tensor.numpy())

    
    # TODO: Implement Validation Split?
    
    # Convert NumPy arrays back to PyTorch tensors
    X_numeric_train = torch.tensor(X_numeric_train, dtype=torch.float32)
    X_numeric_test = torch.tensor(X_numeric_test, dtype=torch.float32)
    X_categorical_train = torch.tensor(X_categorical_train, dtype=torch.int32)
    X_categorical_test = torch.tensor(X_categorical_test, dtype=torch.int32)
    y_train = torch.tensor(y_train, dtype=torch.float32)
    y_test = torch.tensor(y_test, dtype=torch.float32)

    # Torch tensors into custom dataset, then into DataLoaders
    train_dataset = CategoricalDataset(X_numeric_train, X_categorical_train, y_train)
    test_dataset = CategoricalDataset(X_numeric_test, X_categorical_test, y_test)
    train_dataloader = DataLoader(dataset=train_dataset, batch_size=64, shuffle=True)  # Shuffles the data each epoch
    test_dataloader = DataLoader(dataset=test_dataset, batch_size=len(test_dataset))  # Can do all testing in one batch

    my_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    my_model = EmbeddingMLP(embedding_size_period=2, embedding_size_strength=6, embedding_size_shot_type=4)
    # TODO: Look into embedding sizes.
    my_optimizer = torch.optim.Adam(my_model.parameters(), lr=1e-5, weight_decay=1e-3)

    # pos_weight calucalatin for BCEWithLogitsLoss()
    # TODO: Should this weight be from train only? or can it include everything?
    # percent_shots = (y_tensor==1).sum()/y_tensor.sum()
    # pos_weight = (1-percent_shots)/percent_shots
    # print("Pos weight: ", pos_weight)
    # my_loss_fn = torch.nn.BCEWithLogitsLoss() # Binary Cross Entropy Loss

    my_loss_fn = torch.nn.BCELoss() # Binary Cross Entropy Loss

    train(n_epochs=arguments.e, optimizer=my_optimizer, model=my_model, loss_fn=my_loss_fn,
          train_loader=train_dataloader, test_loader=test_dataloader, device=my_device, plot_file=arguments.p, save_file=arguments.s)