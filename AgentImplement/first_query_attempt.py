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
db_uri = "sqlite:///2023RegularSeason.db"

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

#print(full_chain.invoke({"question": "How many goals did Sidney Crosby score in the 2023 regular season?"})) # Test the second chain generating natural language response

def get_chain():
    return full_chain