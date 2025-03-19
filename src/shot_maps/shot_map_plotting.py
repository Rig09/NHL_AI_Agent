import pandas as pd
import matplotlib.pyplot as plt
from hockey_rink import NHLRink
import urllib.request
import urllib.error
import hockey_rink.rink_feature
hockey_rink.rink_feature.urllib = urllib  # Force the module to use correct imports
import os
from utils.database_init import run_query_mysql, init_db
from chains.stats_sql_chain import get_sql_chain
from langchain_openai import ChatOpenAI
from openai import OpenAI 
import numpy as np

def extract_shot_data(db, api_key, llm, conditions, season_lower_bound, season_upper_bound, situation, season_type, shot_result):
    """
    Extracts shot data for a given natural language description of conditions, season upper and lower bounds, situation, and shot result type
    """
    sql_chain = get_sql_chain(db, api_key, llm)
    # Validate input parameters
    valid_situations = ['5on5', '5on4', '4on5', 'all', 'other']
    valid_shot_results = ['GOAL', 'SOG_OR_GOAL', 'ANY']
    valid_season_types = ['all', 'regular', 'playoffs']

    if situation not in valid_situations:
        raise ValueError(f"Situation {situation} not found in data")
    if shot_result not in valid_shot_results:
        raise ValueError(f"Event type {shot_result} not found in data")
    if season_type not in valid_season_types:
        raise ValueError(f"Season type {season_type} not found in data")

    # Define the query with filtering based on input, using season_lower_bound and season_upper_bound
    # query = f"""
    # SELECT * 
    # FROM shots_data
    # WHERE shooterName = '{player_name}' 
    # AND season >= {season_lower_bound}
    # AND season <= {season_upper_bound}
    # """
    template_for_sql_query = f"""return from the shots_data table with all of the columns in the table  intact, Given the conditions: {conditions}, In the seasons between {season_lower_bound} to {season_upper_bound}. For this query please use the {situation} situation and the {season_type} season type.
                                Return the list of shots so they can be put into a dataframe. An example query for the player Morgan Rielly between 2020 and 2023 seasons would be: SELECT * FROM SHOTS_DATA WHERE SEASON <=2023 AND SEASON >= 2020 AND  shooterName='Morgan Rielly'. 
                                Also note to find the team of a shot, compare home team with is_home the attribute."""
    
    query = sql_chain.invoke({"question" : template_for_sql_query})
    shot_data = pd.DataFrame(run_query_mysql(query, db))
    if shot_data.empty:
        raise ValueError("There was an error with the query. Please try again with a different query.")
    # Filter for the player name
    # shot_data = shot_data[shot_data['shooterName'] == player_name]

    # # Filter for season range
    # shot_data = shot_data[(shot_data['season'] >= season_lower_bound) & (shot_data['season'] <= season_upper_bound)]

    # NOTE: Excluding shots from behind half
    shot_data = shot_data[shot_data['xCordAdjusted'] <= 89]

    # Season type filtering
    if season_type == 'regular':
        shot_data = shot_data[shot_data['isPlayoffGame'] == 0]
    elif season_type == 'playoffs':
        shot_data = shot_data[shot_data['isPlayoffGame'] == 1]
    # No filtering needed if season_type is 'all'
    # Season type filtering
    if season_type == 'regular':
        shot_data = shot_data[shot_data['isPlayoffGame'] == 0]
    elif season_type == 'playoffs':
        shot_data = shot_data[shot_data['isPlayoffGame'] == 1]
    # No filtering needed if season_type is 'all'


    # Shot result filtering
    if shot_result == 'GOAL':
        shot_data = shot_data[shot_data['event'] == "GOAL"]
    elif shot_result == 'SOG_OR_GOAL':
        shot_data = shot_data[shot_data['event'].isin(["GOAL", "SHOT"])]
    # No filtering needed if shot_result is 'ANY'

    # Situation filtering
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
    elif situation == 'other':  # Inverse of 5on5, 5on4, 4on5
        shot_data = shot_data.loc[~(
            ((shot_data['awaySkatersOnIce'] == 5) & (shot_data['homeSkatersOnIce'] == 5)) |
            ((shot_data['isHomeTeam'] == 1) & (shot_data['awaySkatersOnIce'] == 4) & (shot_data['homeSkatersOnIce'] == 5)) |
            ((shot_data['isHomeTeam'] == 0) & (shot_data['awaySkatersOnIce'] == 5) & (shot_data['homeSkatersOnIce'] == 4)) |
            ((shot_data['isHomeTeam'] == 1) & (shot_data['awaySkatersOnIce'] == 5) & (shot_data['homeSkatersOnIce'] == 4)) |
            ((shot_data['isHomeTeam'] == 0) & (shot_data['awaySkatersOnIce'] == 4) & (shot_data['homeSkatersOnIce'] == 5))
        )]
    # No filtering needed if situation is 'all'

    # Exclude empty net shots
    shot_data = shot_data[shot_data['shotOnEmptyNet'] == 0]  # Exclude empty net shots

    # Drop unnecessary columns if needed (e.g., 'id', 'event' or other non-essential columns)
    shot_data = shot_data.drop(columns=['id'])  # example column removal

    return shot_data


