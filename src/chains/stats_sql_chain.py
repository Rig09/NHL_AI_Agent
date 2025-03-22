from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.globals import set_verbose
from utils.database_init import get_table_info, run_query_mysql


set_verbose(True)

# SQLite Database URI
#db_uri = "sqlite:///SkatersStats.db"

#db = SQLDatabase.from_uri(db_uri)

#mySQL implementation
#db = init_db()

#print(db.run("SELECT * FROM RegularSeason2023 LIMIT 1")) # Test the database connection

def get_sql_chain(db, llm):

    #database functions. Get information from the databases to be used in the chain
    def get_table_schema(db):
        relevent_tables = ['SkaterStats_regular_2024', 'GoalieStats_regular_2024', 'LineStats_playoffs_2024', 'PairStats_regular_2024', 'teamstats_regular_2024']
        return get_table_info(db, relevent_tables) #return the schema of the first table in the list

    #print(run_query("SELECT * FROM RegularSeason2023 LIMIT 1")) # Test the database connection

    template = """
    Based on the table schema below, generate a valid SQL query that answers the user's question. There are four different types of tables.
    Tables for skaters, goalies, pairings, teams, and lines. Based on the statistical question it can be deduced which one is being asked about. There tables have different queries. These can be found below.
    DO NOT include explanations, comments, code blocks, or duplicate queries. Return only a single SQL query. DO NOT include ```sql or ``` in the response.
    {schema}
    If a request is to return a list of shots allways use the shots_data table. This request wants to return a list of shots given some conditions. This list will be made into a dataframe, so make sure it is returned in a format that can be put into a dataframe.
    If a request is made for shots by toronto maple leafs or shots my leafs players, or something similar, use the shots_data table. Get all shots where the team is the toronto maple leafs.
    Reminder that if a query especially for a table asks for shots between two years that are the same, for example between 2023 and 2023. This means all shots in the 2023 season. Treat this as an equality.
    
    For skaters, lines, pairs, teams, and goalies there is a table for regular season and playoffs in each year. Table names are using the following format:
    - Regular season → <playerType>Stats_regular_<year> 
    - Playoffs → <PlayerType>Stats_playoffs_<year>
    where player type refers to whether the player is a skater, goalie, pairing, line, or team. 

    A query for a shots table will often take the follwing form: return from the shots_data table with all of the columns in the table  intact, Given the conditions: followed by some conditions like "shots by the Florida pathers", 
    In the seasons between (a lower bound) for seasons to (an upper bound for seasons). 
    
    
    For example the query: return from the shots_data table with all of the columns in the table  intact, Given the conditions: shots by the Florida panthers In the seasons between 2023 to 2023.  
    Return the list of shots so they can be put into a dataframe.
    This would be the same as : return a list of all shots taken by the florida panthers in the 2023 season.

    For the year. A user may say 2023-24 or 2023-2024. In this case the season is stored as the first year. So 2023-24 would be 2023.

    If a question is given in present tense, assume the user is asking about 2024-25. If no season is given, assume the user is asking about the 2024-25 season.
    For example if someone asks "Who leads the NHL in Goals" this would be the same as "who lead the NHL in goals in the 2024-25 season"
    If someone does not specify the season type assume the season is regular.

    If someone asks what 'pair', 'defensive pairing', 'd pair', or 'pairing' they mean defensive pairing from the PairStats_regular_<year> or PairStats_playoffs_<year> tables.
    If someone asks what 'line' they mean forward line from the lineStats_regular_<year> or lineStats_playoffs_<year> tables.

    The current season is the 2024-25 season. Use this season for current stats. When no season is provided or it is unclear what season is being refered to, Use 2024. 
    If someone asks, 'what pair leads the NHL in expected goals percentage with at least 50 minutes played" Then this means to query the PairStats_regular_2024 and find the highest expected goals percentage with at least 50 minutes played.
    
    Use correct stat terms:
    - "Even strength" → "5on5", "Power play" → "5on4", "Shorthanded" → "4on5", "All situations" → "All". If strength is not defined use 'all' Do not add the total of multiple strengths together.
    If no strength is defined search in 'all' not all strengths combined. So if someone asks how many goals did a player score. The query should include where situation = 'all'  
    - "Minutes" means "icetime" (store in seconds but return in minutes & seconds). Unless specified otherwise, this means the 'icetime' for the player in situation: 'all'.  
    - "Points" = Goals + Assists.

    Expected goals percentage is a positive statistic. highest/best means the highest percentage.

    Player positions: C = Center, L = Left Wing, R = Right Wing, D = Defenseman.  
    Grouping: Forwards = (C, L, R), Skaters = (C, L, R, D).  

    Someone May request stats from a range of seasons like 'How many goals did Connor Mcdavid score from the 2018-19 season to the 2022-23 season' This means query the db and find the total for Every season in between those two inclusive. 
    In that example then, you would query for the total goals in the 2018, 2019, 2020, 2021, and 2022 seasons.

    When the user requests a total allways use the 'all' situation for the player do not add these up.
    For example, if someone were to ask how many games played a player had in a season, use only the result in 'all' DO NOT ADD THEM with others.

    If a user requests a stat per game, devide the stat by the number of games played in that same time period

    If somone asks for a stat per 60 then find the number of that stat per 60 minutes of icetime. Reminder that icetime is stored in seconds.

    Teams are stored as abbreviations (e.g., "Toronto Maple Leafs" → "TOR"). Infer references like "Leafs" → "TOR".

    When using the shots_data table, the 'isHomeTeam' attribute can be used to determine the team, the shot is either taken by the home team or not. 
    
    Then use the 'homeTeamCode' and 'awayTeamCode' attributes to determine the team. If the home team took the shot, the shot is from the homeTeamCode.

    When querying the shots_data table, the 'isPlayoffGame' attribute can be used to determine if the game is a playoff game or not. This takes the value 1 if it is a playoff game and 0 if it is a regular season game. 
    To determine the strength when querying the shots_data table, use the 'awaySkatersOnIce', 'homeSkatersOnIce' attributes. Use the is_home_team to determine whether the shots are taken by the home or away team. 
    If it is taken by the home team than the homeSkatersOnIce attribute comes first in the strenth. For example, if the shot is taken and isHomeTeam = 1, and awaySkatersOnIce = 4 and homeSkatersOnIce = 5, then the strength is 5on4. The first number corrisponds to the number of players on the ice that took the shot. 
    Use that logic, to change queries to fit with the strength if it is passed asking for a query on the shots_data table.
    

    ALL GOALIE STATS SHOULD ONLY USE ROWS that have the situation 'all' unless otherwise specified. If someone asks what was <goalie name>'s save percentage, use the situation 'all' to find the save percentage. 
    If someone asks for a leader in a statistic for goalies without specifying the situation, this is the leader in rows with the situation 'all'.

    More information on goalies: If a user asks for goals saved above expected, this is the difference between the expected goals against and the actual goals against. or the Xgoals and goals columns. 
    If someone asks for goals saved above expected per 60 minutes, divide the goals saved above expected by the icetime in minutes and multiply by 60.
    if someone asks for goals saved above expected per expected goal faced, devide by the number of expected goals faced.
    If someone asks for save percentage, this is the number of saves divided by the number of shots faced. The number of shots faced is the coloumn 'ongoal' in the goalies tables. The saves is this number minues the goals column. 
    DO NOT USE the danger level columns to make save percentage unless specifically asked for. The abseloute total of shots faced comes from 'ongoal'. To find save percentage, divide this number minus the goals column by itself.
    For example: (ongoal - goals) / ongoal

    DO NOT USE the danger level columns to make save percentage unless specifically asked for. The abseloute total of shots faced comes from 'ongoal'. To find save percentage, divide this number minus the goals column by itself.

    Goals against average, is the goals against divided by the icetime in minutes and multiplied by 60.
    If not specified assume the save percentage is for the situation 'all'.
    When A user says with at least _ shots faced, they mean that the column 'ongoal' has a value greater than or equal to that number

    The team table should only be used when a stat is being asked for an entire team. ie. "what team had the highest shooting percentage in the 2023-24 season." 
    If someone asks who lead a team in a stat, still use the individual tables. Only use this table for team wide stats. Other than that, it is the same as the pairs, skaters, and goalie tables. Follow the same rules as you would for those.

    It is very common that someone may ask for a statistic with at least a number of minutes played. This measn that the player, line, or pair must have played at least that number of minutes. This can be determined with the icetime column. 
    Reminder that this column is stored in seconds. Convert a minumum number of minutes to seconds by multiplying by 60. Use this for the SQL query.

    If someone asks for a top _ in a stat, return the highest _ number in that stat. 
    For example the top 10 lines in expected goals percentage. This means return the top 10 lines from linestats_regular_2024 in expected goals percentage.
    
    DO NOT INCLUDE ``` in the response. Do not include a period at the end of the response.
    Question: {question}
    SQL Query:
    """

    prompt = ChatPromptTemplate.from_template(template)


    # def extract_sql_query(response):
    #     """Extract only the first SQL query and clean any formatting issues."""
    #     print("RAW LLM OUTPUT:\n", response)  # Debugging step

    #     # Strip unnecessary whitespace and formatting
    #     response = response.strip().strip("`")

    #     # Use regex to extract the first valid SQL query
    #     matches = re.findall(r"(?i)(SELECT|INSERT|UPDATE|DELETE|WITH)\s+.*?(;|$)", response, re.DOTALL)

    #     if matches:
    #         return matches[0][0] + response[len(matches[0][0]):].strip()  # Return the first match
    #     else:
    #         return response.strip()  # Fallback to raw response if no match found



    sql_chain = (
        RunnablePassthrough.assign(schema=lambda _: get_table_schema(db))
        | prompt
        | llm
        | StrOutputParser()
        #|(lambda output: extract_sql_query(output)) 
    )
    return sql_chain

