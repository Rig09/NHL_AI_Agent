import sqlite3
import pandas as pd
import os

# Define seasons to process
seasons = range(2015, 2024)  # Adjust range as needed

# SQLite database file
db_file = "SkatersStats.db"

# Connect to SQLite
conn = sqlite3.connect(db_file)

# Drop old tables (those that match the old naming scheme)
old_tables = [
    "RegularSeason2015", "RegularSeason2016", "RegularSeason2017", "RegularSeason2018", "RegularSeason2019", 
    "RegularSeason2020", "RegularSeason2021", "RegularSeason2022", "RegularSeason2023", "SkaterStats"
]  # Add all obsolete names here

for table in old_tables:
    conn.execute(f"DROP TABLE IF EXISTS {table};")
    print(f"✔ Dropped old table '{table}'")

# Function to process CSV files and save to SQLite
def process_csv(file_path, table_name, season, is_playoff):
    if os.path.exists(file_path):
        print(f"Processing {file_path}...")
        df = pd.read_csv(file_path, encoding="utf-8", low_memory=False)
        df["season"] = season
        df["is_playoff"] = is_playoff
        df.to_sql(table_name, conn, if_exists="replace", index=False, chunksize=5000)
        print(f"✔ Data saved in table '{table_name}'")
    else:
        print(f"⚠ File not found: {file_path}")

# Process skaters, goalies, lines, and pairs data
for season in seasons:
    for is_playoff, game_type in [(0, "regular"), (1, "playoffs")]:
        # Skaters
        process_csv(f"data/skaters/{season}/skaters_{game_type}_{season}.csv", f"SkaterStats_{game_type}_{season}", season, is_playoff)
        
        # Goalies
        process_csv(f"data/goalies/{season}/goalies_{game_type}_{season}.csv", f"GoalieStats_{game_type}_{season}", season, is_playoff)
        
        # Lines and Pairs (from the same CSV, separated by 'position')
        lines_csv = f"data/pairings/{season}/pairings_{game_type}_{season}.csv"
        if os.path.exists(lines_csv):
            print(f"Processing {lines_csv}...")
            df = pd.read_csv(lines_csv, encoding="utf-8", low_memory=False)
            df["season"] = season
            df["is_playoff"] = is_playoff
            
            # Separate into lines and pairs
            df_lines = df[df["position"] == "line"]
            df_pairs = df[df["position"] == "pairing"]
            
            if not df_lines.empty:
                df_lines.to_sql(f"LineStats_{game_type}_{season}", conn, if_exists="replace", index=False, chunksize=5000)
                print(f"✔ LineStats_{game_type}_{season} table saved.")
            else:
                print(f"⚠ No line data found in {lines_csv}.")
            
            if not df_pairs.empty:
                df_pairs.to_sql(f"PairStats_{game_type}_{season}", conn, if_exists="replace", index=False, chunksize=5000)
                print(f"✔ PairStats_{game_type}_{season} table saved.")
            else:
                print(f"⚠ No pair data found in {lines_csv}.")
        else:
            print(f"⚠ File not found: {lines_csv}")

# Close connection
conn.close()
print(f"All available seasons have been processed into '{db_file}'")
