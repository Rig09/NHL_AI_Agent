import pandas as pd
import numpy as np
from datetime import date, datetime
from utils.database_init import run_query_mysql, init_db
import requests
from dotenv import load_dotenv
import os
#import cairosvg
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from PIL import Image
from io import BytesIO
import mysql.connector
from decimal import Decimal
import matplotlib.colors as mcolors
"""
Generate player cards for the NHL AI agent.
Add Team logo and headshot image to card from the NHL API
Information: Name, Team, Position, Age, Height, Weight, Handedness, avg TOI, GP
Scoring Header: Goals, assists, points, primary points, primary assists, 5on5 Goals, 5on5 Points, 5on5 Primary Points
Underlying Numbers Even Strength Header: Query moneypuck database for 5 on 5 expected goals for on ice and percentile, and expected goals against on ice (5 on 5) and percentile, expected goals percentage, expected goals difference. 
Special Teams: Check for min toi for pp and pk, if not met, set to "NA". If met, query moneypuck database for expected goals for (pp) and against on ice (pk) and percentile, also list Powerplay goals, assists, and points.
Team Impact: On ice expected goals for per 60 when playing - same team same stat not on ice, same for defense, and finally for the difference. 

If Multiple seasons are selected, create a graph for xg % at 5 on 5 for each season. Do the above for all the seasons together.

"""

# Helper to load image from URL (PNG or JPEG)
def load_image_from_url(url):
    response = requests.get(url)
    return Image.open(BytesIO(response.content))



# load_dotenv()

# MYSQL_HOST = os.getenv("MYSQL_HOST")
# MYSQL_USER = os.getenv("MYSQL_USER")
# MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
# MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
# open_ai_key = os.getenv("OPENAI_API_KEY")

def find_player_id(db, player_name):
    query = f"""SELECT playerId FROM bio_info WHERE name LIKE '%{player_name}%'
            """
    print(query)
    result = run_query_mysql(query, db)
    
    if result and isinstance(result, list) and isinstance(result[0], dict):
        return result[0].get("playerId")
    
    return None


# Define a function to get the color based on the percentile
def get_box_color(percentile):
    # Percentile above 50
    if percentile > 50:
        # Transition from green to brighter green
        return mcolors.to_rgba(f'#{int((1 - (percentile - 50) / 50) * 255):02x}ff00')
    # Percentile below 50
    else:
        return mcolors.to_rgba(f'#ff{int(abs(((percentile)/50) * 255)):02x}00')

def get_basic_stats_query(situation, player_name, season_value):
   return f"""
                SELECT GAMES_PLAYED, ICETIME, onIce_xGoalsPercentage, offIce_xGoalsPercentage, onIce_corsiPercentage, 
                offIce_corsiPercentage,I_F_xGoals, I_F_primaryAssists, I_F_shotsOnGoal, I_F_points, I_F_goals, I_F_penalityMinutes, I_F_takeaways, I_F_giveaways, 
                I_F_lowDangerShots, I_F_mediumDangerShots, I_F_highDangerShots, OnIce_F_xGoals, OnIce_F_goals, OnIce_A_xGoals, OnIce_A_goals, OffIce_F_xGoals, OffIce_A_xGoals, I_F_hits, shotsBlockedByPlayer
                FROM skaterstats_regular_{season_value} 
                WHERE name = '{player_name}' AND SITUATION = '{situation}'
                """

