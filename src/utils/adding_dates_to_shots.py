import pandas as pd
import requests
from datetime import datetime, timedelta

def get_game_ids_by_date(date):

    adjusted_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=6)).strftime('%Y-%m-%d')
    url = f"https://api-web.nhle.com/v1/schedule/{adjusted_date}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Extract game-ids
        game_ids = list({str(game['id']) for day in data.get('gameWeek', []) for game in day.get('games', [])})
        return game_ids

    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

def generate_dates():
    date_ranges = []
    today = datetime.today().date()

    # 2015: Oct 1 to Dec 31
    date_ranges.append((datetime(2015, 9, 1).date(), datetime(2015, 12, 31).date()))

    # 2016 to 2023: Jan 1 to Jul 1 and Oct 1 to Dec 31
    for year in range(2016, 2024):
        date_ranges.append((datetime(year, 1, 1).date(), datetime(year, 7, 1).date()))
        date_ranges.append((datetime(year, 9, 1).date(), datetime(year, 12, 31).date()))

    # 2025: Jan 1 to today
    date_ranges.append((datetime(2025, 1, 1).date(), today))

    return date_ranges

def get_season_type(game_id):
    """
    Determine the season type based on the game ID.
    """
    season_type_code = game_id[4:6]  # Extract the season type code (02 for regular, 03 for playoffs)
    
    if season_type_code == '02':
        return 'Regular'
    elif season_type_code == '03':
        return 'Playoff'
    else:
        return 'Other'


def main():
    data = []
    date_ranges = generate_dates()

    all_game_ids = set()  # Track all game IDs across all dates
    for start_date, end_date in date_ranges:
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            game_ids = get_game_ids_by_date(date_str)

            # Filter out any game IDs that have already been added
            unique_game_ids = list(set(game_ids) - all_game_ids)
            all_game_ids.update(unique_game_ids)  # Add the new game IDs to the set

            if unique_game_ids:
                season_type = get_season_type(unique_game_ids[0])

                # Append the date, count of game IDs, and season type
                data.append([date_str, len(unique_game_ids), unique_game_ids, season_type])
                print(f"Date: {date_str}, Number of Games: {len(game_ids)}, Unique Games: {len(unique_game_ids)}, Season Type: {season_type}")
            else:
                 data.append([date_str, 0, [], 'NA'])

            # Increment to the next day
            current_date += timedelta(days=1)
            
    df = pd.DataFrame(data, columns=['Date', 'Number of Game IDs', 'Game IDs', 'Season Type'])
    df.to_csv('nhl_game_data.csv', index=False)
    print("Data saved to nhl_game_data.csv")
if __name__ == "__main__":
    main()
