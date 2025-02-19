import sqlite3
import pandas as pd

# CSV file path
csv_file = r"data\skaters\2023\skaters_regular_2023.csv"

db_file = "2023RegularSeason.db"

# Load CSV into pandas DataFrame
df = pd.read_csv(csv_file)

# Connect to SQLite and save the CSV as a table
conn = sqlite3.connect(db_file)
df.to_sql("RegularSeason2023", conn, if_exists="replace", index=False)

conn.close()

print(f"CSV file '{csv_file}' has been converted to SQLite database '{db_file}'")