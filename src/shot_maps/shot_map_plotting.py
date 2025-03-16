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


def extract_shot_data(db, api_key, conditions, season_lower_bound, season_upper_bound, situation, shot_result, season_type):
    """
    Extracts shot data for a given player, season, situation, and shot result type
    """
    sql_chain = get_sql_chain(db, api_key)
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

    template_for_sql_query = f"""return from the shots_data table with all of the columns in the table  intact, Given the conditions: {conditions}, In the seasons between {season_lower_bound} to {season_upper_bound},
                                Return the list of shots so they can be put into a dataframe. An example query for the player Morgan Rielly between 2020 and 2023 seasons would be: SELECT * FROM SHOTS_DATA WHERE SEASON <=2023 AND SEASON >= 2020 AND  shooterName='Morgan Rielly'. 
                                Also note to find the team of a shot, compare home team with is_home the attribute."""
                
    query = sql_chain.invoke({"question" : template_for_sql_query})
    print('query:')
    print(query)
    shot_data = pd.DataFrame(run_query_mysql(query, db))
    print(shot_data.head(5))
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

    # Shot result filtering
    if shot_result == 'GOAL':
        shot_data = shot_data[shot_data['event'] == "GOAL"]
    elif shot_result == 'SOG_OR_GOAL':
        shot_data = shot_data[shot_data['event'].isin(["GOAL", "SHOT"])]
    # No filtering needed if shot_result is 'ANY'

    # # Situation filtering
    # if situation == '5on5':
    #     shot_data = shot_data[(shot_data['awaySkatersOnIce'] == 5) & (shot_data['homeSkatersOnIce'] == 5)]
    # elif situation == '5on4':
    #     shot_data = shot_data.loc[
    #         ((shot_data['isHomeTeam'] == 1) & (shot_data['awaySkatersOnIce'] == 4) & (shot_data['homeSkatersOnIce'] == 5)) |
    #         ((shot_data['isHomeTeam'] == 0) & (shot_data['awaySkatersOnIce'] == 5) & (shot_data['homeSkatersOnIce'] == 4))
    #     ]
    # elif situation == '4on5':
    #     shot_data = shot_data.loc[
    #         ((shot_data['isHomeTeam'] == 1) & (shot_data['awaySkatersOnIce'] == 5) & (shot_data['homeSkatersOnIce'] == 4)) |
    #         ((shot_data['isHomeTeam'] == 0) & (shot_data['awaySkatersOnIce'] == 4) & (shot_data['homeSkatersOnIce'] == 5))
    #     ]
    # elif situation == 'other':  # Inverse of 5on5, 5on4, 4on5
    #     shot_data = shot_data.loc[~(
    #         ((shot_data['awaySkatersOnIce'] == 5) & (shot_data['homeSkatersOnIce'] == 5)) |
    #         ((shot_data['isHomeTeam'] == 1) & (shot_data['awaySkatersOnIce'] == 4) & (shot_data['homeSkatersOnIce'] == 5)) |
    #         ((shot_data['isHomeTeam'] == 0) & (shot_data['awaySkatersOnIce'] == 5) & (shot_data['homeSkatersOnIce'] == 4)) |
    #         ((shot_data['isHomeTeam'] == 1) & (shot_data['awaySkatersOnIce'] == 5) & (shot_data['homeSkatersOnIce'] == 4)) |
    #         ((shot_data['isHomeTeam'] == 0) & (shot_data['awaySkatersOnIce'] == 4) & (shot_data['homeSkatersOnIce'] == 5))
    #     )]
    # No filtering needed if situation is 'all'

    # Exclude empty net shots
    shot_data = shot_data[shot_data['shotOnEmptyNet'] == 0]  # Exclude empty net shots

    # Drop unnecessary columns if needed (e.g., 'id', 'event' or other non-essential columns)
    shot_data = shot_data.drop(columns=['id'])  # example column removal

    return shot_data


def goal_map_scatter_get(db, api_key, llm, conditions, season_lower_bound, season_upper_bound, situation, season_type):
    """
    Generates a scatter plot of a player's goals on a hockey rink, excluding empty net goals and shots from behind half
    :param player_name: str, name of the NHL player to extract data for
    :param situation: str, game situation to extract data for, between the following options (5on5, 5on4, 4on5, all, other)
    :param season: int, season to extract data for (YYYY)
    :param season_type: str, type of season to extract data for, between the following options (regular, playoffs, all)
    :returns: matplotlib figure object
    """
    player_shots = extract_shot_data(db, api_key, conditions, season_lower_bound, season_upper_bound, situation, shot_result="GOAL", season_type=season_type)
    # TODO: Defensive programming if no goals are found for the player in the given season/situation???

    fig, ax = plt.subplots(1,1, figsize=(10,12), facecolor='w', edgecolor='k')
    
    rink = NHLRink(net={"visible": False})

    scatter = rink.scatter(
        "xCordAdjusted", "yCordAdjusted", data=player_shots,
        plot_range="offense", s=100, alpha=0.7, plot_xlim=(0, 89), color="orange",
        ax=ax, draw_kw={"display_range": "offense"},
    )

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
    

def shot_map_scatter_get(db, api_key, conditions, season_lower_bound, season_upper_bound, situation, season_type):
    """
    Generates a scatter plot of a player's shots and goals on a hockey rink, excluding empty net shots and shots from behind half
    :param player_name: str, name of the NHL player to extract data for
    :param situation: str, game situation to extract data for, between the following options (5on5, 5on4, 4on5, all, other)
    :param season: int, season to extract data for (YYYY)
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
#db = init_db()
# Sample function calls
# if __name__ == "__main__":
    # goal_map_scatter("Auston Matthews", 2021, "5on5", "regular")
    # shot_map_scatter("Auston Matthews", 2021, "5on5", "regular")
    # goal_map_scatter("Auston Matthews", 2022, "5on4", "playoffs")
    # goal_map_scatter("Travis Konecny", 2023, "4on5", "all")
    # goal_map_scatter("Connor McDavid", 2022, "all", "all")
    # goal_map_scatter("Auston Matthews", 2022, "other", "all")


#goal_map_scatter_get(db, "Auston Matthews", 2021, 2023, "5on5", "regular")

# query = f"""
#     SELECT * FROM shots_data WHERE shooterName = 'Darren Raddysh' and WHERE seasonLIMIT 5"""

# print(query)

# print(run_query_mysql(query, db))