def get_percentile_query(db_connection, situation, player_name, season_value):
    query =  f"""
                WITH player_stats AS (
                    SELECT 
                        name,
                        GAMES_PLAYED, ICETIME, onIce_xGoalsPercentage, offIce_xGoalsPercentage, onIce_corsiPercentage, 
                        offIce_corsiPercentage, I_F_xGoals, I_F_primaryAssists, I_F_shotsOnGoal, I_F_points, I_F_goals, 
                        I_F_penalityMinutes, I_F_takeaways, I_F_giveaways, I_F_lowDangerShots, I_F_mediumDangerShots, 
                        I_F_highDangerShots, OnIce_F_xGoals, OnIce_F_goals, OnIce_A_xGoals, OnIce_A_goals, OffIce_F_xGoals, 
                        OffIce_A_xGoals, I_F_hits, shotsBlockedByPlayer
                    FROM skaterstats_regular_{season_value}
                    WHERE SITUATION = '{situation}'AND ICETIME IS NOT NULL AND ICETIME > 6000
                ),
                all_players_stats AS (
                    SELECT 
                        name, GAMES_PLAYED, ICETIME, onIce_xGoalsPercentage, offIce_xGoalsPercentage, onIce_corsiPercentage, 
                        offIce_corsiPercentage, I_F_xGoals, I_F_primaryAssists, I_F_shotsOnGoal, I_F_points, I_F_goals, 
                        I_F_penalityMinutes, I_F_takeaways, I_F_giveaways, I_F_lowDangerShots, I_F_mediumDangerShots, 
                        I_F_highDangerShots, OnIce_F_xGoals, OnIce_F_goals, OnIce_A_xGoals, OnIce_A_goals, OffIce_F_xGoals, 
                        OffIce_A_xGoals, I_F_hits, shotsBlockedByPlayer
                    FROM skaterstats_regular_{season_value}
                    WHERE SITUATION = '{situation}' AND ICETIME IS NOT NULL AND ICETIME > 6000
                ),
                player_rank AS (
                    SELECT 
                        ps.name,
                        ROW_NUMBER() OVER (ORDER BY ps.onIce_xGoalsPercentage DESC) AS onIce_xGoalsPercentage_rank,
                        ROW_NUMBER() OVER (ORDER BY ((ps.I_F_goals / ps.ICETIME)*3600) DESC) AS goals_per_60_rank,
                        ROW_NUMBER() OVER (ORDER BY ((ps.I_F_points / ps.ICETIME)*3600) DESC) AS points_per_60_rank,
                        ROW_NUMBER() OVER (ORDER BY ((ps.I_F_primaryAssists / ps.ICETIME)*3600) DESC) AS primary_assists_per_60_rank,
                        ROW_NUMBER() OVER (ORDER BY (ps.OnIce_F_xGoals/ps.ICETIME) DESC) AS OnIce_F_xGoals_per_60_rank,
                        ROW_NUMBER() OVER (ORDER BY (ps.OnIce_A_xGoals/ps.ICETIME) ASC) AS OnIce_A_xGoals_per_60_rank,
                        ROW_NUMBER() OVER (ORDER BY ((ps.OnIce_F_xGoals/ps.ICETIME) - (ps.OffIce_F_xGoals/((ps.GAMES_PLAYED*3600) - ICETIME)))  DESC) AS Offense_impact_rank,
                        ROW_NUMBER() OVER (ORDER BY ((ps.OnIce_A_xGoals/ps.ICETIME) - (ps.OffIce_A_xGoals/((ps.GAMES_PLAYED*3600) - ICETIME)))  ASC) AS Defense_impact_rank,
                        ROW_NUMBER() OVER (ORDER BY ((ps.I_F_goals / ps.I_F_shotsOnGoal) * 100) DESC) AS shooting_percentage_rank,
                        ROW_NUMBER() OVER (ORDER BY (ps.I_F_goals / ps.I_F_xGoals) DESC) AS goals_per_xg_rank,
                        ROW_NUMBER() OVER (ORDER BY ((ps.I_F_points - ps.I_F_goals)/ps.ICETIME) DESC) AS assists_per_60_rank,
                        ROW_NUMBER() OVER (ORDER BY (ps.I_F_hits/ps.ICETIME) DESC) AS hits_per_60_rank,
                        ROW_NUMBER() OVER (ORDER BY (ps.shotsBlockedByPlayer/ps.ICETIME) DESC) AS shotsBlockedByPlayer_per_60_rank,
                        ROW_NUMBER() OVER (ORDER BY (ps.I_F_highDangerShots/ps.ICETIME) DESC) AS highDangerShots_per_60_rank,
                        ROW_NUMBER() OVER (ORDER BY (ps.I_F_takeaways/ps.ICETIME) DESC) AS takeaways_per_60_rank,
                        ROW_NUMBER() OVER (ORDER BY (ps.I_F_xGoals/ps.ICETIME) DESC) AS I_F_xGoals_per_60_rank,
                        ROW_NUMBER() OVER (ORDER BY (ps.I_F_shotsOnGoal/ps.ICETIME) DESC) AS shotsOnGoal_per_60_rank
                    FROM player_stats ps
                )
                SELECT 
                    pr.name,
                    (100 - (pr.onIce_xGoalsPercentage_rank / (SELECT COUNT(*) FROM all_players_stats WHERE onIce_xGoalsPercentage IS NOT NULL AND ICETIME > 6000) * 100)) AS onIce_xGoalsPercentage_percentile,
                    (100 - (pr.goals_per_60_rank / (SELECT COUNT(*) FROM all_players_stats WHERE ((I_F_goals / ICETIME) * 3600) IS NOT NULL AND ICETIME > 6000) * 100)) AS goals_per_60_percentile,
                    (100 - (pr.points_per_60_rank / (SELECT COUNT(*) FROM all_players_stats WHERE ((I_F_points / ICETIME) * 3600) IS NOT NULL AND ICETIME > 6000) * 100)) AS points_per_60_percentile,
                    (100 - (pr.primary_assists_per_60_rank / (SELECT COUNT(*) FROM all_players_stats WHERE I_F_primaryAssists IS NOT NULL AND ICETIME > 6000) * 100)) AS primary_assists_per_60_percentile,
                    (100 - (pr.OnIce_F_xGoals_per_60_rank / (SELECT COUNT(*) FROM all_players_stats WHERE (OnIce_F_xGoals / ICETIME) IS NOT NULL AND ICETIME > 6000) * 100)) AS OnIce_F_xGoals_per_60_percentile,
                    (100 - (pr.OnIce_A_xGoals_per_60_rank / (SELECT COUNT(*) FROM all_players_stats WHERE (OnIce_A_xGoals / ICETIME) IS NOT NULL AND ICETIME > 6000) * 100)) AS OnIce_A_xGoals_per_60_percentile,
                    (100 - (pr.Offense_impact_rank / (SELECT COUNT(*) FROM all_players_stats WHERE ((OnIce_F_xGoals / ICETIME) - (OffIce_F_xGoals / ((GAMES_PLAYED * 3600) - ICETIME))) IS NOT NULL AND ICETIME > 6000) * 100)) AS Offense_impact_percentile,
                    (100 - (pr.Defense_impact_rank / (SELECT COUNT(*) FROM all_players_stats WHERE ((OnIce_A_xGoals / ICETIME) - (OffIce_A_xGoals / ((GAMES_PLAYED * 3600) - ICETIME))) IS NOT NULL AND ICETIME > 6000) * 100)) AS Defense_impact_percentile,
                    (100 - (pr.shooting_percentage_rank / (SELECT COUNT(*) FROM all_players_stats WHERE ((I_F_goals / I_F_shotsOnGoal) * 100) IS NOT NULL AND ICETIME > 6000) * 100)) AS shooting_percentage_percentile,
                    (100 - (pr.goals_per_xg_rank / (SELECT COUNT(*) FROM all_players_stats WHERE (I_F_goals / I_F_xGoals) IS NOT NULL AND ICETIME > 6000) * 100)) AS goals_per_xg_percentile,
                    (100 - (pr.assists_per_60_rank / (SELECT COUNT(*) FROM all_players_stats WHERE I_F_points IS NOT NULL AND ICETIME > 6000) * 100)) AS assists_per_60_percentile,
                    (100 - (pr.hits_per_60_rank / (SELECT COUNT(*) FROM all_players_stats WHERE I_F_hits IS NOT NULL AND ICETIME > 6000) * 100)) AS hits_per_60_percentile,
                    (100 - (pr.shotsBlockedByPlayer_per_60_rank / (SELECT COUNT(*) FROM all_players_stats WHERE shotsBlockedByPlayer IS NOT NULL AND ICETIME > 6000) * 100)) AS shotsBlockedByPlayer_per_60_percentile,
                    (100 - (pr.highDangerShots_per_60_rank / (SELECT COUNT(*) FROM all_players_stats WHERE I_F_highDangerShots IS NOT NULL AND ICETIME > 6000) * 100)) AS highDangerShots_per_60_percentile,
                    (100 - (pr.takeaways_per_60_rank / (SELECT COUNT(*) FROM all_players_stats WHERE I_F_takeaways IS NOT NULL AND ICETIME > 6000) * 100)) AS takeaways_per_60_percentile,
                    (100 - (pr.I_F_xGoals_per_60_rank / (SELECT COUNT(*) FROM all_players_stats WHERE I_F_xGoals IS NOT NULL AND ICETIME > 6000) * 100)) AS I_F_xGoals_per_60_percentile,
                    (100 - (pr.shotsOnGoal_per_60_rank / (SELECT COUNT(*) FROM all_players_stats WHERE I_F_shotsOnGoal IS NOT NULL AND ICETIME > 6000) * 100)) AS shotsOnGoal_per_60_percentile
                FROM player_rank pr
                WHERE pr.name = '{player_name}'
                """
    print(query)
    try:
        cursor = db_connection.cursor(dictionary=True)  # Use dictionary=True to get results as dictionaries
        cursor.execute(query)
        result = cursor.fetchone()  # Use fetchone() since we expect only a single row as output
        cursor.close()

        if result:
                print(result)
                return result
        else:
                print("No data found for the player:", player_name)
                return None

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None
    except Exception as ex:
        print(f"Unexpected Error: {ex}")
        return None


