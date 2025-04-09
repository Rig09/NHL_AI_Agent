import pandas as pd
import numpy as np
from datetime import date
from utils.database_init import run_query_mysql


def ngames_player_xgpercent(db, player_name, game_number, situation):
        """Runs a SQL query to find the expected goals percentage for a player over their last n games."""
        if situation == 'all':
            query = f"""
            SELECT teamCode, shooting_team_players, opposing_team_players, xGoal, shotID
            FROM shots_data
            WHERE (LOWER(shooting_team_players) LIKE LOWER('%{player_name}%') OR LOWER(opposing_team_players) LIKE LOWER('%{player_name}%'))
            AND nhl_game_id IN (
                SELECT nhl_game_id
                FROM (
                    SELECT DISTINCT nhl_game_id
                    FROM shots_data
                    WHERE (LOWER(shooting_team_players) LIKE LOWER('%{player_name}%') OR LOWER(opposing_team_players) LIKE LOWER('%{player_name}%'))
                    ORDER BY nhl_game_id DESC
                    LIMIT {game_number}
                ) AS recent_games
            )
            """
        elif situation == 'Even strength':
             query = f"""
            SELECT teamCode, shooting_team_players, opposing_team_players, xGoal, shotID
            FROM shots_data
            WHERE (LOWER(shooting_team_players) LIKE LOWER('%{player_name}%') OR LOWER(opposing_team_players) LIKE LOWER('%{player_name}%')) AND awaySkatersOnice = homeSkatersOnIce
            AND nhl_game_id IN (
                SELECT nhl_game_id
                FROM (
                    SELECT DISTINCT nhl_game_id
                    FROM shots_data
                    WHERE (LOWER(shooting_team_players) LIKE LOWER('%{player_name}%') OR LOWER(opposing_team_players) LIKE LOWER('%{player_name}%'))
                    ORDER BY nhl_game_id DESC
                    LIMIT {game_number}
                ) AS recent_games
            )
            """
        else:
              raise ValueError(f"Invalid situation: {situation}. Expected 'all' or 'Even strength'.")
        shots_df = pd.DataFrame(run_query_mysql(query, db))
        player_xGoals = shots_df.loc[shots_df['shooting_team_players'].str.contains(player_name, na=False), 'xGoal'].sum()
        against_xGoals = shots_df.loc[shots_df['opposing_team_players'].str.contains(player_name, na=False),'xGoal'].sum()

        print(shots_df.head(20))
        print(f"expected for: {player_xGoals}")
        print(f"expected against: {against_xGoals}")
        # Calculate the total sum of xGoal
        #total_xGoals = shots_df['xGoal'].sum()
        total_xGoals = player_xGoals + against_xGoals
        # Avoid division by zero
        if total_xGoals == 0:
            return 'No shots Given those conditions'
        
        return player_xGoals/total_xGoals
            


def date_player_xgpercent(db, player_name, start_date, end_date, situation):
    """Hardcoded SQL query to find the expected goals percentage for a player over a given date range"""
    if situation == 'all':
        query = f"""
            SELECT teamCode, shooting_team_players, opposing_team_players, xGoal, shotID
            FROM shots_data
            WHERE(shooting_team_players LIKE '%{player_name}%' OR opposing_team_players LIKE '%{player_name}%')
            AND gameDate between '{start_date}' AND '{end_date}'
        """
    elif situation == 'Even strength':
         query = f"""
            SELECT teamCode, shooting_team_players, opposing_team_players, xGoal, shotID
            FROM shots_data
            WHERE(shooting_team_players LIKE '%{player_name}%' OR opposing_team_players LIKE '%{player_name}%') AND awaySkatersOnice = homeSkatersOnIce
            AND gameDate between '{start_date}' AND '{end_date}'
        """
    else: 
        raise ValueError(f"Invalid situation: {situation}. Expected 'all' or 'Even strength'.")
    shots_df = pd.DataFrame(run_query_mysql(query, db))
                # Calculate the number of shots containing the player in shooting_team_players
    # Calculate the sum of xGoal where the player is in shooting_team_players
    player_xGoals = shots_df.loc[shots_df['shooting_team_players'].str.contains(player_name, na=False), 'xGoal'].sum()

    # Calculate the total sum of xGoal
    total_xGoals = shots_df['xGoal'].sum()

    # Avoid division by zero
    if total_xGoals == 0:
        return 'No shots Given those conditions'
    
    return player_xGoals/total_xGoals



