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
cursor = conn.cursor()
print("connected")
# Create database if it doesn't exist
cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE};")
cursor.execute(f"USE {MYSQL_DATABASE};")
print("using db")
# Define seasons to process
seasons = range(2015, 2024)  # Adjust range as needed

# # Get all table names
# cursor.execute("SHOW TABLES;")
# tables = cursor.fetchall()

# # Clean the table name (remove unwanted characters like file paths)
# for table in tables:
#     table_name = table[0]
    
#     # Ensure table_name is a valid identifier (e.g., remove potential path components)
#     table_name = table_name.strip().split("\\")[-1]  # This strips potential path components

#     cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`;")  # Ensure table names are quoted to avoid conflicts with reserved words
#     print(f"✔ Dropped table '{table_name}'")

# Use SQLAlchemy for Pandas `.to_sql()` with MySQL
print("got to engine create")
engine = create_engine(f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}")
print("created")
# Function to process CSV files and save to MySQL
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

# # Process skaters, goalies, lines, and pairs data
# for season in seasons:
#     for is_playoff, game_type in [(0, "regular"), (1, "playoffs")]:
#         # Skaters
#         process_csv(f"data/skaters/{season}/skaters_{game_type}_{season}.csv", f"SkaterStats_{game_type}_{season}", season, is_playoff)
        
#         # Goalies
#         process_csv(f"data/goalies/{season}/goalies_{game_type}_{season}.csv", f"GoalieStats_{game_type}_{season}", season, is_playoff)
        
#         # Lines and Pairs (from the same CSV, separated by 'position')
#         lines_csv = f"data/pairings/{season}/pairings_{game_type}_{season}.csv"
#         if os.path.exists(lines_csv):
#             print(f"Processing {lines_csv}...")
#             df = pd.read_csv(lines_csv, encoding="utf-8", low_memory=False)
#             df["season"] = season
#             df["is_playoff"] = is_playoff
            
#             # Separate into lines and pairs
#             df_lines = df[df["position"] == "line"]
#             df_pairs = df[df["position"] == "pairing"]
            
#             if not df_lines.empty:
#                 df_lines.to_sql(f"LineStats_{game_type}_{season}", engine, if_exists="replace", index=False, chunksize=5000, method="multi")
#                 print(f"✔ LineStats_{game_type}_{season} table saved.")
#             else:
#                 print(f"⚠ No line data found in {lines_csv}.")
            
#             if not df_pairs.empty:
#                 df_pairs.to_sql(f"PairStats_{game_type}_{season}", engine, if_exists="replace", index=False, chunksize=5000, method="multi")
#                 print(f"✔ PairStats_{game_type}_{season} table saved.")
#             else:
#                 print(f"⚠ No pair data found in {lines_csv}.")
#         else:
#             print(f"⚠ File not found: {lines_csv}")

# # Process player bio information
# data_bio = "data/bio_information/allPlayersLookup.csv"
# process_csv(data_bio, "BIO_Info")


shots_df = pd.read_csv(r'C:\Users\agjri\Desktop\NHL_Chatbot\shots_with_line_data.csv')

# Convert 'season' to numeric (to handle any potential issues with data types)
shots_df['season'] = pd.to_numeric(shots_df['season'], errors='coerce')
shots_df['season'] = shots_df['season'].astype(int) 
shots_df['gameDate'] = pd.to_datetime(shots_df['gameDate'], errors='coerce').dt.date
# Save filtered data to a temporary file
filtered_shots_file = "filtered_shots.csv"
shots_df.to_csv(filtered_shots_file, index=False)
print("got to process csv call")
# Process CSV

process_csv(filtered_shots_file, "shots_data")

cursor.execute("SHOW COLUMNS FROM shots_data;")
columns = cursor.fetchall()

print("\nColumns in 'shots_data' table:")
for column in columns:
    print(column[0])

cursor.execute("SELECT season FROM shots_data LIMIT 5;")
seasons_check = cursor.fetchall()
print("\nSample stored seasons:", seasons_check)

# Close connection
cursor.close()
conn.close()
print(f"All available seasons have been processed into MySQL database '{MYSQL_DATABASE}'")
