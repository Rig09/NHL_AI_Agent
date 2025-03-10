from app import get_secrets_or_env
from utils.database_init import init_db
from shot_maps.shot_map_plotting import extract_shot_data
import requests
import pandas as pd
from bs4 import BeautifulSoup

# Cache for PBP reports to prevent duplicate fetches
pbp_cache = {}

# NOTE: Function is not working yet.

def get_pbp_events(game_id, season):
    """
    Fetch play-by-play data from NHL's HTML report with caching
    """
    # Check cache first
    if game_id in pbp_cache:
        print(f"Using cached PBP data for game {game_id}")
        return pbp_cache[game_id]

    # Convert game_id to proper format (e.g., 2023030181 -> PL030181.HTM)
    season_str = f"{season}{season+1}"  # e.g., 20232024
    # Extract last 6 digits and ensure leading zero
    game_number = str(game_id)[-6:]
    if game_number.startswith('3'):  # Playoff game
        report_id = f"PL0{game_number}"
    else:  # Regular season game
        report_id = f"PL{game_number}"
    
    url = f"https://www.nhl.com/scores/htmlreports/{season_str}/{report_id}.HTM"
    print(f"Fetching PBP report from: {url}")  # Debug print
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the main play-by-play table
        table = soup.find('table', class_='tablewidth')
        if not table:
            print("Could not find main PBP table")
            return None
            
        # Find all rows in the play-by-play table
        events = []
        rows = table.find_all('tr')
        print(f"Found {len(rows)} total rows in table")
        
        for row in rows:
            # Skip header rows and empty rows
            if not row.find_all('td'):
                continue
                
            cols = row.find_all('td')
            if len(cols) >= 6:  # Valid event row should have at least 6 columns
                try:
                    # Check if this is a GOAL event first
                    event_type = cols[4].text.strip() if len(cols) > 4 else ""
                    if event_type != 'GOAL':
                        continue
                        
                    # Get the event number from the first column with class='bborder'
                    event_num = None
                    event_cell = row.find('td', class_='bborder')
                    if event_cell and event_cell.text.strip().isdigit():
                        event_num = event_cell.text.strip()
                    
                    if not event_num:
                        continue
                        
                    period = int(cols[1].text.strip())  # Period
                    
                    # Parse the game time (second row of the time column)
                    time_cell = cols[3]
                    time_parts = time_cell.get_text(separator='|').split('|')
                    if len(time_parts) >= 2:
                        game_time = time_parts[1].strip()  # Use the game time (second part)
                    else:
                        game_time = time_parts[0].strip()  # Fallback to first part if only one exists
                        
                    description = cols[5].text.strip() if len(cols) > 5 else ""  # Description
                    
                    print(f"Found GOAL: #{event_num} at {game_time} in period {period}")
                    print(f"Description: {description}")
                    
                    events.append({
                        'pl_id': event_num,
                        'period': period,
                        'time': game_time,
                        'event_type': event_type,
                        'description': description
                    })
                except (ValueError, IndexError) as e:
                    print(f"Error parsing row: {e}")
                    continue  # Skip rows that don't match expected format
        
        # Cache the results
        pbp_cache[game_id] = events
        print(f"Found {len(events)} GOAL events in PBP report")
        return events
    except requests.RequestException as e:
        print(f"Error fetching PBP report for game {game_id}: {e}")
        return None

def find_goal_event_number(events, period, time_in_seconds, shooter_name):
    """
    Find the PL ID for a specific goal in the play-by-play data
    """
    if not events:
        print(f"No events provided for period {period}, time {time_in_seconds}, shooter {shooter_name}")
        return None
        
    # Convert time from seconds to MM:SS format for comparison
    minutes = int(time_in_seconds) // 60
    seconds = int(time_in_seconds) % 60
    time_str = f"{minutes:02d}:{seconds:02d}"
    
    # For period 1, time counts up from 00:00
    # For periods 2 and 3, need to add 20:00 for each previous period
    if period > 1:
        base_minutes = (period - 1) * 20
        minutes += base_minutes
        time_str = f"{minutes:02d}:{seconds:02d}"
    
    print(f"\nLooking for goal: Period {period}, Game Time {time_str}, Shooter {shooter_name}")
    
    # Look for matching goal event
    for event in events:
        print(f"Comparing with event: Period {event['period']}, Time {event['time']}, Description: {event['description']}")
        if (event['period'] == period and
            shooter_name.upper() in event['description'].upper()):
            # Convert event time to seconds for comparison
            try:
                event_time_parts = event['time'].split(':')
                event_minutes = int(event_time_parts[0])
                event_seconds = int(event_time_parts[1])
                
                # If times are within 3 seconds, consider it a match
                event_total_seconds = event_minutes * 60 + event_seconds
                target_total_seconds = minutes * 60 + seconds
                if abs(event_total_seconds - target_total_seconds) <= 3:
                    print(f"Match found! PL ID: {event['pl_id']}")
                    return event['pl_id']
            except (ValueError, IndexError) as e:
                print(f"Error parsing event time: {e}")
                continue
    
    print("No matching goal event found")
    return None

def interactive_goal_map_scatter_get(db, player_name, season_lower_bound, season_upper_bound, situation, season_type):
    """
    Extracts shot data for a given player, season, situation, and shot result type
    and generates embed links for goal replays
    """
    shot_data = extract_shot_data(db, player_name, season_lower_bound, season_upper_bound, situation, 'GOAL', season_type)
    
    # Create a list to store embed URLs
    embed_urls = []
    
    # Process each goal
    for _, row in shot_data.iterrows():
        game_id = row['game_id']
        period = row['period']
        time = row['time']
        
        print(f"\nProcessing goal: Game {game_id}, Period {period}, Time {time}")
        
        # Fetch play-by-play data from HTML report
        events = get_pbp_events(game_id, season_lower_bound)
        
        # Find the PL ID for this goal
        pl_id = find_goal_event_number(events, period, time, player_name)
        
        if pl_id:
            embed_url = f"https://www.nhl.com/ppt-replay/goal/{game_id}/{pl_id}"
        else:
            embed_url = "Event not found"
            
        embed_urls.append(embed_url)
    
    # Add embed URLs to the DataFrame
    shot_data['embed_url'] = embed_urls
    
    print("\nGoal data with embed links:")
    print(shot_data[['game_id', 'period', 'time', 'embed_url']].to_string())
    
    return shot_data

if __name__ == "__main__":
    MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, open_ai_key = get_secrets_or_env(remote=True)
    db = init_db(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE)
    interactive_goal_map_scatter_get(db, 'Zach Hyman', 2023, 2023, 'all', 'playoffs')
    # TODO: Test with regular season data