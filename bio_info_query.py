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


def get_table_schema(_):
    relevent_tables = ['BIO_Info']
    return db.get_table_info(relevent_tables) #return the schema of the first table in the list

def run_query(query):
    return db.run(query)

llm = ChatOpenAI(model_name="gpt-4o")

template = """
Based on the table schema below, generate a valid SQL query that answers the user's question. Generate only the query do not say sql ``` before the query.
{schema}

Player positions: C = Center, L = Left Wing, R = Right Wing, D = Defenseman, G = Goalies.  

Teams are stored as abbreviations (e.g., "Toronto Maple Leafs" → "TOR"). Infer references like "Leafs" → "TOR".

The shootsCatches attribute indicates which way a player shoots if it is a skater (C, L, R, D). This can also be refered to as handedness. For each player this is right or left.
A user may ask which way a player shoots, return the side indicated in shootsCatches

For goalies (G) someone may ask which way they catch instead of shoot. This is indicated in shootsCatches
For goalies, this can also be refered to as southpaw (aka right), or regular (aka left).

Nations are stored as abbreviations (e.g., "Canada" -> CAN). Infer references like "Canadian" -> CAN

DO NOT INCLUDE ``` in the response.
Question: {question}
SQL Query:
"""
prompt = ChatPromptTemplate.from_template(template)

sql_chain = (
    RunnablePassthrough.assign(schema=get_table_schema)
    | prompt
    | llm
    | StrOutputParser()
)

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

#print(full_chain.invoke({"question": "How tall is Auston Matthews?"}))
def get_bio_chain():
    return full_chain