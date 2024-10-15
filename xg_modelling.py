import pandas as pd
from sklearn.model_selection import train_test_split
# from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge, Lasso
from sklearn.ensemble import StackingRegressor
from sklearn.metrics import root_mean_squared_error
from xgboost import XGBRegressor
import shap


# Load data from CSV file
XG_data = pd.read_csv('data/xg_shot_input_2015-2023.csv')

# NOTE: Possibly convert to notebook for segmented code running?
print("XG Data CSV loaded")

# Split data into features (X) and target (y)
y = XG_data['isGoal']
X = XG_data.drop(columns=['isGoal'])

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=True)

print("Data splitting complete")

# Define base estimators for StackingRegressor
estimators = [
    ('xgb', XGBRegressor(objective='reg:squarederror', random_state=42)),
    ('ridge', Ridge(alpha=3)),
    ('lasso', Lasso(alpha=0.5)),
    #('rf', RandomForestRegressor(n_estimators=100, random_state=42))
]
# TODO: Model checkpoints?

# Create and train the StackingRegressor
reg = StackingRegressor(estimators=estimators, verbose=1)
reg.fit(X_train, y_train)

# Make predictions on the test set
reg_predictions = reg.predict(X_test)

# Calculate root mean squared error (RMSE) on the test set
reg_rmse = root_mean_squared_error(y_test, reg_predictions)
print("Stacked RMSE:", reg_rmse)

# TODO: Plotting of results
# TODO: Plotting of feature importance with SHAP: https://shap.readthedocs.io/en/latest/