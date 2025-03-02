"""
Create a file which tests flow for various run conditions
"""
import os
from langchain.globals import set_verbose
from utils.database_init import  init_vector_db
from chains.rag_chains import get_cba_information, get_rules_information

# Test flow for RAG CBA and Rules

# Test flow for RAG CBA

def test_rag_cba(api_key):
    # Initialize the CBA vector database
    cba_db = init_vector_db('cba', api_key)

    # Test flow for RAG CBA
    query = "What is escrow in the nhl?"
    cba_information = get_cba_information(cba_db, api_key, query)
    print(cba_information)

def test_rag_rules(api_key):
    # Initialize the Rules vector database
    rules_db = init_vector_db('rules', api_key)

    # Test flow for RAG Rules
    query = "What is offside in the nhl?"
    rules_information = get_rules_information(rules_db, api_key, query)
    print(rules_information)

if __name__ == "__main__":
    set_verbose(True)
    api_key = os.getenv("OPENAI_API_KEY")
    print("--------------------------------TEST CBA--------------------------------")
    test_rag_cba(api_key)
    print("--------------------------------TEST CBA DONE--------------------------------")
    print("--------------------------------TEST RULES--------------------------------")
    test_rag_rules(api_key)
    print("--------------------------------TEST RULES DONE--------------------------------")