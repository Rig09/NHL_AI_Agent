#!/bin/bash

# Directory to check for files
DATA_DIR="./data"

# File paths
FILE1="$DATA_DIR/skaters_regular_2023-2024.csv"
FILE2="$DATA_DIR/skaters_playoffs_2023-2024.csv"
FILE3="$DATA_DIR/shots_2015-2023.csv"
ZIP_FILE="$DATA_DIR/shots_2015-2023.zip"

# URLs for download
# TODO: Additional files may need to be downloaded and this code could use lists instead of individual conditions for each.
URL1="https://moneypuck.com/moneypuck/playerData/seasonSummary/2023/regular/skaters.csv"
URL2="https://moneypuck.com/moneypuck/playerData/seasonSummary/2023/playoffs/skaters.csv"
ZIP_URL="https://peter-tanner.com/moneypuck/downloads/shots_2015-2023.zip"

# Create the data directory if it doesn't exist
mkdir -p "$DATA_DIR"

# Check if skaters_regular_2023-2024.csv exists, if not download it
if [ ! -f "$FILE1" ]; then
    echo "Downloading skaters_regular_2023-2024.csv..."
    curl -o "$FILE1" "$URL1"
else
    echo "File skaters_regular_2023-2024.csv already exists."
fi

# Check if skaters_playoffs_2023-2024.csv exists, if not download it
if [ ! -f "$FILE2" ]; then
    echo "Downloading skaters_playoffs_2023-2024.csv..."
    curl -o "$FILE2" "$URL2"
else
    echo "File skaters_playoffs_2023-2024.csv already exists."
fi

# Check if shots_2015-2023.csv exists, if not download and unzip it
if [ ! -f "$FILE3" ]; then
    echo "Downloading shots_2015-2023.zip..."
    curl -o "$ZIP_FILE" "$ZIP_URL"
    
    echo "Unzipping shots_2015-2023.zip..."
    unzip "$ZIP_FILE" -d "$DATA_DIR"

    # Optional: Move the extracted file to a specific name if needed
    # if [ -f "$DATA_DIR/shots.csv" ]; then
    #     mv "$DATA_DIR/shots.csv" "$FILE3"
    # fi

    # Delete the .zip file after extraction
    echo "Deleting shots_2015-2023.zip..."
    rm "$ZIP_FILE"
else
    echo "File shots_2015-2023.csv already exists."
fi

echo "All files are checked, downloaded, and unzipped if necessary."
