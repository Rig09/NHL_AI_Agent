from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.globals import set_verbose

# Load environment variables
load_dotenv()

set_verbose(True)

# SQLite Database URI
db_uri = "sqlite:///SkatersStats.db"

db = SQLDatabase.from_uri(db_uri)

#print(db.run("SELECT * FROM RegularSeason2023 LIMIT 1")) # Test the database connection



#database functions. Get information from the databases to be used in the chain
def get_table_schema(_):
    relevent_tables = ['SkaterStats_regular_2023']
    return db.get_table_info(relevent_tables) #return the schema of the first table in the list

def run_query(query):
    return db.run(query)

#print(run_query("SELECT * FROM RegularSeason2023 LIMIT 1")) # Test the database connection

# Initialize LLM
llm = ChatOpenAI(model_name="gpt-4o", max_tokens=300)


template = """
Based on the table schema below, generate a valid SQL query that answers the user's question. All tables have the same schema.
DO NOT include explanations, comments, code blocks, or duplicate queries. Return only a single SQL query. DO NOT include ```sql or ``` in the response.
{schema}

There is a table for regular season and playoffs in each year. Table names are using the following format:
- Regular season → SkaterStats_regular_<year>  
- Playoffs → SkaterStats_playoffs_<year>  

Use correct stat terms:
- "Even strength" → "5on5", "Power play" → "5on4", "Shorthanded" → "4on5", "All situations" → "All". If strength is not defined use 'all' Do not add the total of multiple strengths together.
If no strength is defined search in 'all' not all strengths combined. So if someone asks how many goals did a player score. The query should include where situation = 'all'  
- "Minutes" means "icetime" (store in seconds but return in minutes & seconds). Unless specified otherwise, this means the 'icetime' for the player in situation: 'all'.  
- "Points" = Goals + Assists.


Player positions: C = Center, L = Left Wing, R = Right Wing, D = Defenseman.  
Grouping: Forwards = (C, L, R), Skaters = (C, L, R, D).  

Teams are stored as abbreviations (e.g., "Toronto Maple Leafs" → "TOR"). Infer references like "Leafs" → "TOR". VIDE THE QUERY.
DO NOT INCLUDE ``` in the response.
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

#print(sql_chain.invoke({"question": "How many goals did William Nylander score in the 2018 playoffs"}))
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

#print(full_chain.invoke({"question": "How many goals did William Nylander score in the 2018 playoffs"}))
def get_chain():
    return full_chain