def ngames_team_xgpercent(db, teamCode, game_number, situation):
    """Runs a SQL query to find the expected goals percentage for a team over their last n games."""
    if situation == 'all':
        query = f"""
        SELECT teamCode, xGoal, shotID
        FROM shots_data
        WHERE (homeTeamCode = '{teamCode}' OR awayTeamCode = '{teamCode}')
        AND nhl_game_id IN (
            SELECT DISTINCT nhl_game_id
            FROM (
                SELECT nhl_game_id
                FROM shots_data
                WHERE (homeTeamCode = '{teamCode}' OR awayTeamCode = '{teamCode}')
                ORDER BY nhl_game_id DESC
                LIMIT {game_number}
            ) AS recent_games
        )
        """
    elif situation == 'Even strength':
        query = f"""
        SELECT teamCode, xGoal, shotID
        FROM shots_data
        WHERE (homeTeamCode = '{teamCode}' OR awayTeamCode = '{teamCode}') AND awaySkatersOnice = homeSkatersOnIce
        AND nhl_game_id IN (
            SELECT DISTINCT nhl_game_id
            FROM (
                SELECT nhl_game_id
                FROM shots_data
                WHERE (homeTeamCode = '{teamCode}' OR awayTeamCode = '{teamCode}')
                ORDER BY nhl_game_id DESC
                LIMIT {game_number}
            ) AS recent_games
        )
        """
    else: 
        raise ValueError(f"Invalid situation: {situation}. Expected 'all' or 'Even strength'.")
    shots_df = pd.DataFrame(run_query_mysql(query, db))

    # Calculate the sum of xGoal for the given team
    team_xGoals = shots_df.loc[shots_df['teamCode'] == teamCode, 'xGoal'].sum()

    # Calculate the total sum of xGoal
    total_xGoals = shots_df['xGoal'].sum()

    # Avoid division by zero
    if total_xGoals == 0:
        return 'No shots given those conditions'
    
    return team_xGoals / total_xGoals
            


def date_team_xgpercent(db, teamCode, start_date, end_date, situation):
    """Hardcoded SQL query to find the expected goals percentage for a player over a given date range"""
    if situation == 'all':
        query = f"""
            SELECT teamCode, xGoal, shotID
            FROM shots_data
            WHERE (homeTeamCode = '{teamCode}' OR awayTeamCode = '{teamCode}')
            AND gameDate between '{start_date}' AND '{end_date}'
        """
    elif situation == 'Even strength':
        query = f"""
            SELECT teamCode, xGoal, shotID
            FROM shots_data
            WHERE (homeTeamCode = '{teamCode}' OR awayTeamCode = '{teamCode}') AND awaySkatersOnice = homeSkatersOnIce
            AND gameDate between '{start_date}' AND '{end_date}'
        """
    else:
        raise ValueError(f"Invalid situation: {situation}. Expected 'all' or 'Even strength'.")
    shots_df = pd.DataFrame(run_query_mysql(query, db))

    # Calculate the sum of xGoal for the given team
    team_xGoals = shots_df.loc[shots_df['teamCode'] == teamCode, 'xGoal'].sum()

    # Calculate the total sum of xGoal
    total_xGoals = shots_df['xGoal'].sum()

    # Avoid division by zero
    if total_xGoals == 0:
        return 'No shots given those conditions'
    
    return team_xGoals / total_xGoals


