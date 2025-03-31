import pandas as pd
import urllib.request
import urllib.error
import os
from dotenv import load_dotenv
from chains.stats_sql_chain import get_sql_chain
from langchain_openai import ChatOpenAI
from openai import OpenAI 
import numpy as np
from langchain_community.utilities import SQLDatabase
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from datetime import datetime, date
from utils.database_init import init_db, run_query_mysql

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
open_ai_key = os.getenv("OPENAI_API_KEY")

def get_date_data_from_table(llm, db, sql_chain, natural_language_query, today_date):
        template_for_sql_query = f"""Please return a list of shots from the shots_data table that contains only the columns and rows relavent to the query: {natural_language_query}.
        Allways add a condition for the dates of the shots, use the natural language query to determine this. Again return only the needed columns. Also note for context today's date is {today_date}"""
        print(template_for_sql_query)
        query = sql_chain.invoke({"question" : template_for_sql_query})
        shot_data = pd.DataFrame(run_query_mysql(query, db))
        print(shot_data.head(5))
        if shot_data.empty:
            raise ValueError("There was an error with the query. Please try again with a different query.")
        return shot_data

def get_ngame_data(llm, db, sql_chain, natural_language_query):
    template_for_sql_query = f"""Please return a list of shots from the shots_data table that contains only the columns and rows relavent to the query: {natural_language_query}.
    This should be a query asking for a stat over the last _ number of games. Or between game numbers for a team. Use the fact that the greater the nhl_game_id value, the more recent the game was.
    When somone refers to a game number though, they mean within a certain season value"""
    print(template_for_sql_query)
    query = sql_chain.invoke({"question" : template_for_sql_query})
    shot_data = pd.DataFrame(run_query_mysql(query, db))
    print(shot_data.head(5))
    if shot_data.empty:
        raise ValueError("There was an error with the query. Please try again with a different query.")
    return shot_data


def get_stats_by_dates(llm, db, sql_chain, natural_language_query, today_date):

    table = get_date_data_from_table(llm, db, sql_chain, natural_language_query, today_date)

    table_str = table.to_string()

    template_for_stat_description = f"""You are a tool for finding stats between given a certain date or number of games condition. Using a LangChain tool, we have fetched a table of
    shots for games within those dates based on a user question: {natural_language_query}.
    The resulting table: {table_str} 

    Based on the user query, and the provided table, please provide a natural language description of the result. The table will have fewer columns,
    but here is a data dictionary so you understand the table's output:
    shotID: Unique id for each shot
    homeTeamCode: The home team in the game. For example: TOR, MTL, NYR, etc
    awayTeamCode: The away team in the game
    season: Season the shot took place in. Example: 2009 for the 2009-2010 season
    isPlayoffGame: Set to 1 if a playoff game, otherwise 0
    game_id: The NHL Game_id of the game the shot took place in
    time: Seconds into the game of the shot
    period: Period of the game
    team: The team taking the shot. HOME or AWAY
    location: The zone the shot took place in. HOMEZONE, AWAYZONE, or Neu. Zone
    event: Whether the shot was a shot on goal (SHOT), goal, (GOAL), or missed the net (MISS)
    goal: Set to 1 if shot was a goal. Otherwise 0
    xCord: The X coordinate "North South" on the ice of the shot. Feet from red line.  -89 and 89 are the goal lines at each of the rink
    yCord: The Y coordinate  "East West" on the ice of the shot. The middle of the ice has a y-coordinate of 0
    xCordAdjusted: Adjusts the x coordinate as if all shots were at the right end of the rink. Usually makes the coordinate a positive number
    yCordAdjusted: Adjusts the y coordinate as if all shots were at the right end of the rink.
    homeTeamGoals: Home team goals before the shot took place
    awayTeamGoals: Away team goals before the shot took palce
    homeSkatersOnIce: The number of skaters on the ice for the home team. Does not count the goalie
    awaySkatersOnIce: The number of skaters on the ice for the away team. Does not count the goalie
    goalieNameForShot: The First and Last name of the goalie the shot is on.
    shooterPlayerId: The NHL player id of the skater taking the shot
    shooterName: The First and Last name of the player taking the shot
    xGoal: The probability the shot will be a goal. Also known as "Expected Goals"
    playerPositionThatDidEvent: The position of the player doing the shot. L for Left Wing, R for Right Wing, D for Defenceman, C for Centre.
    teamCode: The team code of the shooting team. For example, TOR, NYR, etc
    gameDate: a date when the shot took place. Repersented as year-month-day. For example, November 27th 2024 would be: 2024-11-27
    shooting_team_players: This is a list of the players on the ice for the shooting team at the time of the shot. They are listed as the full names seperated by a comma. Often times a players last name will be the only name given. Use like keyword in a SQL query.
    opposing_team_players: This is a list of the players on the ice for the opposing team at the time of the shot. They are listed as the full names seperated by a comma. Here is an example of what the column would have: "Nicolas Aube-Kubel, Sam Lafferty, Beck Malenstyn, Henri Jokiharju, Rasmus Dahlin"

    ALLWAYS RETURN THE VALUE REQUESTED, DO NOT RETURN A PROCESS TO FIND IT.
    
    For addition context, todays date is {today_date}. Allways insure you return the value being requested.
    """
    natural_language_response = llm.invoke(template_for_stat_description).content
    return natural_language_response


