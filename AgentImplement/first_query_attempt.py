from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Load environment variables
load_dotenv()

# SQLite Database URI
db_uri = "sqlite:///SkatersStats.db"

db = SQLDatabase.from_uri(db_uri)

#print(db.run("SELECT * FROM RegularSeason2023 LIMIT 1")) # Test the database connection



#database functions. Get information from the databases to be used in the chain
def get_table_schema(_):
    return db.get_table_info()

def run_query(query):
    return db.run(query)

#print(run_query("SELECT * FROM RegularSeason2023 LIMIT 1")) # Test the database connection

# Initialize LLM
llm = ChatOpenAI(model_name="gpt-4o")


template = """
Based on the table schema below, generate a valid SQL query that answers the user's question.
DO NOT include explanations, comments, code blocks, or duplicate queries. Return only a single SQL query. DO NOT include ```sql or ``` in the response.
{schema}

The season attribute is in the format of the year the season started. For example, the 2023 regular season would be 2023. The 2023 playoffs would be 2023. The 2023-2024 regular season would be 2023.

The attribute is_playoffs indicates whether the statstic is from the playoffs or not. 0 indicates the regular season and 1 indicates the playoffs. This is also known as the season type.

If a user user asks for a statistics during the playoffs, this means only stats where is_playoffs is 1. If a user asks for a statistic during the regular season, this means only stats where is_playoffs is 0.

Someone may refer to a playoffs as a postseason. This means the same thing as playoffs.

Someone may say the year and then playoffs, for example, who lead the league in goals during the 2023 playoffs. This means the season is 2023 and the season type is playoffs.

If a user does not specify a season type, interpret it as referring to the regular season.
If a user does not specify a season, interpret it as referring to all seasons combined.

If the user asks for an "even strength statistic," interpret it as referring to the situation "5on5".
If the user asks for a "powerplay statistic," interpret it as referring to the situation "5on4".
If the user asks for a "shorthanded statistic," interpret it as referring to the situation "4on5".
If the user asks for an "all situations statistic," interpret it as referring to the situation all of these situations combined.
If the user does not specify even strength, shorthanded, or even strength, interpret it as referring to all situations combined.

Also please not that the attribute team is in short form. This may mean that someone may be asking for a statistic involving a team.
Most of the short forms involve the first letters of the teams city. For example, the Toronto Maple Leafs would be TOR. The Los Angelas Kings would be LAK. The New York Rangers would be NYR.
The New York Islanders would be NYI. The New Jersey Devils would be NJD. The San Jose Sharks would be SJS. The St. Louis Blues would be STL. The Tampa Bay Lightning would be TBL.
The Vancouver Canucks would be VAN. The Vegas Golden Knights would be VGK. The Washington Capitals would be WSH. The Winnipeg Jets would be WPG. The Arizona Coyotes would be ARI. 
The Boston Bruins would be BOS. The Buffalo Sabres would be BUF. The Calgary Flames would be CGY. The Carolina Hurricanes would be CAR. The Chicago Blackhawks would be CHI. 
The Colorado Avalanche would be COL. The Columbus Blue Jackets would be CBJ. The Dallas Stars would be DAL. The Detroit Red Wings would be DET. The Edmonton Oilers would be EDM. 
The Florida Panthers would be FLA. The Minnesota Wild would be MIN. The Montreal Canadiens would be MTL. The Nashville Predators would be NSH. The Ottawa Senators would be OTT. 
The Philadelphia Flyers would be PHI. The Pittsburgh Penguins would be PIT. The Seattle Kraken would be SEA. The Anaheim Ducks would be ANA. The Los Angelas Kings would be LAK. 
The New York Islanders would be NYI. The New Jersey Devils would be NJD. The San Jose Sharks would be SJS. The St. Louis Blues would be STL. The Tampa Bay Lightning would be TBL. The Vancouver Canucks would be VAN. The Vegas Golden Knights would be VGK. The Washington Capitals would be WSH. The Winnipeg Jets would be WPG. The Arizona Coyotes would be ARI. The Boston Bruins would be BOS. The Buffalo Sabres would be BUF. The Calgary Flames would be CGY. The Carolina Hurricanes would be CAR. The Chicago Blackhawks would be CHI. The Colorado Avalanche would be COL. The Columbus Blue Jackets would be CBJ. The Dallas Stars would be DAL. 
The Detroit Red Wings would be DET. The Edmonton Oilers would be EDM. The Florida Panthers would be FLA. The Minnesota Wild would be MIN. The Montreal Canadiens would be MTL.
The Nashville Predators would be NSH. The Ottawa Senators would be OTT. The Philadelphia Flyers would be PHI. The Pittsburgh Penguins would be PIT. The Seattle Kraken would be SEA. 
The Anaheim Ducks would be ANA.

When someone refrences minutes, they mean icetime. This is the amount of total time on ice a player had during the season. This value is measured in seconds. If someone requests minutes, give them the answer as the number of minutes with a remainder of seconds. So for example, 100 seconds would be 2 minutes and 40 seconds.

When someone asks for a statistic with a minimum of a certain number of minutes, this means only include players who have played at least that many minutes. For example, if someone asks for the player with the most goals with a minimum of 100 minutes played, only include players who have played at least 100 minutes.

Expected goals are a positive statistic when measuring performance, and also expected goals percentage, also known as expected goals share is desired to be as high as possible. If someone asks who leads a team in expected goals precentage, find the highest percentage that meets the requirements put into the prompt.

When someone asks for expected goals or expected goals percentage, unless they specify otherwise, they are asking for even strength expected goals or expected goals percentage.

Also notice that the position attribute is in short form. This means that someone may be asking for a statistic involving a position. The short forms are as follows:
C is short for Center. L is short for Left Wing. R is short for Right Wing. D is short for Defense. Someone may also group both left wing and right wing as wingers.
Someone may refer to a player as a center. This means they are of position C. Similarly they may ask for a defemsman. This means they are of position D. They may also ask for a winger. This means they are of position L or R. They may also ask for a forward. 
This means they are of position C, L, or R. They may also ask for a skater. This means they are of position C, L, R, or D.
 
If a question is provided asking for the player who had the highest or lowest of a statistic in addition to providing the player, provide the value of the statistic as well.


THE MOST IMPORTANT THING: DO NOT include explanations, comments, code blocks, or duplicate queries. Return only a single SQL query. DO NOT include ```sql or ``` in the response.
ONLY PROVIDE A SINGLE SQL QUERY. DO NOT INCLUDE ANYTHING ELSE.

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
    RunnablePassthrough.assign(schema=get_table_schema)
    | prompt
    | llm
    | StrOutputParser()
    #|(lambda output: extract_sql_query(output)) 
)

#print(sql_chain.invoke({"question": "How many goals did Sidney Crosby score in the 2023 regular season?"})) #Test the first chain generating sql query

template = """
Based on the table schema below, quesiton, sql query, and sql response, write a natural language response to the user's question.
{schema}


Quesiton: {question}
SQL Query: {query}
SQL Response: {response}

"""

prompt = ChatPromptTemplate.from_template(template)

full_chain = (
    RunnablePassthrough.assign(query = sql_chain).assign(schema=get_table_schema, response=lambda variables: run_query(variables["query"]))
    | prompt
    | llm
    | StrOutputParser()
)

#print(full_chain.invoke({"question": "During the 2023 regular season, what player led the NHL in on ice expected goals for percentage at even strength with a minimum of 100 minutes played. What was that expected goals percentage. How many goals did this player have? What team did he play for?"})) # Test the second chain generating natural language response

#print(full_chain.invoke({"question": "What player lead the kings in expected goals percentage at even strength with a minimum of 100 minutes during the 2023 regular season? What was that percentage and how many assists did this player have?"})) # Test the second chain generating natural language response
#print(full_chain.invoke({"question": "who lead the toronto maple leafs in 5 on 5 expected goals percentage with at least 100 minutes played in the 2023 regular season?"}))

def get_chain():
    return full_chain