def goal_map_scatter_get(db, api_key, llm, conditions, season_lower_bound, season_upper_bound, situation, season_type):
    """
    Generates a scatter plot of a player's goals on a hockey rink, excluding empty net goals and shots from behind half
    :param conditions: str, Natural language conditions to filter the data
    :param season_lower_bound: int, the lower bound to filter the season data 
    :param season_upper_bound: int, the upper bound to filter the season data
    :param situation: str, game situation to extract data for, between the following options (5on5, 5on4, 4on5, all, other)
    :param season_type: str, type of season to extract data for, between the following options (regular, playoffs, all)
    :returns: matplotlib figure object
    """
    player_shots = extract_shot_data(db, api_key, llm, conditions, season_lower_bound, season_upper_bound, situation, shot_result="GOAL", season_type=season_type)
    # TODO: Defensive programming if no goals are found for the player in the given season/situation???

    fig, ax = plt.subplots(1,1, figsize=(10,12), facecolor='w', edgecolor='k')
    
    rink = NHLRink(net={"visible": False})

    scatter = rink.scatter(
        "xCordAdjusted", "yCordAdjusted", data=player_shots,
        plot_range="offense", s=100, alpha=0.7, plot_xlim=(0, 89), color="orange",
        ax=ax, draw_kw={"display_range": "offense"},
    )

    goal_count = (player_shots['event'] == 'GOAL').sum()
    ax.text(-0.05, 1.05, f"Total Goals: {goal_count}", 
            transform=ax.transAxes, fontsize=12, verticalalignment='top', 
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

    caption = llm.invoke(
    f"""Return a figure caption for a scatterplot of goals that was made based on the following criteria: '{conditions}', in the seasons between {season_lower_bound} to {season_upper_bound}, 
    in the {situation} situation, and in the {season_type} season type. Provide only the caption, no extra information. DO not include the figure number. For example 'Figure 1:' Do not include that."""
    ).content

    # Title for the figure
    # if season_lower_bound == season_upper_bound:
    #     fig.suptitle(f"{season_lower_bound}-{season_lower_bound + 1} Season {situation} Goals", fontsize=16)
    # else:
    #     fig.suptitle(f"{season_lower_bound}-{season_lower_bound+1} to {season_upper_bound}- {season_upper_bound+1} Seasons {situation} Goals", fontsize=16)    
    fig.suptitle(caption, fontsize=16)
    return fig
    

def shot_map_scatter_get(db, api_key, llm, conditions, season_lower_bound, season_upper_bound, situation, season_type):
    """
    Generates a scatter plot of a player's shots and goals on a hockey rink, excluding empty net shots and shots from behind half
    :param conditions: str, Natural language conditions to filter the data
    :param season_lower_bound: int, the lower bound to filter the season data 
    :param season_upper_bound: int, the upper bound to filter the season data
    :param situation: str, game situation to extract data for, between the following options (5on5, 5on4, 4on5, all, other)
    :param season_type: str, type of season to extract data for, between the following options (regular, playoffs, all)
    :returns: matplotlib figure object
    """
    player_shots = extract_shot_data(db, api_key, llm, conditions, season_lower_bound, season_upper_bound, situation, shot_result="SOG_OR_GOAL", season_type=season_type)

    fig, ax = plt.subplots(1,1, figsize=(10,12), facecolor='w', edgecolor='k')
    
    rink = NHLRink(net={"visible": False})

    # Plotting shots and goals in different colors
    # NOTE: Colour mapping is not working.
    player_shots = (player_shots.assign(color=lambda df_: df_.event.map({"SHOT": "grey", "GOAL": "orange"})))

    scatter = rink.scatter(
        "xCordAdjusted", "yCordAdjusted", color=player_shots['color'], data=player_shots,
        plot_range="offense", s=100, alpha=0.7, plot_xlim=(0, 89),
        ax=ax, draw_kw={"display_range": "offense"}
    )

    # Add legend (moved up and to the right)
    ax.scatter([], [], color='grey', s=100, label='Shot')
    ax.scatter([], [], color='orange', s=100, label='Goal')
    ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.05), fontsize=12)

    # Calculate and display totals (moved up and to the left)
    goal_count = (player_shots['event'] == 'GOAL').sum()
    shot_count = goal_count + (player_shots['event'] == 'SHOT').sum()
    ax.text(-0.05, 1.05, f"Total Shots: {shot_count}\nTotal Goals: {goal_count}", 
            transform=ax.transAxes, fontsize=12, verticalalignment='top', 
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))
    # # Title for the figure
    # if season_lower_bound == season_upper_bound:
    #     fig.suptitle(f"{season_lower_bound}-{season_lower_bound + 1} Season {situation} Shots (Grey) and Goals (Orange)", fontsize=16)
    # else:
    #     fig.suptitle(f"{season_lower_bound}-{season_lower_bound + 1} Season {situation} Shots (Grey) and Goals (Orange)", fontsize=16)

    caption = llm.invoke(
    f"""Return a figure caption for a scatterplot of goals that was made based on the following criteria: '{conditions}', in the seasons between {season_lower_bound} to {season_upper_bound}, 
    in the {situation} situation, and in the {season_type} season type. Provide only the caption, no extra information. DO not include the figure number. For example 'Figure 1:' Do not include that."""
    ).content

    fig.suptitle(caption, fontsize=16)

    return fig




