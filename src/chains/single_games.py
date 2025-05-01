from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.globals import set_verbose
from utils.database_init import get_table_info, run_query_mysql, init_db
import os

# load_dotenv()
# MYSQL_HOST = os.getenv("MYSQL_HOST")
# MYSQL_USER = os.getenv("MYSQL_USER")
# MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
# MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
# open_ai_key = os.getenv("OPENAI_API_KEY")

# db = init_db(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE)

# llm=ChatOpenAI(model="gpt-4o", api_key=open_ai_key)

def single_game_sql(db, llm):
    def get_table_schema(db):
        relevent_tables = ['shots_data']
        return get_table_info(db, relevent_tables) #return the schema of the first table in the list

    template = """
                Based on the table schema below, generate a valid SQL query that answers the user's question. 
                DO NOT include explanations, comments, code blocks, or duplicate queries. Return only a single SQL query. DO NOT include ```sql or ``` in the response.
                {schema}
                Here is a description of the table fields:
                shotID: Unique id for each shot. Note this is only unique for each game, this requires nhl_game_id to be used with it to uniquely identify each shot.
                homeTeamCode: The home team in the game. For example: TOR, MTL, NYR, etc
                awayTeamCode: The away team in the game
                season: Season the shot took place in. Example: 2009 for the 2009-2010 season
                isPlayoffGame: Set to 1 if a playoff game, otherwise 0
                game_id: The NHL Game_id of the game the shot took place in. This repeats for every season, only nhl_game_id is fully unique to each game.
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
                nhl_game_id: This is the unique identifier for each individual game the shot took place in. This number begins with the season, then has an indicator for season type, and then a number. More recent games, allways have a larger number.
                gameDate: a date when the shot took place. Repersented as year-month-day. For example, November 27th 2024 would be: 2024-11-27
                shooting_team_players: This is a list of the players on the ice for the shooting team at the time of the shot. They are listed as the full names seperated by a comma. Often times a players last name will be the only name given. Use like keyword in a SQL query.
                opposing_team_players: This is a list of the players on the ice for the opposing team at the time of the shot. They are listed as the full names seperated by a comma. Here is an example of what the column would have: "Nicolas Aube-Kubel, Sam Lafferty, Beck Malenstyn, Henri Jokiharju, Rasmus Dahlin"
                
                Whenever someone asks about whether a player was on the ice, use the like keyword and not the in. In will not work. Use like, '(percent symbol) name (percent symbol)'
                So within a query it would look like 
                "SELECT * FROM shots_data WHERE shotting_team_players like '%Auston Matthews%'" this would find all the shots for Auston Matthew's team when he is on the ice.

                When a user asks how many times something has been done in a single game. Use the shots table. Use the nhl_game_Id and shooterPlayerID to group the shots and see if that feat was accomplished in that single game.
                For example, If somoene asks, how many times has "Auston Matthews" scored 4 goals in a game. Use the shots_data table, group the shots by the nhl_game_id, and count the number of unique gameid values where Auston Matthews scored 4 goals (so 4 different shots have a value for goal of 1 within the same game, all taken by Auston Matthews). 
                ENSURE THAT IF SOMEONE ASKS FOR GOALS YOU ARE ONLY COUNTING SHOTS WHERE goal = 1. Not when it equals zero. Count only rows that are goals, not all shots.
                
                If somoeone were to ask, how many players have scored 4 goals in a single game. Group the shots by nhl_game_id, and shooterPlayerId. Then find where a single player scored 4 goals in a single game. Count the number of unique PLAYERIDS that have accomplished this(ie 4 of the shots in a single nhl_game_id and ShooterPlayerID grouping have a goal value of 1) and return it.
                For that example, its very important to ensure that you are returning games with 4 GOALS not shots. Ensure the goal column has a vlaue of 1.
                
                Here is an example query for the above:
                "WITH rel_games AS (
                SELECT 
                        nhl_game_id,
                        shooterName,
                        COUNT(goal) AS goalNum
                    FROM shots_data
                    WHERE shooterName = 'Auston Matthews' AND goal = 1
                    GROUP BY nhl_game_id, shooterName
                )

                SELECT COUNT(DISTINCT nhl_game_id)
                FROM rel_games
                WHERE goalNum >= 4;"
                
                Alternatively, If someone asked for how many players have scored 4 goals in a single game and who were they, the query would be:
                "WITH rel_games AS (
                    SELECT 
                        nhl_game_id,
                        shooterName,
                        COUNT(goal) AS goalNum
                    FROM shots_data
                    WHERE goal = 1
                    GROUP BY nhl_game_id, shooterName
                    )

                    SELECT 
                    COUNT(DISTINCT nhl_game_id) AS num_games_with_4plus_goals,
                    shooterName
                    FROM rel_games
                    WHERE goalNum >= 4
                    GROUP BY shooterName;"
                
                Someone may ask how many times something has been done in a playoff game. For this simply check if the isPlayoffGame column is 1 or 0.

                The code of the team that took the shot is teamCode. Crossrefrencing this with the values for homeTeamCode, awayTeamCode, homeSkatersOnIce, and awaySkatersOnIce you can find the 'strength'.
                If someone asks for a stat at even strength this means when homeSkatersOnIce and awaySkatersOnIce are equal. If they say 5on5 then when both these values are at 5. If they say on the powerplay,
                this means with the opposition team having fewer skaters on the ice as the requested team. Shorthanded, or on the penalty kill, or just on the kill, mean when the oposition team has more players than the shooting team.


                DO NOT INCLUDE ``` in the response. Do not include a period at the end of the response.
                Question:{question}
                SQL Query:
                '"""

    prompt = ChatPromptTemplate.from_template(template)

    sql_chain = (
        RunnablePassthrough.assign(schema=lambda _: get_table_schema(db))
        | prompt
        | llm
        | StrOutputParser()
        |(lambda sql_query: print("Generated SQL Query:", sql_query) or sql_query) 
        #|(lambda output: extract_sql_query(output)) 
    )
    return sql_chain