def get_stats_ngames(llm, db, sql_chain, natural_language_query):

    table = get_ngame_data(llm, db, sql_chain, natural_language_query)

    table_str = table.to_string()

    template_for_stat_description = f"""You are a tool for finding stats between given a certain date or number of games condition. Using a LangChain tool, we have fetched a table of
    shots for games within those dates based on a user question: {natural_language_query}.
    The resulting table: {table_str} 

    Based on the user query, and the provided table, please provide a natural language description of the result. The table will have fewer columns,
    but here is a data dictionary so you understand the table's output:
    shotID: Unique id for each shot
    homeTeamCode: The home team in the game. For example: TOR, MTL, NYR, etc
    awayTeamCode: The away team in the game
    season: Season the shot took place in. Example: 2009 for the 2009-2010 season
    isPlayoffGame: Set to 1 if a playoff game, otherwise 0
    game_id: The NHL Game_id of the game the shot took place in
    time: Seconds into the game of the shot
    period: Period of the game
    team: The team taking the shot. HOME or AWAY
    location: The zone the shot took place in. HOMEZONE, AWAYZONE, or Neu. Zone
    event: Whether the shot was a shot on goal (SHOT), goal, (GOAL), or missed the net (MISS)
    goal: Set to 1 if shot was a goal. Otherwise 0
    xCord: The X coordinate "North South" on the ice of the shot. Feet from red line.  -89 and 89 are the goal lines at each of the rink
    yCord: The Y coordinate  "East West" on the ice of the shot. The middle of the ice has a y-coordinate of 0
    xCordAdjusted: Adjusts the x coordinate as if all shots were at the right end of the rink. Usually makes the coordinate a positive number
    yCordAdjusted: Adjusts the y coordinate as if all shots were at the right end of the rink.
    homeTeamGoals: Home team goals before the shot took place
    awayTeamGoals: Away team goals before the shot took palce
    homeSkatersOnIce: The number of skaters on the ice for the home team. Does not count the goalie
    awaySkatersOnIce: The number of skaters on the ice for the away team. Does not count the goalie
    goalieNameForShot: The First and Last name of the goalie the shot is on.
    shooterPlayerId: The NHL player id of the skater taking the shot
    shooterName: The First and Last name of the player taking the shot
    xGoal: The probability the shot will be a goal. Also known as "Expected Goals"
    playerPositionThatDidEvent: The position of the player doing the shot. L for Left Wing, R for Right Wing, D for Defenceman, C for Centre.
    teamCode: The team code of the shooting team. For example, TOR, NYR, etc
    gameDate: a date when the shot took place. Repersented as year-month-day. For example, November 27th 2024 would be: 2024-11-27
    shooting_team_players: This is a list of the players on the ice for the shooting team at the time of the shot. They are listed as the full names seperated by a comma. Often times a players last name will be the only name given. Use like keyword in a SQL query.
    opposing_team_players: This is a list of the players on the ice for the opposing team at the time of the shot. They are listed as the full names seperated by a comma. Here is an example of what the column would have: "Nicolas Aube-Kubel, Sam Lafferty, Beck Malenstyn, Henri Jokiharju, Rasmus Dahlin"
    
    ALLWAYS RETURN THE VALUE REQUESTED, DO NOT RETURN A PROCESS TO FIND IT.
    """
    natural_language_response = llm.invoke(template_for_stat_description).content
    return natural_language_response

def main():
    db = init_db(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE)
    
    # Initialize the LLM (e.g., ChatOpenAI or other models)
    llm=ChatOpenAI(model="gpt-4o", api_key=open_ai_key)  # Customize the model and parameters as needed
    
    # Initialize SQL chain
    sql_chain = get_sql_chain(db, llm)

    natural_language_query = "What was the expected goals percentage for the Leafs between Jan 1st 2025 and Jan 10th 2025"
    today_date = date.today()
    # start_date = "2025-01-01"
    # end_date = "2025-01-10"
    print(get_stats_by_dates(llm, db, sql_chain, natural_language_query, today_date))

    second_query = "What is Auston Matthew's Expected goals percentage in his last 5 games"


    print(get_stats_ngames(llm, db, sql_chain, second_query))
if __name__ == "__main__":
    main()