# TODO: Include heatmaps in this file
def shot_heat_map_get(db, api_key, llm, conditions, season_lower_bound, season_upper_bound, situation, season_type):
    """
    Generates a heatmap of a shots on a hockey rink, given an input query.
    :param conditions: str, Natural language conditions to filter the data
    :param season_lower_bound: int, the lower bound to filter the season data 
    :param season_upper_bound: int, the upper bound to filter the season data
    :param situation: str, game situation to extract data for, between the following options (5on5, 5on4, 4on5, all, other)
    :param season_type: str, type of season to extract data for, between the following options (regular, playoffs, all)
    :returns: matplotlib figure object
    """
    player_shots = extract_shot_data(db, api_key, llm, conditions, season_lower_bound, season_upper_bound, situation, shot_result="SOG_OR_GOAL", season_type=season_type)

    fig, ax = plt.subplots(1,1, figsize=(10,12), facecolor='w', edgecolor='k')
    
    rink = NHLRink(net={"visible": False})

    # Plotting shots and goals in different colors
    # NOTE: Colour mapping is not working.
    hist, xedges, yedges = np.histogram2d(
    player_shots["xCordAdjusted"], player_shots["yCordAdjusted"], bins=10
    )

    contour = rink.contourf(
        "xCordAdjusted", "yCordAdjusted", hist.T, data=player_shots, 
        cmap="bwr", alpha=0.8, plot_xlim=(0, 89),
        plot_range="offense", ax=ax, draw_kw={"display_range": "offense"}
    )
    
    cbar = fig.colorbar(contour, ax=ax, orientation="horizontal")
    cbar.set_label("Number of Shots")

    caption = llm.invoke(
    f"""Return a figure caption for a heatmap of all shots that was made based on the following criteria: '{conditions}', in the seasons between {season_lower_bound} to {season_upper_bound}, 
    in the {situation} situation, and in the {season_type} season type. Provide only the caption, no extra information. DO not include the figure number. For example 'Figure 1:' Do not include that."""
    ).content

    fig.suptitle(caption, fontsize=16)

    return fig

