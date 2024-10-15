import argparse
from datetime import datetime
import torch
from torch.utils.data import TensorDataset, random_split, DataLoader
import pandas as pd
import matplotlib.pyplot as plt
# import numpy as np
from sklearn.metrics import classification_report
from pytorch_models.BasicMLP import BasicMLP

# Features:
# https://moneypuck.com/about.htm#shotModel
    # Time since last event
    # Empty Net?
    # Last event type?
    # Last event location?
    # Speed from previous event?


# TODO: Future changes:
    # Batching?
    # 
    # 
    # LR Scheduling
    # Vadliation subset while training
    # Send the data + model using a torch device
    # Model checkpoints
    # Move test code to separate file
    # Regularization techniques, overfitting (only makes predictions as 1)
    # Goals for/against. Have 11 unique values in each home/away. Should be only 11 in one side (since 10 goals were only scored by one team in 2022-23) 
        # (https://www.statmuse.com/nhl/ask?q=highest+scoring+nhl+game+by+team+2022-23)
    # Encode strength as difference between 2 teams? ()
    # Torch Lightning model structure?


def train(n_epochs, optimizer, model, loss_fn, train_loader, test_loader, device, plot_file, save_file):
    print('Training...')
    model.train()
    losses_train = []

    for epoch in range(1, n_epochs + 1):
        loss_train = 0.0

        for features, labels in train_loader:
            labels = labels.unsqueeze(1)
            outputs = model(features)
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

    # TODO: Move Test Code
    loss_test = 0.0
    model.eval()
    correct_predictions = 0
    with torch.no_grad():
        for features, labels in test_loader:  # This loop only has one iteration since batch size is the full test set
            labels = labels.unsqueeze(1)
            outputs = model(features)
            # TODO: calculate metrics from outputs and labels
            loss = loss_fn(outputs, labels)
            loss_test += loss.item()
            # Rounding 0.5 up, ceiling
            correct_predictions += (torch.ceil(outputs) == labels).sum().item()
        
        print(classification_report(y_pred=torch.ceil(outputs), y_true=labels, zero_division=0))  # sklearn function to print results on each class
    
    # Code to export y_test and y_true
    # test_predictions = pd.DataFrame(list(zip(features, outputs, labels)), columns=['Features', 'Outputs', 'Labels'])
    # test_predictions.to_csv("test_predictions.csv", index=False)

    print("Test Loss: ", (loss_test/len(test_loader.dataset)))
    print("Test Accuracy: ", (correct_predictions/len(test_loader.dataset)))
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Lab 1 ELEC475 Training Function')
    parser.add_argument('-e', type=int, default=10, help='Number of epochs (default: 10)')
    parser.add_argument('-s', type=str, default="model_weights/MLP.First.pth",
                        help='PyTorch model state save location name')
    parser.add_argument('-p', type=str, default="plots/loss.MLP.First.png",
                        help='PyTorch loss graph save location name')

    arguments = parser.parse_args()
    
    df = pd.read_csv('data/2022_2023/2022_2023_cleaned.csv', index_col=False)
    X_tensor = torch.tensor(df.loc[:, df.columns != 'Event'].values).to(torch.float32)
    y_tensor = torch.tensor(df['Event'].values).to(torch.float32)
    
    full_tensor = TensorDataset(X_tensor, y_tensor)
    
    train_dataset, test_dataset = random_split(full_tensor, [0.8, 0.2], generator=torch.Generator().manual_seed(42))
    
    train_dataloader = DataLoader(dataset=train_dataset, batch_size=128, shuffle=True)  # Shuffles the data each epoch
    test_dataloader = DataLoader(dataset=test_dataset, batch_size=len(test_dataset))  # Can do all testing in one batch

    my_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    my_model = BasicMLP()

    my_optimizer = torch.optim.Adam(my_model.parameters())

    my_loss_fn = torch.nn.BCELoss() # Binary Cross Entropy Loss

    train(n_epochs=arguments.e, optimizer=my_optimizer, model=my_model, loss_fn=my_loss_fn,
          train_loader=train_dataloader, test_loader=test_dataloader, device=my_device, plot_file=arguments.p, save_file=arguments.s)
