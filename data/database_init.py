import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import errorcode

# Load environment variables
load_dotenv()

# Retrieve MySQL credentials from .env
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

def init_db():
    """Initialize and return the database connection"""
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        ssl_disabled=True
    )

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