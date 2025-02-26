import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

load_dotenv()

model = ChatOpenAI(model="gpt-4o")

current_dir = os.path.dirname(os.path.realpath(__file__))
persistent_dir = os.path.join(current_dir, 'data', 'PDFS', 'chroma_db')

db = Chroma(persist_directory=persistent_dir, embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"))

# print("\n--- Relevant Documents ---")
# for i, doc in enumerate(relevant_docs, 1):
#     print(f"Document {i}:\n{doc.page_content}\n")
#     if doc.metadata:
#         print(f"Source: {doc.metadata.get('source', 'Unknown')}\n")

retriever = db.as_retriever(
search_type="similarity_score_threshold",
search_kwargs={'k': 3, "score_threshold": 0.2}
)

        
def get_rules_information(query: str) -> str:
    relevant_docs = retriever.invoke(query)

    combined_input = (
    "Here are some documents that might help answer the question: "
    + query
    + "\n\nRelevant Documents:\n"
    + "\n\n".join([doc.page_content for doc in relevant_docs])
    + "\n\nPlease provide an answer based only on the provided documents. If the answer is not found in the documents, respond with 'I'm not sure'. Please include the rule number and a small piece of that rule if a rule is being referenced."
    )
    messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content=combined_input),
    ]
    return model.invoke(messages).content

#sample function call
#print(get_rules_information("Can you kick a puck into the net?"))
