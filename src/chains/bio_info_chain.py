from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.globals import set_verbose
from utils.database_init import get_table_info, run_query_mysql, init_db

# Load environment variables
load_dotenv()

set_verbose(True)
# TODO: Can make SQL chains more modular
def run_query(query, db):
        return run_query_mysql(query, db)

def get_table_schema(db):
        relevent_tables = ['BIO_Info']
        return get_table_info(db, relevent_tables) #return the schema of the first table in the list

def get_bio_chain(db, llm):

    template = """
    Based on the table schema below, generate a valid SQL query that answers the user's question. Generate only the query do not say sql ``` before the query.
    {schema}

    Player positions: C = Center, L = Left Wing, R = Right Wing, D = Defenseman, G = Goalies.  
    Note that the title 'forward' refers to all players who are have the position, C, L, or R
    Teams are stored as abbreviations (e.g., "Toronto Maple Leafs" → "TOR"). Infer references like "Leafs" → "TOR".

    The shootsCatches attribute indicates which way a player shoots if it is a skater (C, L, R, D). This can also be refered to as handedness. For each player this is right or left.
    A user may ask which way a player shoots, return the side indicated in shootsCatches

    For goalies (G) someone may ask which way they catch instead of shoot. This is indicated in shootsCatches
    For goalies, this can also be refered to as southpaw (aka right), or regular (aka left).

    Nations are stored as abbreviations (e.g., "Canada" -> CAN). Infer references like "Canadian" -> CAN
    Also When someone asks for a list of where someone ranks. Order by that value, like height or weight and then return the row number.
    This may come with some conditions, like currently playing. Someone also may ask for all the of the top players in that, or bottom ect.
    DO NOT INCLUDE ``` in the response.
    Question: {question}
    SQL Query:
    """
    prompt = ChatPromptTemplate.from_template(template)

    sql_chain = (
        RunnablePassthrough.assign(schema=lambda _: get_table_schema(db))
        | prompt
        | llm
        | StrOutputParser()
    )
    #return sql_chain
    template = """
    Based on the table schema below, quesiton, sql query, and sql response, write a natural language response to the user's question.
    {schema}


    Quesiton: {question}
    SQL Query: {query}
    SQL Response: {response}

    """
    prompt = ChatPromptTemplate.from_template(template)

    full_chain = (
        RunnablePassthrough.assign(query = sql_chain).assign(schema = lambda _: get_table_schema(db)).assign(response=lambda variables: run_query(variables["query"], db))
        | prompt
        | llm
        #| StrOutputParser()
    )
    return full_chain

#print(full_chain.invoke({"question": "How tall is Auston Matthews?"}))

# temp_db = init_db()

# #print(get_table_schema(temp_db))

# #print(run_query('SELECT * FROM BIO_Info LIMIT 10;', temp_db))

# temp_chain = get_bio_chain(temp_db)
# print("Running full chain with question: 'How tall is Auston Matthews?'")
# print(temp_chain.invoke({"question": "How tall is Auston Matthews?"}))
