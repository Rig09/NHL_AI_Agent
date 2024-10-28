import pandas as pd

def find_percentile(arr, item):
    """
    Given an array of values, arr, and a specific value within it, item, 
    find the percentile of where the values lies in the array
    """
    sorted_arr = sorted(arr)
    index = sorted_arr.index(item)
    percentile = (index + 1) / len(sorted_arr) * 100
    return round(percentile, 1)

def get_player_card_dict(player_name, use_playoffs=False):
    """
    # TODO: Fill in docstring
    # TODO: Include multiple seasons? Include stats by year?
    # NOTE: If a player plays for multiple teams in a year, there is no way to separate their year
            #  by team (using MP data)
    # TODO: Modify so full season, reg only, and playoff only can be calculated?
    """

    if use_playoffs == 0: # Regular season
        skater_data = pd.read_csv("../data/skaters_regular_2023-2024.csv")
    else:  # Playoffs
        skater_data = pd.read_csv("../data/skaters_playoffs_2023-2024.csv")

    # TODO: Check for player name in that season

    # NOTE: Filtering for all situations. Will need additional processing for PP, PK
    skater_data = skater_data[skater_data["situation"] == "all"]

    cols_to_keep = ["name", "team", "icetime", "I_F_goals", "I_F_primaryAssists", "I_F_secondaryAssists", "I_F_points",
                    "OnIce_F_goals", "OnIce_A_goals","I_F_takeaways", "I_F_giveaways", "I_F_xGoals",
                    "OnIce_F_xGoals", "OnIce_A_xGoals", "onIce_xGoalsPercentage", "I_F_hits", "shotsBlockedByPlayer"]

    # Filtering DF to include relevant cols only
    skater_data = skater_data[cols_to_keep]

    # Calculating a few columns which are not present in the skaters.csv files
    skater_data["I_F_assists"] = skater_data["I_F_primaryAssists"] + skater_data["I_F_secondaryAssists"]
    skater_data["I_F_primaryPoints"] = skater_data["I_F_points"] - skater_data["I_F_secondaryAssists"]
    skater_data["I_F_primaryPoints"] = skater_data["I_F_points"] - skater_data["I_F_secondaryAssists"]

    # NOTE: Defensive program for 0s?
    skater_data["onIce_goalsPercentage"] = (skater_data["OnIce_F_goals"] / (skater_data["OnIce_F_goals"] + skater_data["OnIce_A_goals"])).round(2)
    skater_data["I_F_takeawaysToGiveaways"] = (skater_data["I_F_takeaways"] / skater_data["I_F_giveaways"]).round(2)
    # 
    skater_data["I_F_assistsToGiveaways"] = (skater_data["I_F_assists"] / skater_data["I_F_giveaways"]).round(2)

    # Format: Stat Name, DF col
    stats = [("TOI", "icetime"), ("Goals", "I_F_goals"), ("Assists", "I_F_assists"), 
            ("Primary Assists", "I_F_primaryAssists"), ("Primary Points", "I_F_primaryPoints"), 
            ("Points", "I_F_points"), ("XG For", "I_F_xGoals"), ("On Ice XG For", "OnIce_F_xGoals"),
            ("On Ice Goals For", "OnIce_F_goals"), ("On Ice XG Against", "OnIce_A_xGoals"), 
            ("On Ice Goals Against", "OnIce_A_goals"), ("On Ice XG%", "onIce_xGoalsPercentage"), 
            ("On Ice Goal%", "onIce_goalsPercentage"), ("Hits", "I_F_hits"), 
            ("Blocked Shots", "shotsBlockedByPlayer"), ("Takeaways", "I_F_takeaways"),
            ("Giveaways", "I_F_giveaways"), ("Takeaways to Giveaways Ratio", "I_F_takeawaysToGiveaways"), 
            ("Assist to Giveaways Ratio", "I_F_assistsToGiveaways")]
    # NOTE: Giveaways and takeaways by zone (off, neu, def) are not available with MP data

    player_df = skater_data[skater_data["name"] == player_name]

    player_stats_dict = {} # Dict with stat as key and tuple of value and percentile
    # NOTE: Percentiles currently calculated for all stats. Would need bools in the stats array to change this behaviour

    for category, df_col in stats:
        indiv_value = player_df[df_col].values[0]
        percentile = find_percentile(skater_data[df_col], indiv_value)

        # Giveaways are a negative stat, so percentile is inverted
        if category == "Giveaways":
            percentile = 100 - percentile
        
        player_stats_dict[category] = indiv_value, percentile

    return player_stats_dict
