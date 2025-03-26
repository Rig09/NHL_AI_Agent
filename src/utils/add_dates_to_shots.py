import pandas as pd

shots_data = r'C:\Users\agjri\Desktop\NHL_agent\NHL_AI_Agent\data\shots\shots_2015-2023.csv'
shots_2024 = r'C:\Users\agjri\Desktop\shots_2024.csv'

col_list = [
    'shotID', 'homeTeamCode', 'awayTeamCode', 'season', 'isPlayoffGame', 'game_id', 
    'homeTeamWon', 'id', 'time', 'period', 'team', 'xCord', 'yCord', 'location', 
    'event', 'goal', 'shotDistance', 'shotType', 'shotOnEmptyNet', 
    'goalieNameForShot', 'shooterPlayerId', 'shooterName', 'shooterLeftRight', 
    'xCordAdjusted', 'yCordAdjusted', 'isHomeTeam', 'awaySkatersOnIce', 'homeSkatersOnIce', 
    'xGoal', 'homeTeamGoals', 'awayTeamGoals', 'shotAngle', 
    'playerPositionThatDidEvent', 'shootingTeamForwardsOnIce', 'shootingTeamDefencemenOnIce', 
    'defendingTeamForwardsOnIce', 'defendingTeamDefencemenOnIce'
]

# Read CSV with only required columns
shots_df = pd.read_csv(shots_data, usecols=col_list)
shots_2024 = pd.read_csv(shots_2024, usecols=col_list)

# Combine the two shot dataframes
shots_df = pd.concat([shots_df, shots_2024], ignore_index=True)

# Initialize current_game_id as None before starting the loop
current_game_id = None
# Convert 'season' to numeric (to handle any potential issues with data types)
shots_df['season'] = pd.to_numeric(shots_df['season'], errors='coerce')
shots_df['season'] = shots_df['season'].astype(int)

# Read the game data CSV (from the API with game dates)
game_data_df = pd.read_csv('nhl_game_data.csv')

# Sort shots dataframe by season and game_id
shots_df = shots_df.sort_values(by=['season', 'game_id'])

# Initialize the 'date' column in the shots dataframe
shots_df['date'] = None

# Create an index to keep track of which row to assign a date
shot_index = 0

for index, row in game_data_df.iterrows():
    date = row['Date']  # The date for this set of games
    num_games = row['Number of Game IDs']  # Number of games on this date

    # Skip if no games for this date (num_games == 0)
    if num_games == 0:
        continue

    # Get the unique game_ids that still need to have a date assigned
    game_ids_to_assign = shots_df[shots_df['date'].isna()]['game_id'].unique()

    # For each of the first `num_games` game_ids, assign the date
    for i in range(min(num_games, len(game_ids_to_assign))):
        game_id = game_ids_to_assign[i]
        
        # Assign the date to all shots that belong to this game_id
        shots_df.loc[shots_df['game_id'] == game_id, 'date'] = date

# After processing, check if the date column is populated correctly
print(shots_df.head())  # Check the first few rows to verify

# Save the modified shots dataframe to a new CSV (if needed)
shots_df.to_csv('updated_shots_with_dates.csv', index=False)