def ngames_line_xgpercent(db, player_one, player_two, player_three, game_number):
    """Runs a SQL query to find the expected goals percentage for a player over their last n games."""
    if player_three != 'None':
        query = f"""
        SELECT teamCode, shooting_team_players, opposing_team_players, xGoal, shotID
        FROM shots_data
        WHERE (
            (LOWER(shooting_team_players) LIKE LOWER('%{player_one}%') AND
            LOWER(shooting_team_players) LIKE LOWER('%{player_two}%') AND
            LOWER(shooting_team_players) LIKE LOWER('%{player_three}%'))
            OR
            (LOWER(opposing_team_players) LIKE LOWER('%{player_one}%') AND
            LOWER(opposing_team_players) LIKE LOWER('%{player_two}%') AND
            LOWER(opposing_team_players) LIKE LOWER('%{player_three}%')) AND awaySkatersOnice = homeSkatersOnIce
        )
        AND nhl_game_id IN (
        SELECT nhl_game_id
        FROM (
            SELECT DISTINCT nhl_game_id
            FROM shots_data
            WHERE (
                (LOWER(shooting_team_players) LIKE LOWER('%{player_one}%') AND
                LOWER(shooting_team_players) LIKE LOWER('%{player_two}%') AND
                LOWER(shooting_team_players) LIKE LOWER('%{player_three}%'))
                OR
                (LOWER(opposing_team_players) LIKE LOWER('%{player_one}%') AND
                LOWER(opposing_team_players) LIKE LOWER('%{player_two}%') AND
                LOWER(opposing_team_players) LIKE LOWER('%{player_three}%')) AND awaySkatersOnice = homeSkatersOnIce
            )
            ORDER BY nhl_game_id DESC
            LIMIT {game_number}
        ) AS recent_games
        )
        """
    else:
        query = f"""
        SELECT teamCode, shooting_team_players, opposing_team_players, xGoal, shotID
        FROM shots_data
        WHERE (
            (LOWER(shooting_team_players) LIKE LOWER('%{player_one}%') AND
            LOWER(shooting_team_players) LIKE LOWER('%{player_two}%'))
            OR
            (LOWER(opposing_team_players) LIKE LOWER('%{player_one}%') AND
            LOWER(opposing_team_players) LIKE LOWER('%{player_two}%')) AND awaySkatersOnice = homeSkatersOnIce
        )
        AND nhl_game_id IN (
        SELECT nhl_game_id
        FROM (
            SELECT DISTINCT nhl_game_id
            FROM shots_data
            WHERE (
                (LOWER(shooting_team_players) LIKE LOWER('%{player_one}%') AND
                LOWER(shooting_team_players) LIKE LOWER('%{player_two}%'))
                OR
                (LOWER(opposing_team_players) LIKE LOWER('%{player_one}%') AND
                LOWER(opposing_team_players) LIKE LOWER('%{player_two}%')) AND awaySkatersOnice = homeSkatersOnIce
            )
            ORDER BY nhl_game_id DESC
            LIMIT {game_number}
        ) AS recent_games
        )
        """  
    shots_df = pd.DataFrame(run_query_mysql(query, db))
    player_xGoals = shots_df.loc[shots_df['shooting_team_players'].str.contains(player_one, na=False), 'xGoal'].sum()
    against_xGoals = shots_df.loc[shots_df['opposing_team_players'].str.contains(player_one, na=False),'xGoal'].sum()

    # Calculate the total sum of xGoal
    #total_xGoals = shots_df['xGoal'].sum()
    total_xGoals = player_xGoals + against_xGoals
    # Avoid division by zero
    if total_xGoals == 0:
        return 'No shots Given those conditions'
    
    return player_xGoals/total_xGoals
            


def date_line_xgpercent(db, player_one, player_two, player_three, start_date, end_date):
    """Hardcoded SQL query to find the expected goals percentage for a player over a given date range"""
    if player_three != 'None':
        query = f"""
            SELECT teamCode, shooting_team_players, opposing_team_players, xGoal, shotID
            FROM shots_data
            WHERE(LOWER(shooting_team_players) LIKE LOWER('%{player_one}%') AND
                    LOWER(shooting_team_players) LIKE LOWER('%{player_two}%') AND
                    LOWER(shooting_team_players) LIKE LOWER('%{player_three}%')) AND awaySkatersOnice = homeSkatersOnIce
                OR
                (LOWER(opposing_team_players) LIKE LOWER('%{player_one}%') AND
                    LOWER(opposing_team_players) LIKE LOWER('%{player_two}%') AND
                    LOWER(opposing_team_players) LIKE LOWER('%{player_three}%')) AND awaySkatersOnice = homeSkatersOnIce
            AND gameDate between '{start_date}' AND '{end_date}'
        """
    else:
        query = f"""
            SELECT teamCode, shooting_team_players, opposing_team_players, xGoal, shotID
            FROM shots_data
            WHERE(LOWER(shooting_team_players) LIKE LOWER('%{player_one}%') AND
                    LOWER(shooting_team_players) LIKE LOWER('%{player_two}%')) AND awaySkatersOnice = homeSkatersOnIce
                OR
                (LOWER(opposing_team_players) LIKE LOWER('%{player_one}%') AND
                    LOWER(opposing_team_players) LIKE LOWER('%{player_two}%')) AND awaySkatersOnice = homeSkatersOnIce
            AND gameDate between '{start_date}' AND '{end_date}'
        """
    shots_df = pd.DataFrame(run_query_mysql(query, db))
                # Calculate the number of shots containing the player in shooting_team_players
    # Calculate the sum of xGoal where the player is in shooting_team_players
    player_xGoals = shots_df.loc[shots_df['shooting_team_players'].str.contains(player_one, na=False), 'xGoal'].sum()

    # Calculate the total sum of xGoal
    total_xGoals = shots_df['xGoal'].sum()

    # Avoid division by zero
    if total_xGoals == 0:
        return 'No shots Given those conditions'
    
    return player_xGoals/total_xGoals