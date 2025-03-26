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
    'defendingTeamForwardsOnIce', 'defendingTeamDefencemenOnIce', 'teamCode'
]

# def assign_season(date):
#     year = date.year
#     if pd.Timestamp(f'{year}-09-01').date() <= date <= pd.Timestamp(f'{year+1}-07-01').date():
#         return year
#     elif pd.Timestamp(f'{year-1}-09-01').date() <= date <= pd.Timestamp(f'{year}-07-01').date():
#         return year - 1
#     return None  # In case the date doesn't fit the range

# Read CSV with only required columns
shots_df = pd.read_csv(shots_data, usecols=col_list, index_col=None)
shots_2024 = pd.read_csv(shots_2024, usecols=col_list, index_col=None)

# Combine the two shot dataframes
shots_df = pd.concat([shots_df, shots_2024], ignore_index=True)

#shots_df.to_csv('shots_before_dates.csv', index=False)

# Create nhl_game_id column
shots_df['nhl_game_id'] = shots_df['season'].astype(str) + shots_df['game_id'].astype(str).str.zfill(6)


game_data = pd.read_csv(r'C:\Users\agjri\Desktop\NHL_Chatbot\NHL_AI_Agent\all_teams.csv', index_col=None)

game_data = game_data[game_data['season'] >= 2015]

game_data = game_data[game_data['home_or_away'] == 'HOME']

# Ensure that game data has unique gameId values
game_data = game_data.drop_duplicates(subset='gameId', keep='first')

#game_data.to_csv('sample_game_data.csv', index=False)

# Convert nhl_game_id and gameId to integers after creating them as strings
shots_df['nhl_game_id'] = shots_df['nhl_game_id'].astype(int)
game_data['gameId'] = game_data['gameId'].astype(int)

# Perform a left join to add date from game_data to shots_df
shots_df = pd.merge(shots_df, game_data[['gameId', 'gameDate']], 
                     left_on='nhl_game_id', right_on='gameId', 
                     how='left')

shots_df = shots_df.reset_index(drop=True)
# Drop the extra gameID column
shots_df.drop(columns='gameId', inplace=True)


if shots_df['gameDate'].isnull().sum() > 0:
    print("Warning: Some shots could not be matched to a game date.")
else:
    print("All shots matched successfully.")

shots_df['gameDate'] = pd.to_datetime(shots_df['gameDate'], format='%Y%m%d').dt.strftime('%Y-%m-%d')

# print("Before dropping duplicates:", shots_df.duplicated(subset=['shotID', 'season']).sum())
shots_df = shots_df.drop_duplicates(subset=['shotID', 'nhl_game_id'])
# print("After dropping duplicates:", shots_df.duplicated(subset=['shotID', 'season']).sum())

print(shots_df.head(5))
print(shots_df[shots_df['shotID'] == 0].head(5))
shots_csv_path = 'shots_with_dates.csv'

shots_df.to_csv(shots_csv_path, index=False)

final_df = pd.read_csv(shots_csv_path, index_col=None)
print(final_df.head(5))
final_df = final_df.drop_duplicates(subset=['shotID', 'nhl_game_id'])
print(final_df.head(5))

final_df.to_csv('final_shots.csv', index=False)