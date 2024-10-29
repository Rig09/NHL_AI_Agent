#!/bin/bash

# Base directories
SKATERS_DIR="./skaters"
SHOTS_DIR="./shots"

# URLs for download
BASE_URL="https://moneypuck.com/moneypuck/playerData/seasonSummary"
ZIP_URL="https://peter-tanner.com/moneypuck/downloads/shots_2015-2023.zip"

# Create the main data directories if they don't exist
mkdir -p "$SKATERS_DIR"
mkdir -p "$SHOTS_DIR"

# Loop through each year from 2015 to 2023
for YEAR in {2015..2023}; do
    # Create a subfolder for each season year
    SEASON_DIR="$SKATERS_DIR/$YEAR"
    mkdir -p "$SEASON_DIR"

    # Define file paths without the -1 suffix
    REGULAR_FILE="$SEASON_DIR/skaters_regular_${YEAR}.csv"
    PLAYOFF_FILE="$SEASON_DIR/skaters_playoffs_${YEAR}.csv"
    
    # Check and download the regular season file if it doesn't exist
    if [ ! -f "$REGULAR_FILE" ]; then
        echo "Downloading skaters_regular_${YEAR}.csv..."
        curl -o "$REGULAR_FILE" "$BASE_URL/$YEAR/regular/skaters.csv"
    else
        echo "File skaters_regular_${YEAR}.csv already exists."
    fi

    # Check and download the playoffs file if it doesn't exist
    if [ ! -f "$PLAYOFF_FILE" ]; then
        echo "Downloading skaters_playoffs_${YEAR}.csv..."
        curl -o "$PLAYOFF_FILE" "$BASE_URL/$YEAR/playoffs/skaters.csv"
    else
        echo "File skaters_playoffs_${YEAR}.csv already exists."
    fi
done

# Check if shots_2015-2023.csv exists, if not download and unzip it
ZIP_FILE="$SHOTS_DIR/shots_2015-2023.zip"
FILE3="$SHOTS_DIR/shots_2015-2023.csv"

if [ ! -f "$FILE3" ]; then
    echo "Downloading shots_2015-2023.zip..."
    curl -o "$ZIP_FILE" "$ZIP_URL"
    
    echo "Unzipping shots_2015-2023.zip..."
    unzip "$ZIP_FILE" -d "$SHOTS_DIR"

    # Delete the .zip file after extraction
    echo "Deleting shots_2015-2023.zip..."
    rm "$ZIP_FILE"
else
    echo "File shots_2015-2023.csv already exists."
fi

echo "All files are checked, downloaded, and organized into subfolders if necessary."