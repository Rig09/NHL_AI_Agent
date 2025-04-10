import requests
from utils.database_init import run_query_mysql
import pandas as pd
import numpy as np
from datetime import date
import matplotlib.pyplot as plt

def nhl_schedule_info_by_date(input_date: date):
    date_str = input_date.strftime("%Y-%m-%d")
    url = f"https://api-web.nhle.com/v1/schedule/{date_str}"
    response = requests.get(url)
    data = response.json()

    game_data = []

    for day in data.get("gameWeek", []):
        if day.get("date") != date_str:
            continue  # Skip days that don't match the requested date
        for game in day.get("games", []):
            game_info = {
                "game_id": game["id"],
                "date": day["date"],
                "venue": game["venue"]["default"],
                "start_time_utc": game["startTimeUTC"],
                "home_team": {
                    "name": f"{game['homeTeam']['placeName']['default']} {game['homeTeam']['commonName']['default']}",
                    "abbrev": game['homeTeam']['abbrev'],
                    "score": game['homeTeam'].get('score', None)
                },
                "away_team": {
                    "name": f"{game['awayTeam']['placeName']['default']} {game['awayTeam']['commonName']['default']}",
                    "abbrev": game['awayTeam']['abbrev'],
                    "score": game['awayTeam'].get('score', None)
                },
                "tv_broadcasts": [b["network"] for b in game.get("tvBroadcasts", [])],
                "winning_goalie": f"{game.get('winningGoalie', {}).get('firstInitial', {}).get('default', '')} {game.get('winningGoalie', {}).get('lastName', {}).get('default', '')}".strip(),
                "winning_goal_scorer": f"{game.get('winningGoalScorer', {}).get('firstInitial', {}).get('default', '')} {game.get('winningGoalScorer', {}).get('lastName', {}).get('default', '')}".strip(),
            }
            game_data.append(game_info)

    return game_data


def get_nhl_standings(input_date):

    date_str = input_date.strftime("%Y-%m-%d")
    url = f"https://api-web.nhle.com/v1/standings/{date_str}"
    response = requests.get(url)

    if response.status_code != 200:
        raise ValueError(f"Failed to fetch data for {date_str}: {response.status_code}")

    data = response.json()
    standings = []

    for team in data.get("standings", []):
        points = team.get('points', 0)
        standings.append({
            'Team Abbreviation': team.get('teamAbbrev', {}).get('default', ''),
            'Logo URL': team.get('teamLogo', ''),
            'Conference': team.get('conferenceName', ''),
            'Division': team.get('divisionName', ''),
            'Record': f"{team.get('wins', 0)}-{team.get('losses', 0)}-{team.get('otLosses', 0)}",
            'Points': points,
            'Point %': f"{team.get('pointPctg', 0.0):.3f}",
            'Streak': f"{team.get('streakCode', '')}{team.get('streakCount', 0)}",
            'GP': team.get('gamesPlayed', 0),
            'RegWins': team.get('regulationWins', 0)
        })

    df = pd.DataFrame(standings)

    # Split into top 3 in each division
    df['GamesRemaining'] = 82 - df['GP']
    divisions = df['Division'].unique()
    top3_dfs = {}
    for division in divisions:
        div_df = df[df['Division'] == division].sort_values('Points', ascending=False)
        top3_dfs[division] = div_df.head(3)

    # Top 3 in each division:
    atlantic_top3 = top3_dfs.get('Atlantic', pd.DataFrame())
    metro_top3 = top3_dfs.get('Metropolitan', pd.DataFrame())
    central_top3 = top3_dfs.get('Central', pd.DataFrame())
    pacific_top3 = top3_dfs.get('Pacific', pd.DataFrame())

    # Remaining teams in each conference
    top3_indices = pd.concat([atlantic_top3, metro_top3, central_top3, pacific_top3]).index
    rest_df = df.drop(index=top3_indices)

    east_rest = rest_df[rest_df['Conference'] == 'Eastern']
    west_rest = rest_df[rest_df['Conference'] == 'Western']

    return plot_nhl_standings(atlantic_top3, central_top3, metro_top3, pacific_top3, east_rest, west_rest, date_str)
    


