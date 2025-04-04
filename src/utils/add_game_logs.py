import mysql.connector
import pandas as pd
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables from .env file
print("running the file")
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

def process_csv(file_path, table_name, season=None, is_playoff=None):
    if os.path.exists(file_path):
        print(f"Processing {file_path}...")

        df = pd.read_csv(file_path, encoding="utf-8", low_memory=False)
        if 'gameDate' in df.columns:
            df['gameDate'] = pd.to_datetime(df['gameDate'], errors='coerce').dt.date
        #df["season"] = season
        #df["is_playoff"] = is_playoff

        # Write to MySQL (replace table each time)
        df.to_sql(table_name, engine, if_exists="replace", index=False, chunksize=5000, method="multi")
        print(f"✔ Data saved in table '{table_name}'")
    else:
        print(f"⚠ File not found: {file_path}")


cursor = conn.cursor()
print("connected")
# Create database if it doesn't exist
cursor.execute(f"USE {MYSQL_DATABASE};")
print("using db")
# Define seasons to process

print("got to engine create")
engine = create_engine(f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}")
print("created")


game_logs_path = r'C:\Users\agjri\Desktop\NHL_Chatbot\NHL_AI_Agent\all_teams.csv'

process_csv(game_logs_path, "game_logs")

cursor.execute("SHOW COLUMNS FROM game_logs;")
columns = cursor.fetchall()

print("\nColumns in 'game_logs' table:")
for column in columns:
    print(column[0])

# Close connection
cursor.close()
conn.close()
print(f"All available seasons have been processed into MySQL database '{MYSQL_DATABASE}'")


