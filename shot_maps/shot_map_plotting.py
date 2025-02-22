import pandas as pd
# import numpy as np
# from scipy.interpolate import griddata
# from scipy.ndimage import gaussian_filter
import matplotlib.pyplot as plt
from hockey_rink import NHLRink
import urllib.request
import urllib.error
import hockey_rink.rink_feature
hockey_rink.rink_feature.urllib = urllib  # Force the module to use correct imports


def extract_shot_data(player_name, season, situation, shot_result, season_type):
    """
    Extracts shot data for a given player, season, situation, and shot result type

    :param player_name: str, name of the NHL player to extract data for
    :param season: int, season to extract data for (YYYY)
    :param situation: str, game situation to extract data for, between the following options (5on5, 5on4, 4on5, all, other)
    :param shot_result: str, type of shot result to extract data for, between the following options (GOAL, SOG_OR_GOAL, ANY)
    :param season_type: str, type of season to extract data for, between the following options (regular, playoffs, all)
    :return: pd.DataFrame, filtered shot data for the given player, season, situation, and shot result type
    """
    # TODO: Segment player data into seasons to make CSV reading faster?
    # TODO: Experiment with order of filtering on CSV to optimize speed? Will this be different when using a database?
    shot_data = pd.read_csv('data\shots\shots_2015-2023.csv')

    # Assertions to validate input
    # TODO: How will these assertions be routed with the LLM? if they fail? Are they necessary?
    # TODO: Make global variable to store the possible values for the season param, since this will be used elsewhere
    assert player_name in shot_data['shooterName'].unique(), f"Player {player_name} not found in data"
    assert season in [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023], f"Season {season} not found in data"
    assert situation in ['5on5', '5on4', '4on5', 'all', 'other'], f"Situation {situation} not found in data"
    assert shot_result in ['GOAL', 'SOG_OR_GOAL', 'ANY'], f"Event type {shot_result} not found in data"
    assert season_type in ['all', 'regular', 'playoffs'], f"Season type {season_type} not found in data"

    # Filter data based on input 
    shot_data = shot_data[shot_data['shooterName'] == player_name]
    shot_data = shot_data[shot_data['season'] == season]

    # NOTE: Excluding shots from behind half
    shot_data = shot_data[shot_data['xCordAdjusted'] <= 89]

    if season_type == 'regular':
        shot_data = shot_data[shot_data['isPlayoffGame'] == 0]
    elif season_type == 'playoffs':
        shot_data = shot_data[shot_data['isPlayoffGame'] == 1]
    # For the else, no need to filter for season_type='full'

    # shot_result filtering
    if shot_result == 'GOAL':
        shot_data = shot_data[shot_data['event'] == "GOAL"]
    elif shot_result == 'SOG_OR_GOAL':
        shot_data = shot_data[shot_data['event'].isin(["GOAL", "SHOT"])]
    # For the else, no need to filter for shot_result='ANY'

    if situation == '5on5':
        shot_data = shot_data[(shot_data['awaySkatersOnIce'] == 5) & (shot_data['homeSkatersOnIce'] == 5)]
    elif situation == '5on4':
        shot_data = shot_data.loc[
            ((shot_data['isHomeTeam'] == 1) & (shot_data['awaySkatersOnIce'] == 4) & (shot_data['homeSkatersOnIce'] == 5)) |
            ((shot_data['isHomeTeam'] == 0) & (shot_data['awaySkatersOnIce'] == 5) & (shot_data['homeSkatersOnIce'] == 4))
        ]
    elif situation == '4on5':
        shot_data = shot_data.loc[
            ((shot_data['isHomeTeam'] == 1) & (shot_data['awaySkatersOnIce'] == 5) & (shot_data['homeSkatersOnIce'] == 4)) |
            ((shot_data['isHomeTeam'] == 0) & (shot_data['awaySkatersOnIce'] == 4) & (shot_data['homeSkatersOnIce'] == 5))
        ]
    elif situation == 'other': # Other situations are the inverse of 5on5, and both 5on4, and 4on5 versions
        shot_data = shot_data.loc[~(
            ((shot_data['awaySkatersOnIce'] == 5) & (shot_data['homeSkatersOnIce'] == 5)) |  # 5on5
            ((shot_data['isHomeTeam'] == 1) & (shot_data['awaySkatersOnIce'] == 4) & (shot_data['homeSkatersOnIce'] == 5)) |  # 5on4
            ((shot_data['isHomeTeam'] == 0) & (shot_data['awaySkatersOnIce'] == 5) & (shot_data['homeSkatersOnIce'] == 4)) |  # 5on4
            ((shot_data['isHomeTeam'] == 1) & (shot_data['awaySkatersOnIce'] == 5) & (shot_data['homeSkatersOnIce'] == 4)) |  # 4on5
            ((shot_data['isHomeTeam'] == 0) & (shot_data['awaySkatersOnIce'] == 4) & (shot_data['homeSkatersOnIce'] == 5))    # 4on5
        )]
    # For the else, no need to filter for situation='all'

    # NOTE: Excluding empty net shots
    shot_data = shot_data[shot_data['shotOnEmptyNet'] == 0] # Exclude empty net

    # TODO: Remove unnecessary columns from the DataFrame to reduce memory usage?
    return shot_data