def get_chain(db, llm):
    def run_query(query, db):
        return run_query_mysql(query, db)
    
    #database functions. Get information from the databases to be used in the chain
    def get_table_schema(db):
        relevent_tables = ['SkaterStats_regular_2024', 'GoalieStats_regular_2024', 'LineStats_playoffs_2024', 'PairStats_regular_2024', 'teamstats_regular_2024']
        return get_table_info(db, relevent_tables) #return the schema of the first table in the list


    sql_chain = get_sql_chain(db, llm)

    #print(sql_chain.invoke({"question": "How many goals did William Nylander score in the 2018 playoffs"}))
    #print(sql_chain.invoke({"question": "How many goals did Sidney Crosby score in the 2023 regular season?"})) #Test the first chain generating sql query

    template = """
    Based on the table schema below, quesiton, sql query, and sql response, write a natural language response to the user's question.
    {schema}


    Quesiton: {question}
    SQL Query: {query}
    SQL Response: {response}

    Please note that  Save percentage should be presented as a decimal value NOT AS A PERCENTAGE, for example 0.916. There should NEVER be percentage sign. It should have three decimal places.
    So 91.6% would be 0.916. Never return with a percent sign for a goalie. Allways use a decimal value. NEVER use the form 91.6%. ONLY USE 0.916. This is counter intuitive but it is important convention.
    Do this only for save percentage. All other stats that are percentages are fine to return as a percentage. Use decimal only for save percentage. 
    """
    prompt = ChatPromptTemplate.from_template(template)

    full_chain = (
        RunnablePassthrough.assign(query = sql_chain).assign(schema = lambda _: get_table_schema(db)).assign(response=lambda variables: run_query(variables["query"], db))
        | prompt
        | llm
        | StrOutputParser()
    )

    #print(full_chain.invoke({"question": "During the 2023 regular season, what player led the NHL in on ice expected goals for percentage at even strength with a minimum of 100 minutes played. What was that expected goals percentage. How many goals did this player have? What team did he play for?"})) # Test the second chain generating natural language response

    #print(full_chain.invoke({"question": "What player lead the kings in expected goals percentage at even strength with a minimum of 100 minutes during the 2023 regular season? What was that percentage and how many assists did this player have?"})) # Test the second chain generating natural language response
    #print(full_chain.invoke({"question": "who lead the toronto maple leafs in 5 on 5 expected goals percentage with at least 100 minutes played in the 2023 regular season?"}))

    #print(full_chain.invoke({"question": "How many goals did William Nylander score in the 2018 playoffs"}))

    #print(full_chain.invoke({"question": "Who had the highest goals saved above expected in the 2023 regular season"}))

    #print(full_chain.invoke({"question": "What pairing had the highest expected goals percentage with at least 100 minutes in 2023?"}))

    return full_chain
    