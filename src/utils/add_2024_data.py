import mysql.connector
import pandas as pd
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

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
cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE};")
cursor.execute(f"USE {MYSQL_DATABASE};")

# Use SQLAlchemy for Pandas `.to_sql()` with MySQL
engine = create_engine(f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}")

def process_csv(file_path, table_name):
    if os.path.exists(file_path):
        print(f"Processing {file_path}...")
        
        df = pd.read_csv(file_path, encoding="utf-8", low_memory=False)
        
        # Write to MySQL (replace table each time)
        df.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=5000, method="multi")
        print(f"✔ Data saved in table '{table_name}'")
    else:
        print(f"⚠ File not found: {file_path}")

# Define your CSV file paths (update the filenames as needed)
downloads_path = os.path.expanduser('~/Downloads')
csv_files = {
    'skaterstats_regular_2024': os.path.join(downloads_path, 'skaters_2024_regular.csv'),
    'goaliestats_regular_2024': os.path.join(downloads_path, 'goalies_2024_regular.csv'),
    'linestats_regular_2024': os.path.join(downloads_path, 'lines_2024_regular.csv'),
    'teamstats_regular_2024': os.path.join(downloads_path, 'teams_2024_regular.csv'),
}

# Process each CSV and upload to MySQL
for table_name, file_path in csv_files.items():
    process_csv(file_path, table_name)

print("All specified tables have been added to the database.")

# Close connection
cursor.close()
conn.close()