def fetch_player_card(db, player_name, season):
    player_id = find_player_id(db, player_name)
    url = f"https://api-web.nhle.com/v1/player/{player_id}/landing"
    response = requests.get(url)
    
    if response.status_code != 200:
        return {"error": "Failed to fetch data", "status_code": response.status_code}
    
    data = response.json()

    team_logo_url = data.get("teamLogo", None) #URL for team logo
    sweaterNumber = data.get("sweaterNumber", None)
    position = data.get("position", None)
    headshot_url = data.get("headshot", None)
    heightInches = data.get("heightInInches", None)
    weightInPounds = data.get("weightInPounds", None)
    birthDate = data.get("birthDate", None)
    shootsCatches = data.get("shootsCatches", None)
    birthCountry = data.get("birthCountry", None)

    
    ev_total = {}
    non_ev_total = {}
    ev_counts = {}
    non_ev_counts = {}
    # TODO: Get images for team logos and headshots and perhaps birth country flags
    Basic_stats_seasons = {}
    percentile_seasons = {}
    total_percentiles = {}
    ev_percentiles = {}
    ev_percentiles_total = {}
    non_ev_percentiles_total = {}
    valid_seasons = 0

    if len(season) == 0:
        season_value = 2015
        for i in range(10):
            ev_key = f"{season_value}_ev"
            total_key = f"{season_value}"
            ev_percentile_key = f"{season_value}_ev_percentile"
            total_percentile_key = f"{season_value}_percentile"

            ev_query = get_basic_stats_query("5on5", player_name, season_value)
            total_query = get_basic_stats_query("all", player_name, season_value)
            
            ev_data = run_query_mysql(ev_query, db)

            # If ev_data is empty or None, increment season_value and try again
            if not ev_data:
                season_value += 1
                continue  # Restart loop with incremented season_value

            Basic_stats_seasons[ev_key] = ev_data
            #Basic_stats_seasons[f"'{season_value}'_ev"] = run_query_mysql(ev_query, db)
            Basic_stats_seasons[total_key] = run_query_mysql(total_query, db)

            percentile_seasons[ev_percentile_key] = get_percentile_query(db, "5on5", player_name, season_value)
            percentile_seasons[total_percentile_key] = get_percentile_query(db, "all", player_name, season_value)

            ev_data = Basic_stats_seasons[ev_key]
            total_data = Basic_stats_seasons[total_key]
            ev_percentiles = percentile_seasons[ev_percentile_key]
            total_percentiles = percentile_seasons[total_percentile_key]
            if ev_data and ev_data[0].get("ICETIME", 0) > 100:

                for k, v in ev_data[0].items():
                    if isinstance(v, (int, float)):
                        if isinstance(v, float) and 0 < v < 1:
                            ev_total[k] = ev_total.get(k, 0) + v
                            ev_counts[k] = ev_counts.get(k, 0) + 1
                        else:
                            ev_total[k] = ev_total.get(k, 0) + v

                # Calculate average percentile for each stat in `ev_percentiles`
                for key in ev_percentiles.keys():
                    if isinstance(ev_percentiles[key], (int, float, Decimal)):
                        ev_percentiles_total[key] = float(ev_percentiles_total.get(key, 0)) + float(ev_percentiles[key])
                valid_seasons += 1

            if total_data and total_data[0].get("ICETIME", 0) > 100:
                for k, v in total_data[0].items():
                    if isinstance(v, (int, float)):
                        if isinstance(v, float) and 0 < v < 1:
                            non_ev_total[k] = non_ev_total.get(k, 0) + v
                            non_ev_counts[k] = non_ev_counts.get(k, 0) + 1
                        else:
                            non_ev_total[k] = non_ev_total.get(k, 0) + v

                # Calculate average percentile for each stat in `total_percentiles`
                for key in total_percentiles.keys():
                    if isinstance(total_percentiles[key], (int, float, Decimal)):
                        non_ev_percentiles_total[key] = float(non_ev_percentiles_total.get(key, 0)) + float(total_percentiles[key])

            season_value += 1

    else:
        for season_value in season:
            ev_key = f"{season_value}_ev"
            total_key = f"{season_value}"
            ev_percentile_key = f"{season_value}_ev_percentile"
            total_percentile_key = f"{season_value}_percentile"
            
            ev_query = get_basic_stats_query("5on5", player_name, season_value)
            total_query = get_basic_stats_query("all", player_name, season_value)


            Basic_stats_seasons[ev_key] = run_query_mysql(ev_query, db)
            Basic_stats_seasons[total_key] = run_query_mysql(total_query, db)

            percentile_seasons[ev_percentile_key] = get_percentile_query(db, "5on5", player_name, season_value)
            percentile_seasons[total_percentile_key] = get_percentile_query(db, "all", player_name, season_value)

            ev_data = Basic_stats_seasons[ev_key]
            total_data = Basic_stats_seasons[total_key]
            ev_percentiles = percentile_seasons[ev_percentile_key]
            total_percentiles = percentile_seasons[total_percentile_key]

            if ev_data:
                for k, v in ev_data[0].items():
                    if isinstance(v, (int, float)):
                        if isinstance(v, float) and 0 < v < 1:
                            ev_total[k] = ev_total.get(k, 0) + v
                            ev_counts[k] = ev_counts.get(k, 0) + 1
                        else:
                            ev_total[k] = ev_total.get(k, 0) + v

                # Calculate average percentile for each stat in `ev_percentiles`
                for key in ev_percentiles.keys():
                    if isinstance(ev_percentiles[key], (int, float, Decimal)):
                        ev_percentiles_total[key] = float(ev_percentiles_total.get(key, 0)) + float(ev_percentiles[key])

            if total_data:
                for k, v in total_data[0].items():
                    if isinstance(v, (int, float)):
                        if isinstance(v, float) and 0 < v < 1:
                            non_ev_total[k] = non_ev_total.get(k, 0) + v
                            non_ev_counts[k] = non_ev_counts.get(k, 0) + 1
                        else:
                            non_ev_total[k] = non_ev_total.get(k, 0) + v

                # Calculate average percentile for each stat in `total_percentiles`
                for key in total_percentiles.keys():
                    if isinstance(total_percentiles[key], (int, float, Decimal)):
                        non_ev_percentiles_total[key] = float(non_ev_percentiles_total.get(key, 0)) + float(total_percentiles[key])

    ev_total["xgoals_on_ice_for_per_60"] = ev_total.get('OnIce_F_xGoals', 0) / (ev_total.get('ICETIME', 0) / 3600) if ev_total.get('ICETIME', 0) > 0 else 0
    ev_total["xgoals_on_ice_against_per_60"] = (ev_total.get('OnIce_A_xGoals', 0) / (ev_total.get('ICETIME', 0) / 3600)) if ev_total.get('ICETIME', 0) > 0 else 0

    # Additional stats
    ev_total["shooting_percentage"] = (ev_total.get("I_F_goals", 0) / ev_total.get("I_F_shotsOnGoal", 1)) if ev_total.get("I_F_shotsOnGoal", 0) > 0 else 0
    ev_total["goals_per_xg"] = ev_total.get("I_F_goals", 0) / ev_total.get("I_F_xGoals", 1) if ev_total.get("I_F_xGoals", 0) > 0 else 0


    non_ev_total["shooting_percentage"] = (non_ev_total.get("I_F_goals", 0) / non_ev_total.get("I_F_shotsOnGoal", 1)) if non_ev_total.get("I_F_shotsOnGoal", 0) > 0 else 0
    non_ev_total["goals_per_xg"] = non_ev_total.get("I_F_goals", 0) / non_ev_total.get("I_F_xGoals", 1) if non_ev_total.get("I_F_xGoals", 0) > 0 else 0

    if len(season) == 0:
        for key in total_percentiles.keys():
            non_ev_percentiles_total[key] = non_ev_percentiles_total.get(key, 0)/valid_seasons
        
        for key in ev_percentiles.keys():
            ev_percentiles_total[key] = ev_percentiles_total.get(key, 0)/valid_seasons
    else:
        for key in ev_percentiles_total.keys():
            ev_percentiles_total[key] = ev_percentiles_total.get(key, 0) / len(season)
            
        for key in total_percentiles.keys():
            non_ev_percentiles_total[key] = non_ev_percentiles_total.get(key, 0)/len(season)        # Now average the ratio values
    for k in ev_counts:
        if ev_counts[k] > 0:
            ev_total[k] /= ev_counts[k]

    for k in non_ev_counts:
        if non_ev_counts[k] > 0:
            non_ev_total[k] /= non_ev_counts[k]


    print(Basic_stats_seasons)
    # Display core stats on the matplotlib figure
    fig, ax = plt.subplots(figsize=(10, 8))
    plt.axis('off')
        
    # Load headshot
    headshot = load_image_from_url(headshot_url)

    # # Convert SVG to PNG if needed using cairosvg (install with pip install cairosvg)
    # team_logo_png = BytesIO()
    # cairosvg.svg2png(url=team_logo_url, write_to=team_logo_png)
    # team_logo = Image.open(team_logo_png)
    # Add headshot
    ax_headshot = fig.add_axes([0.05, 0.75, 0.2, 0.2]) # [left, bottom, width, height]
    ax_headshot.imshow(headshot)
    ax_headshot.axis('off')

    # # Add team logo
    # ax_logo = fig.add_axes([0.5, 0.4, 0.15, 0.5])
    # ax_logo.imshow(team_logo)
    # ax_logo.axis('off')

    # Add player name
    fig.text(0.05, 0.72, player_name, fontsize=14, fontweight='bold', ha='left')
    if len(season) == 0:
        fig.text(0.05, 0.7, f"Career Stats", fontsize=8, ha='left')
    elif len(season) == 1:
        next_season = int(season[0]) + 1
        display_season = f"{season[0]}-{str(next_season)[2:]}"
        fig.text(0.05, 0.7, f"{display_season} Season", fontsize=8, ha='left')
    else: 
        next_season = int(season[0]) + 1
        display_first_season = f"{season[0]}-{str(next_season)[2:]}"
        next_season = int(season[-1]) + 1
        display_last_season = f"{season[-1]}-{str(next_season)[2:]}"
        fig.text(0.05, 0.7, f"{display_first_season} - {display_last_season} Seasons", fontsize=8, ha='left')

    #Print out total games played and time on ice.
    games_played = ev_total.get('GAMES_PLAYED', 0)
    avg_toi = (non_ev_total.get('ICETIME', 0)) / games_played if games_played > 0 else 0

    minutes = int(avg_toi // 60)  # Get the whole minutes
    seconds = int(avg_toi % 60)   # Get the remaining seconds

    # Format as 'minutes:seconds'
    formatted_toi = f"{minutes}:{seconds:02d}"
    fig.text(0.05, 0.68, f"GP: {games_played}", fontsize=8, ha='left')
    fig.text(0.05, 0.66, f"TOI: {formatted_toi}", fontsize=8, ha='left')
    # Assuming birthDate is in the format "YYYY-MM-DD"
    birth_date = datetime.strptime(birthDate, "%Y-%m-%d")
    current_date = datetime.now()

    # Calculate age
    age = current_date.year - birth_date.year - ((current_date.month, current_date.day) < (birth_date.month, birth_date.day))


    feet = heightInches // 12
    inches = heightInches % 12

# Create feet_height variable
    feet_height = f"{feet} {inches}'"

    ax.text(0.8, 1.04, f"Number: #{sweaterNumber}", fontsize=12, ha='left')
    ax.text(0.8, 1.00, f"Position: {position}", fontsize=12, ha='left')
    ax.text(0.8, 0.96, f"Age: {age}", fontsize=12, ha='left')
    ax.text(0.8, 0.92, f"Born: {birthCountry}", fontsize=12, ha='left')
    ax.text(0.8, 0.88, f"Height: {feet_height}", fontsize=12, ha='left')
    ax.text(0.8, 0.84, f"Weight: {weightInPounds} lbs", fontsize=12, ha='left')
    ax.text(0.8, 0.80, f"Shoots: {shootsCatches}", fontsize=12, ha='left')

    if len(season) == 1:
        percentile_string = "Percentile: "
    else:
        percentile_string = "Avg Percentile: "


    ax.text(-0.1, 0.65, "Totals", fontsize=14, fontweight='bold', ha='left')
    stats_to_display = [
        "Goals", "Assists", "Points", "xGoals%", "Shots", "Shooting%", "Primary Assists","Individual XG", "Goals/XG", "Takeaways", "Hits", "Blocked Shots"
    ]
    stats_values = ["I_F_goals", "I_F_primaryAssists", "I_F_points", "onIce_xGoalsPercentage", "I_F_shotsOnGoal", "shooting_percentage", "I_F_primaryAssists", "I_F_xGoals", 
                    "goals_per_xg", "I_F_takeaways", "I_F_hits", "shotsBlockedByPlayer"]
    percentile_values = ["goals_per_60_percentile", "assists_per_60_percentile","points_per_60_percentile", "onIce_xGoalsPercentage_percentile", "shotsOnGoal_per_60_percentile",
                          "shooting_percentage_percentile", "primary_assists_per_60_percentile",
                          "I_F_xGoals_per_60_percentile", "goals_per_xg_percentile", "takeaways_per_60_percentile", "hits_per_60_percentile", "shotsBlockedByPlayer_per_60_percentile"]
    x_value = 0.0  # Starting x position for the stats
    y_value = 0.55  # Starting y position for the stats
    for i in range (len(stats_to_display)):
        ax.text(x_value, y_value + 0.05, stats_to_display[i], fontsize=12, ha='center', va='center')
                # Draw the box with the number of goals inside it
        if stats_to_display[i] == "Assists":
            stat_num = non_ev_total.get('I_F_points', 0) - ev_total.get('I_F_goals', 0)
        else:
            stat_num = non_ev_total.get(stats_values[i], 0)
        if stats_to_display[i] == "xGoals%" or stats_to_display[i] == "Shooting%":
            stat_num = stat_num * 100
            stat_text = f"{stat_num:.0f}%"
        elif stats_to_display[i] == "Individual XG" or stats_to_display[i] == "Goals/XG":
            stat_text = f"{stat_num:.2f}"
        else:
            stat_text = f"{stat_num:.0f}"

        box_color = get_box_color(non_ev_percentiles_total.get(percentile_values[i], 0))
        ax.text(x_value, y_value, stat_text, fontsize=12, ha='center', va='center', 
                bbox=dict(facecolor=box_color, edgecolor='black', boxstyle='round,pad=0.3'))

        # Display the percentile below the box
        percentile_text = f"{percentile_string} {non_ev_percentiles_total.get(percentile_values[i], 0):.2f}%"
        ax.text(x_value, y_value-0.05, percentile_text, fontsize=8, ha='center', va='center')
        x_value += 0.2
        if x_value > 1.0:
            x_value = 0.0
            y_value -= 0.15
    # Display "5 on 5 Stats" at the top
    x_value = 0.0  # Reset x position for the next row of stats
    ax.text(-0.1, y_value, "5 on 5 Stats", fontsize=14, fontweight='bold', ha='left')
    y_value -= 0.1  # Move down for the next row of stats
    stats_to_display = [
        "Goals", "Assists", "Points", "xGoals%", "Shots", "Shooting%", "xGoals For/60", "xGoals Against/60", "Offense Impact", "Defense Impact", "Individual XG", "Goals/XG"
    ]
    stats_values = ["I_F_goals", "I_F_primaryAssists", "I_F_points", "onIce_xGoalsPercentage", "I_F_shotsOnGoal", "shooting_percentage", "xgoals_on_ice_for_per_60",
                     "xgoals_on_ice_against_per_60", "Offense_impact_percentile", "Defense_impact_percentile", "I_F_xGoals", "goals_per_xg"]
    percentile_values = ["goals_per_60_percentile", "assists_per_60_percentile","points_per_60_percentile","onIce_xGoalsPercentage_percentile", "shotsOnGoal_per_60_percentile",
                          "shooting_percentage_percentile", "OnIce_F_xGoals_per_60_percentile", "OnIce_A_xGoals_per_60_percentile", "Offense_impact_percentile", "Defense_impact_percentile",
                          "I_F_xGoals_per_60_percentile", "goals_per_xg_percentile"]

    for i in range (len(stats_to_display)):
        ax.text(x_value, y_value + 0.05, stats_to_display[i], fontsize=12, ha='center', va='center')
                # Draw the box with the number of goals inside it
        if stats_to_display[i] == "Assists":
            stat_num = ev_total.get('I_F_points', 0) - ev_total.get('I_F_goals', 0)
        elif stats_to_display[i] == "Offense Impact" or stats_to_display[i] == "Defense Impact":
            stat_num = ev_percentiles.get(stats_values[i], 0)
        else:
            stat_num = ev_total.get(stats_values[i], 0)
        if stats_to_display[i] == "xGoals%" or stats_to_display[i] == "Shooting%":
            stat_num = stat_num * 100
            stat_text = f"{stat_num:.0f}%"
        elif stats_to_display[i] == "Offense Impact" or stats_to_display[i] == "Defense Impact":
            stat_text = f"{stat_num:.1f}%"
        elif stats_to_display[i] == "Goals" or stats_to_display[i] == "Points" or stats_to_display[i] == "Shots" or stats_to_display[i] == "Assists":
            stat_text = f"{stat_num:.0f}"
        else:
            stat_text = f"{stat_num:.2f}"

        box_color = get_box_color(ev_percentiles_total.get(percentile_values[i], 0))
        ax.text(x_value, y_value, stat_text, fontsize=12, ha='center', va='center', 
                bbox=dict(facecolor=box_color, edgecolor='black', boxstyle='round,pad=0.3'))
        
        # Display the percentile below the box
        if stats_to_display[i] != "Offense Impact" and stats_to_display[i] != "Defense Impact":
            percentile_text = f"{percentile_string} {ev_percentiles_total.get(percentile_values[i], 0):.2f}%"
            ax.text(x_value, y_value-0.05, percentile_text, fontsize=8, ha='center', va='center')
        else: 
            percentile_text = f"Already in Percentile"
            ax.text(x_value, y_value-0.05, percentile_text, fontsize=8, ha='center', va='center')
        x_value += 0.2
        if x_value > 1.0:
            x_value = 0.0
            y_value -= 0.15

    return fig

# db = init_db(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE)

# fetch_player_card(db, "Simon Benoit", [2023])
        