# TODO: Include heatmaps in this file
def goal_heat_map_get(db, api_key, llm, conditions, season_lower_bound, season_upper_bound, situation, season_type):
    """
    Generates a heatmap of a goals on a hockey rink, given an input query.
    :param conditions: str, Natural language conditions to filter the data
    :param season_lower_bound: int, the lower bound to filter the season data 
    :param season_upper_bound: int, the upper bound to filter the season data
    :param situation: str, game situation to extract data for, between the following options (5on5, 5on4, 4on5, all, other)
    :param season_type: str, type of season to extract data for, between the following options (regular, playoffs, all)
    :returns: matplotlib figure object
    """
    player_shots = extract_shot_data(db, api_key, llm, conditions, season_lower_bound, season_upper_bound, situation, shot_result="GOAL", season_type=season_type)

    fig, ax = plt.subplots(1,1, figsize=(10,12), facecolor='w', edgecolor='k')
    
    rink = NHLRink(net={"visible": False})

    # Plotting shots and goals in different colors
    # NOTE: Colour mapping is not working.
    hist, xedges, yedges = np.histogram2d(
    player_shots["xCordAdjusted"], player_shots["yCordAdjusted"], bins=10
    )

    contour = rink.contourf(
        "xCordAdjusted", "yCordAdjusted", hist.T, data=player_shots, 
        cmap="bwr", alpha=0.8, plot_xlim=(0, 89),
        plot_range="offense", ax=ax, draw_kw={"display_range": "offense"}
    )

    cbar = fig.colorbar(contour, ax=ax, orientation="horizontal")
    cbar.set_label("Number of Goals")

    caption = llm.invoke(
    f"""Return a figure caption for a heatmap of all goals that was made based on the following criteria: '{conditions}', in the seasons between {season_lower_bound} to {season_upper_bound}, 
    in the {situation} situation, and in the {season_type} season type. Provide only the caption, no extra information. DO not include the figure number. For example 'Figure 1:' Do not include that."""
    ).content

    fig.suptitle(caption, fontsize=16)

    return fig

def xg_heat_map_get(db, api_key, llm, conditions, season_lower_bound, season_upper_bound, situation, season_type):
    """
    Generates a heatmap of a shots on a hockey rink, given an input query.
    :param conditions: str, Natural language conditions to filter the data
    :param season_lower_bound: int, the lower bound to filter the season data 
    :param season_upper_bound: int, the upper bound to filter the season data
    :param situation: str, game situation to extract data for, between the following options (5on5, 5on4, 4on5, all, other)
    :param season_type: str, type of season to extract data for, between the following options (regular, playoffs, all)
    :returns: matplotlib figure object
    """
    player_shots = extract_shot_data(db, api_key, llm, conditions, season_lower_bound, season_upper_bound, situation, shot_result="SOG_OR_GOAL", season_type=season_type)

    fig, ax = plt.subplots(1,1, figsize=(10,12), facecolor='w', edgecolor='k')
    
    rink = NHLRink(net={"visible": False})

    fig, ax = plt.subplots(1,1, figsize=(10,12), facecolor='w', edgecolor='k')

    rink = NHLRink(net={"visible": False})

    contour = rink.contourf(
        "xCordAdjusted", "yCordAdjusted", "xGoal", data=player_shots, 
        nbins=8, levels=30, plot_range="offense", cmap="bwr", alpha=0.8, plot_xlim=(0, 89),
        ax=ax, draw_kw={"display_range": "offense"}
    )

    # Add colorbar
    cbar = fig.colorbar(contour, ax=ax, orientation="horizontal")
    cbar.set_label("Average XG")

    caption = llm.invoke(
    f"""Return a figure caption for a heatmap of expected goals that was made based on the following criteria: '{conditions}', in the seasons between {season_lower_bound} to {season_upper_bound}, 
    in the {situation} situation, and in the {season_type} season type. Provide only the caption, no extra information. DO not include the figure number. For example 'Figure 1:' Do not include that."""
    ).content

    fig.suptitle(caption, fontsize=16)

    return fig