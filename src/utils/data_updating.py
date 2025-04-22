import mysql.connector
import pandas as pd
import os
import requests
import zipfile
from io import BytesIO
from sqlalchemy import create_engine
from dotenv import load_dotenv
import io
from datetime import datetime, date

# Load environment variables from .env file
load_dotenv()

# Retrieve MySQL connection details from environment variables
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

# Connect to MySQL
conn = mysql.connector.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD
)
cursor = conn.cursor()

def get_game_type_or_exit():
    today = datetime.today()
    year = today.year
    
    april_20 = datetime(year, 4, 20)
    july_1 = datetime(year, 7, 1)
    sept_1 = datetime(year, 9, 1)

    if april_20 <= today < july_1:
        return "playoffs"
    elif july_1 <= today < sept_1:
        print("Offseason: The program will not run during this time.")
        exit(0)
    else:
        return "regular"
    
game_type = get_game_type_or_exit()
# Create database if it doesn't exist
#cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE};")
cursor.execute(f"USE {MYSQL_DATABASE};")

# Use SQLAlchemy for Pandas `.to_sql()` with MySQL
engine = create_engine(f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}")

# Define the URLs for the CSV files
urls = {
    f'skaterstats_{game_type}_2024': f"https://moneypuck.com/moneypuck/playerData/seasonSummary/2024/{game_type}/skaters.csv",
    f'goaliestats_{game_type}_2024': f"https://moneypuck.com/moneypuck/playerData/seasonSummary/2024/{game_type}/goalies.csv",
    f'linestats_{game_type}_2024': f"https://moneypuck.com/moneypuck/playerData/seasonSummary/2024/{game_type}/lines.csv",
    f'teamstats_{game_type}_2024': f"https://moneypuck.com/moneypuck/playerData/seasonSummary/2024/{game_type}/teams.csv",
    f'shots_data': f"https://peter-tanner.com/moneypuck/downloads/shots_2024.zip",  # New shots data URL
    f'game_logs': f"https://moneypuck.com/moneypuck/playerData/careers/gameByGame/all_teams.csv"
}

required_columns = [
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


def fetch_game_date(nhl_game_id):
    url = f"https://api-web.nhle.com/v1/gamecenter/{nhl_game_id}/landing"
    try:
        response = requests.get(url)
        response.raise_for_status()
        game_data = response.json()
        return game_data.get('gameDate', None)
    except requests.RequestException as e:
        print(f"Error fetching data for {nhl_game_id}: {e}")
        return None

def add_game_dates(df):
    # Extract unique game IDs
    unique_game_ids = df['nhl_game_id'].unique()
    game_date_map = {game_id: fetch_game_date(game_id) for game_id in unique_game_ids}
    
    # Map game dates back to the original dataframe
    df['gameDate'] = df['nhl_game_id'].map(game_date_map)
    return df


def download_csv(url):
    response = requests.get(url)
    if response.status_code == 200:
        return pd.read_csv(BytesIO(response.content))  # Read directly into a DataFrame from memory
    else:
        print(f"⚠ Failed to download CSV from {url}")
        return None

def download_and_extract_zip(url):
    # Download the zip file content
    response = requests.get(url)
    if response.status_code == 200:
        # Extract the zip file in memory using BytesIO
        with zipfile.ZipFile(BytesIO(response.content)) as zip_ref:
            zip_ref.extractall("/tmp")  # Extract to a temporary directory
            extracted_files = zip_ref.namelist()  # List of extracted files
            return extracted_files
    else:
        print(f"⚠ Failed to download ZIP from {url}")
        return None

def get_existing_data(table_name):
    try:
        query = f"SELECT * FROM {table_name} LIMIT 1;"
        return pd.read_sql(query, engine)
    except Exception as e:
        if "doesn't exist" in str(e).lower() or "no such table" in str(e).lower():
            print(f"Table '{table_name}' does not exist yet.")
            return pd.DataFrame()
        else:
            raise Exception(f"Unknown error querying table '{table_name}': {e}")

def update_table(df, table_name):
    # Retrieve existing data from the table
    existing_data = get_existing_data(table_name)
    
    # Compare existing data with new data and find rows that need to be inserted
    if existing_data.empty:
        print(f"Table '{table_name}' is empty. Inserting all data.")
        df.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=5000, method="multi")
    else:
        print(f"Updating '{table_name}' with new data...")
        df = df.drop(columns=['_merge'], errors='ignore')
        existing_data = existing_data.drop(columns=['_merge'], errors='ignore')

        # Perform a left join to identify records that need to be inserted/updated
        merged = pd.merge(df, existing_data, how="left", indicator=True)
        new_records = merged[merged['_merge'] == 'left_only'].drop('_merge', axis=1)
    

        new_records = new_records.drop(columns=['_merge'], errors='ignore')
        #Insert the new records into the table
        if not new_records.empty:
            if table_name == "game_logs":
                new_records.to_sql(table_name, engine, if_exists="append", index=False, chunksize=5000, method="multi")
            else:
                df.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=5000, method="multi")
        else:
            print(f"No new records to add for '{table_name}'.")

            

