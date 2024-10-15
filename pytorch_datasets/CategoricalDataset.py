from torch.utils.data import Dataset

class CategoricalDataset(Dataset):
    def __init__(self, X_numeric, X_categorical, y):
        self.X_numeric = X_numeric
        self.X_categorical = X_categorical
        self.y = y
    
    def __len__(self):
        return len(self.y)
    
    def __getitem__(self, idx):
        return self.X_numeric[idx], self.X_categorical[idx], self.y[idx]
