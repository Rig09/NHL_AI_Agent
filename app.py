from dotenv import load_dotenv
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from First_agent import get_agent
import time
import os

load_dotenv()


# @st.cache_resource
# def load_agent():
#     from First_agent import get_agent  # Import inside function to avoid reload issues
#     return get_agent()

NHLStatsAgent = get_agent()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        AIMessage(content="Welcome to the NHL Stats Chatbot! Ask me anything about NHL statistics and I will do my best to answer your questions!")
    ]

st.set_page_config(page_title="NHL Stats Chatbot", page_icon="🏒", layout="wide")

st.title("NHL Stats Chatbot")

for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.markdown(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human"):
            st.markdown(message.content)

user_query = st.chat_input("Type a message...")
if user_query is not None and user_query.strip() != "":
    st.session_state.chat_history.append(HumanMessage(content=user_query))

    with st.chat_message("Human"):
        st.markdown(user_query)

    with st.chat_message("AI"):
        response = NHLStatsAgent.invoke({"input": user_query})
        st.markdown(response["output"])
        
        # Check if the user query specifically requests a scatterplot
        if "scatterplot" in user_query.lower():  # Case insensitive check for 'scatterplot'
            if os.path.exists("generated_images/scatterplot.png"):
                #time.sleep(2)  # Adjust as needed
                
                # Display the scatterplot image
                st.image("generated_images/scatterplot.png")
        
        st.session_state.chat_history.append(AIMessage(content=response["output"]))
