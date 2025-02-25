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
old_tables = ["RegularSeason2015", "RegularSeason2016", "RegularSeason2017", "RegularSeason2018", "RegularSeason2019", 
              "RegularSeason2020", "RegularSeason2021", "RegularSeason2022", "RegularSeason2023", "SkaterStats"]  # Add all obsolete names here

for table in old_tables:
    conn.execute(f"DROP TABLE IF EXISTS {table};")
    print(f"✔ Dropped old table '{table}'")

# Now process the new tables
for season in seasons:
    for is_playoff, game_type in [(0, "regular"), (1, "playoffs")]:
        csv_file = f"data/skaters/{season}/skaters_{game_type}_{season}.csv"
        table_name = f"SkaterStats_{game_type}_{season}"  # Ensure unique table names

        if os.path.exists(csv_file):
            print(f"Processing {csv_file}...")

            # Load CSV into pandas DataFrame
            df = pd.read_csv(csv_file, encoding="utf-8", low_memory=False)

            # Add season and is_playoff indicator
            df["season"] = season
            df["is_playoff"] = is_playoff  # 0 = Regular, 1 = Playoffs

            # Save to a separate table in SQLite
            df.to_sql(table_name, conn, if_exists="replace", index=False, chunksize=5000)
            print(f"✔ Data saved in table '{table_name}'")
        else:
            print(f"⚠ File not found: {csv_file}")

for season in seasons:
    for is_playoff, game_type in [(0, "regular"), (1, "playoffs")]:
        csv_file = f"data/goalies/{season}/goalies_{game_type}_{season}.csv"
        table_name = f"GoalieStats_{game_type}_{season}"  # Unique table name

        if os.path.exists(csv_file):
            print(f"Processing {csv_file}...")

            # Load CSV into pandas DataFrame
            df = pd.read_csv(csv_file, encoding="utf-8", low_memory=False)

            # Add season and is_playoff indicator
            df["season"] = season
            df["is_playoff"] = is_playoff  # 0 = Regular, 1 = Playoffs

            # Save to SQLite
            df.to_sql(table_name, conn, if_exists="replace", index=False, chunksize=5000)
            print(f"✔ Data saved in table '{table_name}'")
        else:
            print(f"⚠ File not found: {csv_file}")


# Close connection
conn.close()
print(f"All available seasons have been processed into '{db_file}'")
