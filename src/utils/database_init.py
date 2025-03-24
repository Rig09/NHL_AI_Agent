import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import errorcode
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
import os
import pandas as pd
# __import__('pysqlite3')
# import sys
# sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

# Retrieve MySQL credentials from .env

# Load environment variables from the .env file
# load_dotenv()
# MYSQL_HOST = os.getenv("MYSQL_HOST")
# MYSQL_USER = os.getenv("MYSQL_USER")
# MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
# MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
# open_ai_key = os.getenv("OPENAI_API_KEY")

model = ChatOpenAI(model="gpt-4o")

def init_db(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD,MYSQL_DATABASE):
    """Initialize and return the database connection"""
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        ssl_disabled=True
    )

def find_persistent_dir(db_name):
    """Find the persistent directory for vector database storage.
    
    Args:
        db_name (str): Name of the database ('cba' or 'rules')
        
    Returns:
        str: Path to the persistent directory
        
    Raises:
        FileNotFoundError: If the chroma.sqlite3 file is not found in the directory
    """
    assert db_name in ['cba', 'rules']
    
    # Get the directory containing the current file
    base_dir = os.path.abspath(os.path.dirname(__file__))
    
    # Go up one level to the src directory
    src_dir = os.path.dirname(base_dir)
    
    # Go up one more level to the project root
    root_dir = os.path.dirname(src_dir)
    
    # Create path to the vector db directory
    persistent_dir = os.path.join(root_dir, 'data', 'rag', db_name, 'chroma_db')
    
    # Check if the directory exists
    if not os.path.exists(persistent_dir):
        raise FileNotFoundError(f"Vector database directory not found at {persistent_dir}. Please ensure you have initialized the vector database.")
    
    # Check for chroma.sqlite3 file
    sqlite_file = os.path.join(persistent_dir, 'chroma.sqlite3')
    if not os.path.exists(sqlite_file):
        raise FileNotFoundError(
            f"Chroma database file not found at {sqlite_file}. "
            "Please ensure you have initialized the vector database by running the embedding creation script first."
        )
    
    return persistent_dir

def init_vector_db(db_name, api_key):
    assert db_name in ['cba', 'rules']
    persistent_dir = find_persistent_dir(db_name)
    return Chroma(persist_directory=persistent_dir, embedding_function=OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key))
    

def get_table_info(db_connection, table_names=None):
    """Retrieve schema information for specific tables or list all tables."""
    cursor = db_connection.cursor(dictionary=True)

    try:
        if table_names:
            if isinstance(table_names, list):
                # For each table in the list, fetch its column information
                table_schemas = {}
                for table_name in table_names:
                    query = f"""
                        SELECT COLUMN_NAME, DATA_TYPE
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_NAME = '{table_name}' AND TABLE_SCHEMA = DATABASE()
                    """
                    cursor.execute(query)
                    result = cursor.fetchall()
                    table_schemas[table_name] = result  # Store the schema for each table in a dictionary
                return table_schemas  # Returns a dictionary with table names as keys and column info as values
            else:
                # If a single table name is passed (non-list), behave as before
                query = f"""
                    SELECT COLUMN_NAME, DATA_TYPE
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME = '{table_names}' AND TABLE_SCHEMA = DATABASE()
                """
                cursor.execute(query)
                result = cursor.fetchall()
                return {table_names: result}  # Returns schema for the specified single table
        else:
            query = """
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
            """
            cursor.execute(query)
            result = cursor.fetchall()
            return result  # Returns list of tables in the database
    finally:
        cursor.close()

# db = init_db()
# # Get schema for a list of tables (e.g., 'players' and 'games')
# tables_schema = get_table_info(db, ['skaterstats_regular_2023', 'goaliestats_regular_2023'])
# print("Schemas for 'players' and 'goalie' tables:", tables_schema)
def run_query_mysql(query, db_connection):
    """Run a query on the MySQL database and return the result."""
    
    # Establish a cursor to execute the query
    cursor = db_connection.cursor(dictionary=True)  # dictionary=True to return results as dictionaries
    
    try:
        # Execute the query
        cursor.execute(query)
        
        # If it's a SELECT query, fetch the results
        if query.strip().lower().startswith("select"):
            result = cursor.fetchall()  # Fetch all rows
        else:
            result = None  # For non-SELECT queries (INSERT, UPDATE, DELETE)
            db_connection.commit()  # Commit changes for non-SELECT queries (e.g., INSERT, UPDATE)
        
        return result
    
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None
    
    finally:
        # Close the cursor to free up resources
        cursor.close()