def goal_map_scatter_get(player_name, season, situation, season_type):
    """
    Generates a scatter plot of a player's goals on a hockey rink, excluding empty net goals and shots from behind half
    :param player_name: str, name of the NHL player to extract data for
    :param situation: str, game situation to extract data for, between the following options (5on5, 5on4, 4on5, all, other)
    :param season: int, season to extract data for (YYYY)
    :param season_type: str, type of season to extract data for, between the following options (regular, playoffs, all)
    """
    player_shots = extract_shot_data(player_name, season, situation, shot_result="GOAL", season_type=season_type)
    # TODO: Defensive programming if no goals are found for the player in the given season/situation???

    fig, ax = plt.subplots(1,1, figsize=(10,12), facecolor='w', edgecolor='k')
    
    rink = NHLRink(net={"visible": False})

    # TODO Include plot title? Player photo? Team logo?
    scatter = rink.scatter(
        "xCordAdjusted", "yCordAdjusted", data=player_shots,
        plot_range="offense", s=100, alpha=0.7, plot_xlim=(0, 89), color="orange",
        ax=ax, draw_kw={"display_range": "offense"},
    )

    # Title for the figure
    fig.suptitle(f"{player_name} {season} Season {situation} Goals", fontsize=16)
    # TODO: better title formatting based on possible input fields. EG other, playoffs, etc. Maybe goal count?

    plt.show()
    # TODO: Return type? Image or plot object?


# TODO: Add a function for better flow control. There is duplication between the shot map and goal map plotting functions
def shot_map_scatter(player_name, season, situation, season_type):
    """
    Generates a scatter plot of a player's shots and goals on a hockey rink, excluding empty net shots and shots from behind half
    :param player_name: str, name of the NHL player to extract data for
    :param situation: str, game situation to extract data for, between the following options (5on5, 5on4, 4on5, all, other)
    :param season: int, season to extract data for (YYYY)
    :param season_type: str, type of season to extract data for, between the following options (regular, playoffs, all)
    """
    player_shots = extract_shot_data(player_name, season, situation, shot_result="SOG_OR_GOAL", season_type=season_type)

    fig, ax = plt.subplots(1,1, figsize=(10,12), facecolor='w', edgecolor='k')
    
    rink = NHLRink(net={"visible": False})

    # Plotting shots and goals in different colors
    # NOTE: Colour mapping is not working.
    player_shots = (player_shots.assign(color=lambda df_: df_.event.map({"SHOT": "grey", "GOAL": "orange"})))

    # TODO Include plot title? Player photo? Team logo?
    scatter = rink.scatter(
        "xCordAdjusted", "yCordAdjusted", color="color", data=player_shots,
        plot_range="offense", s=100, alpha=0.7, plot_xlim=(0, 89),
        ax=ax, draw_kw={"display_range": "offense"},
    )

    # Title for the figure
    fig.suptitle(f"{player_name} {season} Season {situation} Shots (Grey) and Goals (Orange)", fontsize=16)
    # TODO: better title formatting based on possible input fields. EG other, playoffs, etc. Maybe goal count?

    plt.show()


# TODO: Include heatmaps in this file

# Sample function calls
# if __name__ == "__main__":
    # goal_map_scatter("Auston Matthews", 2021, "5on5", "regular")
    # shot_map_scatter("Auston Matthews", 2021, "5on5", "regular")
    # goal_map_scatter("Auston Matthews", 2022, "5on4", "playoffs")
    # goal_map_scatter("Travis Konecny", 2023, "4on5", "all")
    # goal_map_scatter("Connor McDavid", 2022, "all", "all")
    # goal_map_scatter("Auston Matthews", 2022, "other", "all")

#goal_map_scatter_get("Auston Matthews", 2021, "5on5", "regular")
