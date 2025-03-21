import mysql.connector
import pandas as pd
import os
import requests
import zipfile
from io import BytesIO
from sqlalchemy import create_engine
from dotenv import load_dotenv
import io

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

# Create database if it doesn't exist
#cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE};")
cursor.execute(f"USE {MYSQL_DATABASE};")

# Use SQLAlchemy for Pandas `.to_sql()` with MySQL
engine = create_engine(f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}")

# Define the URLs for the CSV files
urls = {
    'skaterstats_regular_2024': "https://moneypuck.com/moneypuck/playerData/seasonSummary/2024/regular/skaters.csv",
    'goaliestats_regular_2024': "https://moneypuck.com/moneypuck/playerData/seasonSummary/2024/regular/goalies.csv",
    'linestats_regular_2024': "https://moneypuck.com/moneypuck/playerData/seasonSummary/2024/regular/lines.csv",
    'teamstats_regular_2024': "https://moneypuck.com/moneypuck/playerData/seasonSummary/2024/regular/teams.csv",
    'shots_data': "https://peter-tanner.com/moneypuck/downloads/shots_2024.zip"  # New shots data URL
}

required_columns = [
    'shotID', 'homeTeamCode', 'awayTeamCode', 'season', 'isPlayoffGame', 'game_id',
    'homeTeamWon', 'id', 'time', 'period', 'team', 'xCord', 'yCord', 'location',
    'event', 'goal', 'shotDistance', 'shotType', 'shotOnEmptyNet',
    'goalieNameForShot', 'shooterPlayerId', 'shooterName', 'shooterLeftRight',
    'xCordAdjusted', 'yCordAdjusted', 'isHomeTeam', 'awaySkatersOnIce', 'homeSkatersOnIce',
    'xGoal', 'homeTeamGoals', 'awayTeamGoals', 'shotAngle',
    'playerPositionThatDidEvent', 'shootingTeamForwardsOnIce', 'shootingTeamDefencemenOnIce',
    'defendingTeamForwardsOnIce', 'defendingTeamDefencemenOnIce'
]


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
    # Query the existing data from the table
    query = f"SELECT * FROM {table_name};"
    return pd.read_sql(query, engine)

def update_table(df, table_name):
    # Retrieve existing data from the table
    existing_data = get_existing_data(table_name)
    
    # Compare existing data with new data and find rows that need to be inserted
    if existing_data.empty:
        print(f"Table '{table_name}' is empty. Inserting all data.")
        df.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=5000, method="multi")
    else:
        print(f"Updating '{table_name}' with new data...")

        # Perform a left join to identify records that need to be inserted/updated
        merged = pd.merge(df, existing_data, how="left", indicator=True)
        new_records = merged[merged['_merge'] == 'left_only'].drop('_merge', axis=1)
        
        # Insert the new records into the table
        if not new_records.empty:
            new_records.to_sql(table_name, engine, if_exists="append", index=False, chunksize=5000, method="multi")
            print(f"✔ {len(new_records)} new records added to '{table_name}'.")
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

        # Write to MySQL (replace table each time)
        df.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=5000, method="multi")
        print(f"✔ Data saved in table '{table_name}'")
        
        # Clean up the extracted files
        os.remove(csv_file_path)
    else:
        print(f"⚠ File not found: {csv_file_path}")

# Process each CSV and upload to MySQL
for table_name, url in urls.items():
    if "shots_data" in table_name:  # Process the ZIP for shots_data
        process_shots_data(url, table_name)
    else:
        process_csv(url, table_name)

print("All specified tables have been updated in the database.")

# Close connection
cursor.close()
conn.close()
