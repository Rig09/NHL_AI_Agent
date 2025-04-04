import requests
import pandas as pd


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


def time_to_seconds(time_str):
    if pd.isnull(time_str):
        return 0
    minutes, seconds = map(int, time_str.split(':'))
    return minutes * 60 + seconds

def fetch_shifts(nhl_game_id):
    url = f"https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId={nhl_game_id}"
    try:
        print(f"Fetching shitfs for {nhl_game_id}")
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get('data', [])
    except requests.RequestException as e:
        print(f"Error fetching shifts for game {nhl_game_id}: {e}")
        return []

def get_players_on_ice(shifts_data, shot_time, shot_period, team_code):
    """Finds the players on the ice at the given shot time and period, excluding goalies."""
    players_on_ice = {'shooting_team': [], 'opposing_team': []}
    
    for shift in shifts_data:
        start_time = time_to_seconds(shift['startTime'])
        end_time = time_to_seconds(shift['endTime'])
        shift_length = end_time - start_time
        
        if shift['period'] == shot_period and start_time <= shot_time < end_time and shift_length <= 300:
            player_name = f"{shift['firstName']} {shift['lastName']}"
            if shift['teamAbbrev'] == team_code:
                players_on_ice['shooting_team'].append(player_name)
            else:
                players_on_ice['opposing_team'].append(player_name)
    
    return ', '.join(players_on_ice['shooting_team']), ', '.join(players_on_ice['opposing_team'])

def process_shots(shots_df):
    shifts_data_cache = {}
    shots_df['shooting_team_players'] = ''
    shots_df['opposing_team_players'] = ''

    for idx, row in shots_df.iterrows():
        nhl_game_id = row['nhl_game_id']
        team_code = row['teamCode']
        shot_time_seconds = row['time']
        shot_period = row['period']

        if shot_period > 1:
            shot_time_seconds -= (shot_period - 1) * 1200
      
        if nhl_game_id not in shifts_data_cache:
            shifts_data_cache[nhl_game_id] = fetch_shifts(nhl_game_id)
        shifts_data = shifts_data_cache[nhl_game_id]

        shooting_team_players, opposing_team_players = get_players_on_ice(shifts_data, shot_time_seconds, shot_period, team_code)
        shots_df.at[idx, 'shooting_team_players'] = shooting_team_players
        shots_df.at[idx, 'opposing_team_players'] = opposing_team_players

    return shots_df
# Example usage

shots_2024 = r'C:\Users\agjri\Desktop\shots_2024.csv'

shots_df = pd.read_csv(shots_2024, usecols=col_list, index_col=None)

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


shots_df = process_shots(shots_df)
print(shots_df.head(5))

shots_df.to_csv('shots2024_with_line_data.csv', index=False)
