#!/bin/bash

# Base directories
SKATERS_DIR="./skaters"
GOALIES_DIR="./goalies"
PAIRINGS_DIR="./pairings"
SHOTS_DIR="./shots"
BIO_INFO_DIR="./bio_information"

# URLs for download
BASE_URL="https://moneypuck.com/moneypuck/playerData/seasonSummary"
ZIP_URL="https://peter-tanner.com/moneypuck/downloads/shots_2015-2023.zip"
BIO_INFO_URL="https://moneypuck.com/moneypuck/playerData/playerBios/allPlayersLookup.csv"

# Create the main data directories if they don't exist
mkdir -p "$SKATERS_DIR"
mkdir -p "$GOALIES_DIR"
mkdir -p "$PAIRINGS_DIR"
mkdir -p "$SHOTS_DIR"
mkdir -p "$BIO_INFO_DIR"

# Loop through each year from 2015 to 2023
for YEAR in {2015..2023}; do
    # Create a subfolder for each season year
    SEASON_SKATERS_DIR="$SKATERS_DIR/$YEAR"
    SEASON_GOALIES_DIR="$GOALIES_DIR/$YEAR"
    SEASON_PAIRINGS_DIR="$PAIRINGS_DIR/$YEAR"

    mkdir -p "$SEASON_SKATERS_DIR"
    mkdir -p "$SEASON_GOALIES_DIR"
    mkdir -p "$SEASON_PAIRINGS_DIR"

    # Define file paths
    SKATERS_REGULAR_FILE="$SEASON_SKATERS_DIR/skaters_regular_${YEAR}.csv"
    SKATERS_PLAYOFF_FILE="$SEASON_SKATERS_DIR/skaters_playoffs_${YEAR}.csv"

    GOALIES_REGULAR_FILE="$SEASON_GOALIES_DIR/goalies_regular_${YEAR}.csv"
    GOALIES_PLAYOFF_FILE="$SEASON_GOALIES_DIR/goalies_playoffs_${YEAR}.csv"

    PAIRINGS_REGULAR_FILE="$SEASON_PAIRINGS_DIR/pairings_regular_${YEAR}.csv"
    PAIRINGS_PLAYOFF_FILE="$SEASON_PAIRINGS_DIR/pairings_playoffs_${YEAR}.csv"

    # Download skaters data
    if [ ! -f "$SKATERS_REGULAR_FILE" ]; then
        echo "Downloading skaters_regular_${YEAR}.csv..."
        curl -o "$SKATERS_REGULAR_FILE" "$BASE_URL/$YEAR/regular/skaters.csv"
    else
        echo "File skaters_regular_${YEAR}.csv already exists."
    fi

    if [ ! -f "$SKATERS_PLAYOFF_FILE" ]; then
        echo "Downloading skaters_playoffs_${YEAR}.csv..."
        curl -o "$SKATERS_PLAYOFF_FILE" "$BASE_URL/$YEAR/playoffs/skaters.csv"
    else
        echo "File skaters_playoffs_${YEAR}.csv already exists."
    fi

    # Download goalies data
    if [ ! -f "$GOALIES_REGULAR_FILE" ]; then
        echo "Downloading goalies_regular_${YEAR}.csv..."
        curl -o "$GOALIES_REGULAR_FILE" "$BASE_URL/$YEAR/regular/goalies.csv"
    else
        echo "File goalies_regular_${YEAR}.csv already exists."
    fi

    if [ ! -f "$GOALIES_PLAYOFF_FILE" ]; then
        echo "Downloading goalies_playoffs_${YEAR}.csv..."
        curl -o "$GOALIES_PLAYOFF_FILE" "$BASE_URL/$YEAR/playoffs/goalies.csv"
    else
        echo "File goalies_playoffs_${YEAR}.csv already exists."
    fi

    # Download pairings (lines) data
    if [ ! -f "$PAIRINGS_REGULAR_FILE" ]; then
        echo "Downloading pairings_regular_${YEAR}.csv..."
        curl -o "$PAIRINGS_REGULAR_FILE" "$BASE_URL/$YEAR/regular/lines.csv"
    else
        echo "File pairings_regular_${YEAR}.csv already exists."
    fi

    if [ ! -f "$PAIRINGS_PLAYOFF_FILE" ]; then
        echo "Downloading pairings_playoffs_${YEAR}.csv..."
        curl -o "$PAIRINGS_PLAYOFF_FILE" "$BASE_URL/$YEAR/playoffs/lines.csv"
    else
        echo "File pairings_playoffs_${YEAR}.csv already exists."
    fi

done

# Check if shots_2015-2023.csv exists, if not download and unzip it
ZIP_FILE="$SHOTS_DIR/shots_2015-2023.zip"
SHOTS_FILE="$SHOTS_DIR/shots_2015-2023.csv"

if [ ! -f "$SHOTS_FILE" ]; then
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

# Check if allPlayersLookup.csv exists, if not download it
BIO_FILE="$BIO_INFO_DIR/allPlayersLookup.csv"
if [ ! -f "$BIO_FILE" ]; then
    echo "Downloading allPlayersLookup.csv..."
    curl -o "$BIO_FILE" "$BIO_INFO_URL"
else
    echo "File allPlayersLookup.csv already exists."
fi

echo "All files are checked, downloaded, and organized into subfolders if necessary."
