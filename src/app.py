from dotenv import load_dotenv
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
import os
import argparse
from agent.agent_main import get_agent
from utils.database_init import init_db, init_cba_db, init_rules_db

parser = argparse.ArgumentParser()
# Use local environment variables by default
parser.add_argument("--local", action="store_false", help="Use local environment variables") 

# TODO: make function cleaner, remove duplicate code, naming
def get_secrets_or_env(local):
    if local:
        load_dotenv()
        MYSQL_HOST = os.getenv("MYSQL_HOST")
        MYSQL_USER = os.getenv("MYSQL_USER")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
        MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
        open_ai_key = os.getenv("OPENAI_API_KEY")
    else:
        MYSQL_HOST = st.secrets["MYSQL_HOST"]
        MYSQL_USER = st.secrets["MYSQL_USER"]
        MYSQL_PASSWORD = st.secrets["MYSQL_PASSWORD"]
        MYSQL_DATABASE = st.secrets["MYSQL_DATABASE"]
        open_ai_key = st.secrets["OPENAI_API_KEY"]
    return MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, open_ai_key

if "database" not in st.session_state:
    args = parser.parse_args()
    MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, open_ai_key = get_secrets_or_env(args.local)
    
    db = init_db(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE)
    rules_db = init_rules_db(open_ai_key)
    cba_db = init_cba_db(open_ai_key)

if "agent_chain" not in st.session_state:
    NHLStatsAgent = get_agent(db, rules_db, cba_db, open_ai_key)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        AIMessage(content="Welcome to the NHL Stats Chatbot! Ask me anything about NHL statistics and I will do my best to answer your questions!")
    ]

st.set_page_config(page_title="NHL Stats Chatbot", page_icon="🏒", layout="wide")

st.title("NHL Stats Chatbot")

# Display the chat history
for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.markdown(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human"):
            st.markdown(message.content)

# Handle user input and update the chat history
user_query = st.chat_input("Type a message...")
if user_query is not None and user_query.strip() != "":
    # Add human message to history
    st.session_state.chat_history.append(HumanMessage(content=user_query))

    with st.chat_message("Human"):
        st.markdown(user_query)

    # Get response from the agent, passing the chat history
    with st.chat_message("AI"):
        # Pass the entire chat history to the agent
        agent_input = "\n".join([message.content for message in st.session_state.chat_history])  # Join all messages
        response = NHLStatsAgent.invoke({"input": agent_input})

        # Check that the response contains the expected 'output' key
        if isinstance(response, dict) and "output" in response:
            ai_response = response["output"]
            st.markdown(ai_response)
            
            # Append AI response to chat history
            st.session_state.chat_history.append(AIMessage(content=ai_response))

            # Check if the user query specifically requests a scatterplot
            if "scatterplot" in user_query.lower():  # Case insensitive check for 'scatterplot'
                scatterplot_path = "generated_images/scatterplot.png"
                if os.path.exists(scatterplot_path):
                    # Display the scatterplot image
                    st.image(scatterplot_path)
        else:
            # Handle the case where the response is not as expected
            st.markdown("Sorry, I couldn't understand that request. Please try again.")
