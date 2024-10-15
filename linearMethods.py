import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge, Lasso
from sklearn.ensemble import StackingRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error

# Load data from CSV file
NHL_data = pd.read_csv('Tempcleaned.csv')

# Create a temporary DataFrame copy for manipulation
temp_df = NHL_data.copy()

# Define columns to drop for prediction
columns_to_drop = ['p1_name','evPlayer1', 'evPlayer2','evPlayer3', 'evPlayer4','evPlayer5', 'evPlayer6', 'evGoalie', 
                   'agPlayer1', 'agPlayer2','agPlayer3', 'agPlayer4', 'agPlayer5', 'agPlayer6', 'agGoalie']

NHL_data.drop(columns=columns_to_drop, inplace=True)

# Split data into features (X) and target (y)
X = NHL_data.drop(columns=['Event'])
y = NHL_data['Event']

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)


# Define base estimators for StackingRegressor
estimators = [
    ('xgb', XGBRegressor(objective='reg:squarederror', random_state=42)),
    ('ridge', Ridge(alpha=3)),
    ('lasso', Lasso(alpha=0.5)),
    #('rf', RandomForestRegressor(n_estimators=100, random_state=42))
]

# Create and train the StackingRegressor
reg = StackingRegressor(estimators=estimators, verbose=1)
reg.fit(X_train, y_train)

# Make predictions on the test set
reg_predictions = reg.predict(X_test)

# Calculate root mean squared error (RMSE) on the test set
reg_rmse = mean_squared_error(y_test, reg_predictions, squared=False)
print("Stacked RMSE:", reg_rmse)

# Assign predictions to a new column 'Prediction' in temp_df
NHL_data['Prediction'] = reg.predict(X)
NHL_data.to_csv('removedPlayers.csv', index=False)

NHL_data[columns_to_drop] = temp_df[columns_to_drop]

# Export the updated DataFrame (temp_df) with predictions to a CSV file

NHL_data.to_csv('PredictedVals.csv', index=False)
