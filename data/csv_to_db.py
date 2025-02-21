import sqlite3
import pandas as pd
import os

# Define seasons to process
seasons = range(2015, 2024)  # Adjust range as needed

# SQLite database file
db_file = "SkatersStats.db"

# Connect to SQLite
conn = sqlite3.connect(db_file)

# Master table name
table_name = "SkaterStats"

all_data = []  # List to store data before inserting into DB

for season in seasons:
    for is_playoff, game_type in [(0, "regular"), (1, "playoffs")]:
        csv_file = f"data/skaters/{season}/skaters_{game_type}_{season}.csv"

        if os.path.exists(csv_file):
            print(f"Processing {csv_file}...")

            # Load CSV into pandas DataFrame
            df = pd.read_csv(csv_file, encoding="utf-8", low_memory=False)

            # Add season and is_playoff indicator
            df["season"] = season
            df["is_playoff"] = is_playoff  # 0 = Regular, 1 = Playoffs

            # Append to all_data list
            all_data.append(df)
        else:
            print(f"⚠ File not found: {csv_file}")

# Combine all data into a single DataFrame and write to SQLite
if all_data:
    final_df = pd.concat(all_data, ignore_index=True)
    final_df.to_sql(table_name, conn, if_exists="replace", index=False, chunksize=5000)
    print(f"✔ All data saved in table '{table_name}'")
else:
    print("⚠ No data was processed!")

# Close connection
conn.close()
print(f"All available seasons have been processed into '{db_file}'")