def process_csv(url, table_name):
    # Download the CSV file into memory
    df = download_csv(url)
    
    if df is not None:
        # Update the database with the new data
        update_table(df, table_name)

def process_shots_data(zip_url, table_name):
    # Download the ZIP file from the URL
    response = requests.get(zip_url)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
        # Extract the CSV file from the ZIP
        zip_ref.extractall("/tmp")

    # Get the CSV filename in the extracted directory (assuming only one CSV file in ZIP)
    csv_filename = [f for f in os.listdir("/tmp") if f.endswith('.csv')][0]
    csv_file_path = os.path.join("/tmp", csv_filename)
    
    if os.path.exists(csv_file_path):
        print(f"Processing {csv_file_path}...")
        
        # Read the CSV into a DataFrame
        df = pd.read_csv(csv_file_path, encoding="utf-8", low_memory=False)
        
        # Keep only the required columns
        df = df[required_columns]

        df['nhl_game_id'] = df['season'].astype(str) + df['game_id'].astype(str).str.zfill(6)
        df['nhl_game_id'] = df['nhl_game_id'].astype(int)
        
        existing_data = get_existing_data(table_name)

        df = df.drop(columns=['_merge'], errors='ignore')
        existing_data = existing_data.drop(columns=['_merge'], errors='ignore')

        merged = pd.merge(df, existing_data, how="left", indicator=True)
        new_records = merged[merged['_merge'] == 'left_only'].drop('_merge', axis=1)

        new_records = process_shots(new_records)
        new_records = add_game_dates(new_records)
        # Write to MySQL (replace table each time)
        new_records.to_sql(table_name, engine, if_exists="append", index=False, chunksize=5000, method="multi")
        print(f"✔ Data saved in table '{table_name}'")
        
        # Clean up the extracted files
        os.remove(csv_file_path)
    else:
        print(f"⚠ File not found: {csv_file_path}")

def process_lines_csv(url, table_name):
    # Download the CSV file into memory
    df = download_csv(url)
    
    if df is not None:
        # Separate into lines and pairs
        df_lines = df[df["position"] == "line"]  # Filter rows for lines
        df_pairs = df[df["position"] == "pairing"]  # Filter rows for pairings
        
        # Now, handle lines (just like the other DataFrames)
        update_table(df_lines, f"{table_name}")  # Update the 'lines' table
        
        # Handle pairs (just like the other DataFrames)
        update_table(df_pairs, f"pairstats_{game_type}_2024")  # Update the 'pairs' table
        
        print(f"✔ Lines and pairs data from {table_name} processed and added to database.")


# Modify the main processing loop to handle the linestats_{game_type}_2024 URL differently
for table_name, url in urls.items():
    if f"linestats_{game_type}_2024" in table_name:
        process_lines_csv(url, table_name)
    elif "shots_data" in table_name:  # Process the ZIP for shots_data
        process_shots_data(url, table_name)
    else:
        process_csv(url, table_name)

print("All specified tables have been updated in the database.")