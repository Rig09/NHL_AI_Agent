from utils.database_init import get_table_info, run_query_mysql
from langchain.chains.base import Chain
from langchain_core.output_parsers import StrOutputParser
import json
from decimal import Decimal
from langchain_core.prompts import ChatPromptTemplate

# Custom function to convert Decimal to str
def decimal_to_str(obj):
    if isinstance(obj, Decimal):
        return str(obj)  # Convert Decimal to string
    raise TypeError(f"Type {type(obj)} not serializable")


def team_record(db, llm, query: str):
    
    template = """
         Based on the table data dictionary below, generate a valid SQL query that answers the user's question based on the shots_data table. The user will request a teams "record" or there wins-loss ect. Given a set of certain conditions.
         A record is returned as follows: Wins-RegulationsLosses-OvertimeLosses. For every user query the goal is to generate an SQL query that finds the total number of unique games given that conditions, the number of wins the team has
         in games that meet the conditions, and the number of overtime losses where in games that meet the conditions. DO NOT INCLUDE GAMES THAT DONT MEET THE CONDITIONS IN THE QUERY. You only want games that meet the conditions to count in the record.
         For example if someone says, in games where they scored a powerplay goal, this should only count games where this occured. This is for wins, total, and overtime losses. Total is only the total of games that meet the conditions. Wins is only wins in games that meet the conditions.
         Allways keep this in mind when making the query.

        Your job is to find the total games, wins, and overtime losses for the specified team and the specified conditions in the user question. Allways infer the team and conditions being requested based on that question.

         DO NOT include explanations, comments, code blocks, or duplicate queries. Return only a single SQL query. DO NOT include ```sql or ``` in the response.
        Here is the data dictionary for shots_data:
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
        nhl_game_id: This is the unique identifier for each individual game the shot took place in. This number begins with the season, then has an indicator for season type, and then a number. More recent games, allways have a larger number.
        gameDate: a date when the shot took place. Repersented as year-month-day. For example, November 27th 2024 would be: 2024-11-27
        shooting_team_players: This is a list of the players on the ice for the shooting team at the time of the shot. They are listed as the full names seperated by a comma. Often times a players last name will be the only name given. Use like keyword in a SQL query.
        opposing_team_players: This is a list of the players on the ice for the opposing team at the time of the shot. They are listed as the full names seperated by a comma. Here is an example of what the column would have: "Nicolas Aube-Kubel, Sam Lafferty, Beck Malenstyn, Henri Jokiharju, Rasmus Dahlin"
        
        There is also some important terminology that you must know in order to understand user queries:
         "Even strength" → "5on5", "Power play" → "5on4", "Shorthanded" → "4on5", "All situations" → "All". This means use the homeSkatersOnIce and awaySkaterOnIce to determine the strength. When the team being asked about has more players than the oponent, this is called being on the powerplay.
         If they score in that situation, its called a powerplay goal. If the other team has more players, this is called being shorthanded. Even strength is when home skaters and away skaters have the sum number on the ice.
            So if someone asks for a record where a team scored on the powerplay or even strength or shorthanded, you have to handle this. I have shown how to do this. In an example.
         Teams are stored as abbreviations (e.g., "Toronto Maple Leafs" → "TOR"). Infer references like "Leafs" → "TOR".

        You must be careful to allways get the record for the teambeing asked about. If someone asks for the 'leafs' record. They want the record for the Toronto Maple Leafs so the team code has to be 'TOR'
        IT IS VERY IMPORTANT YOU USE THE CORRECT TEAM. FIND THE RECORD FOR THE TEAM BEING ASKED ABOUT.

        Note that each row in shots_data stores the data for an individual shot. If a player has 5 shots in that game, this will be 5 different rows. If a player scored multiple goals in one game they will be in two different rows with the same nhl_game_id value.
        If someone asks for games where a certain number of goals occured you must look for nhl_game_id values where there are that many rows with goals matching the creteria.

        If the user asks for a record between or after a certain date those dates MUST BE INCLUDED IN THE QUERY ALLWAYS. NO GAMES SHOULD BE COUNTED WITHOUT IT.
        If someone asks for the a teams 'record' when something happens, this means to return the number of wins and number of losses that occur in certain games. Use the same logic as returning the list of nhl_game_id values from shots_data, but also count the number of wins for the team using some logic and the 'homeTeamWon' column. Return the wins, and the total amount of games.
        A record has three values. Wins, regulation losses, and overtime losses. To find a record simply find the number of wins, total games that meet the conditions, and overtime losses. Here is an example of a query.

        If the user asks for the Toronto Maple Leafs record in games where Auston Matthew's scored since March 1st 2025 The query should be:
        "SELECT 
            SUM(CASE 
                WHEN (scoring_games.homeTeamCode = 'TOR' AND scoring_games.homeTeamWon = 1)  -- Toronto wins at home
                OR (scoring_games.awayTeamCode = 'TOR' AND scoring_games.homeTeamWon = 0)  -- Toronto wins away (when home team lost)
                THEN 1 ELSE 0 
            END) AS wins,
            
            COUNT(DISTINCT scoring_games.nhl_game_id) AS total_games,  -- Counts distinct nhl_game_id for games Matthews scored in
            
            SUM(CASE 
                WHEN ((scoring_games.homeTeamCode = 'TOR' AND scoring_games.homeTeamWon = 0)  -- Toronto loses at home
                    OR (scoring_games.awayTeamCode = 'TOR' AND scoring_games.homeTeamWon = 1))  -- Toronto loses away (home team wins)
                    AND shots_with_overtime.overtime = 1  -- Check if there was an overtime shot
                THEN 1 ELSE 0 
            END) AS overtime_losses
            
        FROM 
            (SELECT DISTINCT nhl_game_id, 
                    homeTeamCode, 
                    awayTeamCode, 
                    homeTeamWon
            FROM shots_data 
            WHERE shooterName = 'Auston Matthews' 
            AND goal = 1 
            AND gameDate >= '2025-03-01') AS scoring_games  -- Subquery to get unique games Matthews scored in
            
        LEFT JOIN 
            (SELECT nhl_game_id, 
                    MAX(CASE WHEN period = 4 THEN 1 ELSE 0 END) AS overtime  -- Check if a shot occurred in overtime period (period 4)
            FROM shots_data
            GROUP BY nhl_game_id) AS shots_with_overtime  -- Aggregate to check for overtime shots in the game
            ON scoring_games.nhl_game_id = shots_with_overtime.nhl_game_id
        "
        REMINDER, WHEN seeing if a shot was on the powerplay, you must account for BOTH home and away games. 
        The team being asked about are NOT nessisarily home or away. Use the team code to determine this. Allways include that step when finding shots on the powerplay.
        You also Have to include 5on3 and 4on3 powerplays AND have to ensure the powerplay was FOR the team with teamcode, since you can have an event while the other team is on the powerplay.

        Here is an example response for the question: 'What is the leafs record in games where they scored a powerplay goal since March 1st 2025':
        "SELECT 
            SUM(CASE
                WHEN (s.homeTeamCode = 'TOR' AND s.homeTeamWon = 1)
                OR (s.awayTeamCode = 'TOR' AND s.homeTeamWon = 0)
                THEN 1 ELSE 0
            END) AS wins,

            COUNT(DISTINCT s.nhl_game_id) AS total_games,

            SUM(CASE
                WHEN ((s.homeTeamCode = 'TOR' AND s.homeTeamWon = 0)
                    OR (s.awayTeamCode = 'TOR' AND s.homeTeamWon = 1))
                    AND ot.overtime = 1
                THEN 1 ELSE 0
            END) AS overtime_losses

        FROM (
            SELECT DISTINCT nhl_game_id, homeTeamCode, awayTeamCode, homeTeamWon
            FROM shots_data
            WHERE nhl_game_id IN (
                SELECT DISTINCT nhl_game_id
                FROM shots_data
                WHERE teamCode = 'TOR'
                AND goal = 1
                AND gameDate >= '2025-03-01'
                AND (
                    (homeSkatersOnIce = 5 AND awaySkatersOnIce IN (3, 4))
                    OR (homeSkatersOnIce IN (3, 4) AND awaySkatersOnIce = 5)
                    OR (homeSkatersOnIce = 4 AND awaySkatersOnIce = 3)
                    OR (homeSkatersOnIce = 3 AND awaySkatersOnIce = 4)
                )
            )
        ) s
        LEFT JOIN (
            SELECT nhl_game_id, MAX(CASE WHEN period = 4 THEN 1 ELSE 0 END) AS overtime
            FROM shots_data
            WHERE nhl_game_id IN (
                SELECT DISTINCT nhl_game_id
                FROM shots_data
                WHERE teamCode = 'TOR'
                AND goal = 1
                AND gameDate >= '2025-03-01'
                AND (
                    (homeSkatersOnIce = 5 AND awaySkatersOnIce IN (3, 4))
                    OR (homeSkatersOnIce IN (3, 4) AND awaySkatersOnIce = 5)
                    OR (homeSkatersOnIce = 4 AND awaySkatersOnIce = 3)
                    OR (homeSkatersOnIce = 3 AND awaySkatersOnIce = 4)
                )
            )
            GROUP BY nhl_game_id
        ) ot ON s.nhl_game_id = ot.nhl_game_id;
        "
            
        DO NOT INCLUDE ``` in the response. Do not include a period at the end of the response.
        Question: {question}
        SQL Query:
        """
    prompt = ChatPromptTemplate.from_template(template)
    recordFind_chain = (
        prompt
        | llm
        | StrOutputParser()
    )

    # Ensure proper usage of keyword arguments in invoke
    #sql_query = llm.invoke(template).content
    sql_query = recordFind_chain.invoke({'question': query})
    print(sql_query)
    result = run_query_mysql(sql_query, db)
    # If the result is a list (from SELECT query), you can convert it into a string
    # if isinstance(result, list):
    #     result= json.dumps(result, default=decimal_to_str, indent=4) # Converts the result list into a pretty-printed JSON string
    #     print(result)
    # else:
    #     # If the result is None (from non-SELECT queries), handle accordingly
    #     print("not a list")
    print(f"first result:{result}")
    result= json.dumps(result, default=decimal_to_str, indent=4) # Converts the result list into a pretty-printed JSON string
    print(result)
    return result