def plot_nhl_standings(atlantic_top3, central_top3, metro_top3, pacific_top3, east_rest, west_rest, date_str):
    fig, ax = plt.subplots(figsize=(14, 8))

    # Set figure background to dark grey
    fig.patch.set_facecolor('#303030')
    
    # Create two subplots - one for Eastern and one for Western conference standings
    ax_east = fig.add_axes([0, 0, 0.5, 1])  # Left side for Eastern conference
    ax_west = fig.add_axes([0.5, 0, 0.5, 1])  # Right side for Western conference

    # Set axes background to dark grey
    # ax_east.set_facecolor('#303030')
    # ax_west.set_facecolor('#303030')

    # Prepare table data for Eastern conference (Atlantic, Central, Wild Card)
    east_table_data = []
    
    # Atlantic section - Add an empty row here
    east_table_data.append(['', '', '', '', '', '', '', '', ''])  # Empty row where "Atlantic" would be
    
    # Atlantic teams data with numbering
    atlantic_numbered = atlantic_top3[['Team Abbreviation', 'GP', 'Record', 'Points', 'Streak', 'Point %', 'RegWins', 'GamesRemaining']].values
    for idx, row in enumerate(atlantic_numbered):
        east_table_data.append([f'{idx+1}', *row])  # Add 1, 2, 3... before team data
    
    # Central section - Add an empty row here
    east_table_data.append(['', '', '', '', '', '', '', '', ''])  # Empty row where "Central" would be
    
    # Central teams data with numbering
    central_numbered = central_top3[['Team Abbreviation', 'GP', 'Record', 'Points', 'Streak', 'Point %', 'RegWins', 'GamesRemaining']].values
    for idx, row in enumerate(central_numbered):
        east_table_data.append([f'{idx+1}', *row])  # Add 1, 2, 3... before team data
    
    # Wild Card East section - Add an empty row here
    east_table_data.append(['', '', '', '', '', '', '', '', ''])  # Empty row where "Wild Card (East)" would be
    
    # Wild Card East teams data with numbering
    east_rest_numbered = east_rest[['Team Abbreviation', 'GP', 'Record', 'Points', 'Streak', 'Point %', 'RegWins', 'GamesRemaining']].values
    for idx, row in enumerate(east_rest_numbered):
        east_table_data.append([f'{idx+1}', *row])  # Add 1, 2, 3... before team data

    # Prepare table data for Western conference (Metropolitan, Pacific, Wild Card)
    west_table_data = []
    
    # Metropolitan section - Add an empty row here
    west_table_data.append(['', '', '', '', '', '', '', '', ''])  # Empty row where "Metropolitan" would be
    
    # Metropolitan teams data with numbering
    metro_numbered = metro_top3[['Team Abbreviation', 'GP', 'Record', 'Points', 'Streak', 'Point %', 'RegWins', 'GamesRemaining']].values
    for idx, row in enumerate(metro_numbered):
        west_table_data.append([f'{idx+1}', *row])  # Add 1, 2, 3... before team data
    
    # Pacific section - Add an empty row here
    west_table_data.append(['', '', '', '', '', '', '', '', ''])  # Empty row where "Pacific" would be
    
    # Pacific teams data with numbering
    pacific_numbered = pacific_top3[['Team Abbreviation', 'GP', 'Record', 'Points', 'Streak', 'Point %', 'RegWins', 'GamesRemaining']].values
    for idx, row in enumerate(pacific_numbered):
        west_table_data.append([f'{idx+1}', *row])  # Add 1, 2, 3... before team data
    
    # Wild Card West section - Add an empty row here
    west_table_data.append(['', '', '', '', '', '', '', '', ''])  # Empty row where "Wild Card (West)" would be
    
    # Wild Card West teams data with numbering
    west_rest_numbered = west_rest[['Team Abbreviation', 'GP', 'Record', 'Points', 'Streak', 'Point %', 'RegWins', 'GamesRemaining']].values
    for idx, row in enumerate(west_rest_numbered):
        west_table_data.append([f'{idx+1}', *row])  # Add 1, 2, 3... before team data

    # Hide axes for both tables
    ax_east.axis('off')
    ax_west.axis('off')
    ax_east.set_frame_on(False)
    ax_west.set_frame_on(False)

    # Create the tables without borders (no lines)
    table_east = ax_east.table(cellText=east_table_data, colLabels=['', 'Team', 'GP', 'Record', 'Points', 'Streak', 'Point %', 'RW', 'GR'], loc='center', cellLoc='center', colLoc='center', bbox=[0.05, 0.05, 0.9, 0.90])
    table_west = ax_west.table(cellText=west_table_data, colLabels=['', 'Team', 'GP', 'Record', 'Points', 'Streak', 'Point %', 'RW', 'GR'], loc='center', cellLoc='center', colLoc='center', bbox=[0.05, 0.05, 0.9, 0.90])

    # Set table background color and text color to match dark theme
    table_east.auto_set_font_size(False)
    table_west.auto_set_font_size(False)
    
    # Set background color of the cells and text to white
    for (i, j), cell in table_east.get_celld().items():
        cell.set_facecolor('#303030')  # Dark grey background for cells
        cell.set_text_props(color='white')  # White text
        
    for (i, j), cell in table_west.get_celld().items():
        cell.set_facecolor('#303030')  # Dark grey background for cells
        cell.set_text_props(color='white')  # White text

    # Set the header font to white
    for key, cell in table_east.get_celld().items():
        if key[0] == 0:  # Header row
            cell.set_text_props(color='white')  # White header text
            cell.set_facecolor('#303030')  # Dark grey header background

    for key, cell in table_west.get_celld().items():
        if key[0] == 0:  # Header row
            cell.set_text_props(color='white')  # White header text
            cell.set_facecolor('#303030')  # Dark grey header background

    # Scale the table down vertically
    table_east.scale(1.0, 0.5)
    table_west.scale(1.0, 0.5)

    # Add title and hide axes
    # ax_east.set_title("Eastern Conference", fontsize=14, color='white', backgroundcolor='#303030')
    # ax_west.set_title("Western Conference", fontsize=14, color='white', backgroundcolor='#303030')
    ax.set_axis_off()
    ax_east.axis('off')
    ax_west.axis('off')
    ax_east.set_alpha(1)
    ax_west.set_alpha(1)
    # Set the y-axis limits explicitly to ensure we can draw at expected positions
    ax_east.set_ylim(0, 1)  # Set the y-axis limits for the Eastern conference
    ax_west.set_ylim(0, 1)  # Set the y-axis limits for the Western conference

    # Adjust these values to position the horizontal lines correctly
    wildcard_line_y_east = 0.41  # Position of the line in the Eastern conference (try 0.5 for central positioning)
    wildcard_line_y_west = 0.41  # Position for the Western conference

    # Draw horizontal lines at these positions (adjust for your specific needs)
    ax_east.hlines(wildcard_line_y_east, 0, 1, color='white', linewidth=1)
    ax_west.hlines(wildcard_line_y_west, 0, 1, color='white', linewidth=1)

    # Remove all borders (no lines at all)
    for (i, j), cell in table_east.get_celld().items():
        cell.set_edgecolor('none')  # Remove all edges for east table

    for (i, j), cell in table_west.get_celld().items():
        cell.set_edgecolor('none')  # Remove all edges for west table

    # Add category headings as text outside the tables
    # Eastern Conference category headings
    ax_east.text(0.05, .895, 'Atlantic', fontsize=14, verticalalignment='top', horizontalalignment='left', color='white')
    ax_east.text(0.05, 0.71, 'Central', fontsize=14, verticalalignment='top', horizontalalignment='left', color='white')
    ax_east.text(0.05, 0.53, 'Wild Card (East)', fontsize=14, verticalalignment='top', horizontalalignment='left', color='white')

    # Western Conference category headings
    ax_west.text(0.05, 0.905, 'Metropolitan', fontsize=14, verticalalignment='top', horizontalalignment='left', color='white')
    ax_west.text(0.05, 0.71, 'Pacific', fontsize=14, verticalalignment='top', horizontalalignment='left', color='white')
    ax_west.text(0.05, 0.53, 'Wild Card (West)', fontsize=14, verticalalignment='top', horizontalalignment='left', color='white')

    # Add titles and adjust layout
    plt.suptitle(f"NHL Standings on {date_str}", fontsize=16, color='white', backgroundcolor='#303030')
    plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)  # Adjust layout
    # plt.tight_layout()
    return fig


# date = date.today()
# standings = get_nhl_standings(date)
# games = nhl_schedule_info_by_date("2023-11-10")
# print(games)