#print(sql_chain.invoke({'question':'How many times did Auston Matthews score 4 goals in a single game'}))

# print(sql_chain.invoke({'question':'How many has Auston Matthews been on the ice for 4 even strength goals against his team in a single game'}))


def get_single_game_chain(db, llm):
    def run_query(query, db):
        return run_query_mysql(query, db)
    
    def get_table_schema(db):
        relevent_tables = ['shots_data']
        return get_table_info(db, relevent_tables) #return the schema of the first table in the list


    sql_chain = single_game_sql(db, llm)

    #print(sql_chain.invoke({"question": "How many goals did William Nylander score in the 2018 playoffs"}))
    #print(sql_chain.invoke({"question": "How many goals did Sidney Crosby score in the 2023 regular season?"})) #Test the first chain generating sql query

    template = """
    Based on the table schema below, quesiton, sql query, and sql response, write a natural language response to the user question.
    {schema}

    Quesiton: {question}
    SQL Query: {query}
    SQL Response: {response}

    Note that if the question asks for a rank or where does something rank among _ include the simple number along with the stat. 
    For example someone asks where a line ranks in expected goals percentage return where they are in a list sorted by the highest percentages. For example a pair would rank fifth. The percentage is 60%. Return both of these, but make sure you return the ranking.
    If a user requests a record, find the number of regulation losses by substracting wins and overtime losses from the total games. Records are presented as Wins - Regulation losses - overtime losses. For example 3-2-1.
    """
    prompt = ChatPromptTemplate.from_template(template)

    full_chain = (
        RunnablePassthrough.assign(query = sql_chain).assign(schema = lambda _: get_table_schema(db)).assign(response=lambda variables: run_query(variables["query"], db))
        | prompt
        | llm
        | StrOutputParser()
    )
    return full_chain

# print(full_chain.invoke({'question':'How many has Auston Matthews been on the ice for 4 even strength goals against his team in a single game'}))