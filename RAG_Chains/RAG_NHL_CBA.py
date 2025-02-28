import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from data.database_init import init_cba_db

# print("\n--- Relevant Documents ---")
# for i, doc in enumerate(relevant_docs, 1):
#     print(f"Document {i}:\n{doc.page_content}\n")
#     if doc.metadata:
#         print(f"Source: {doc.metadata.get('source', 'Unknown')}\n")

def get_cba_information(vector_db, api_key, query: str) -> str:
    
    model = ChatOpenAI(model="gpt-4o", api_key = api_key)

    retriever = vector_db.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={'k': 3, "score_threshold": 0.01}
    )
    
    relevant_docs = retriever.invoke(query)

    combined_input = (
    "Here are some documents that might help answer the question: "
    + query
    + "\n\nRelevant Documents:\n"
    + "\n\n".join([doc.page_content for doc in relevant_docs])
    + "\n\nPlease provide an answer based only on the provided documents. If the answer is not found in the documents, respond with 'I'm not sure'. Please include the part of the CBA being referenced when it is used."
    )
    messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content=combined_input),
    ]
    return model.invoke(messages).content