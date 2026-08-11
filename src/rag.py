import json
import os
import dotenv
from langchain_core.documents import Document
from langchain_cohere import CohereEmbeddings, ChatCohere
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough


dotenv.load_dotenv()
key = os.getenv("COHERE_API_KEY")
def load_json_documents(json_file_path):

    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = [data]
    documents = []
    for item in data:
        page_text = (
            f"Title: {item.get('title', '')}\n"
            f"Content: {item.get('content', '')}"
        )
        metadata = {
            "doc_id": item.get("doc_id"),
            "title": item.get("title"),
            "category": item.get("category"),
            "language": item.get("language"),
            "sentiment": item.get("sentiment"),
        }
        documents.append(
            Document(
                page_content=page_text,
                metadata=metadata
            )
        )
    return documents

documents = load_json_documents("processed_knowledge_base.json")
print("Number of documents:", len(documents))

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)

chunks = text_splitter.split_documents(documents)
print("Number of chunks:", len(chunks))


embeddings = CohereEmbeddings(
    model="embed-v4.0",
    cohere_api_key=key
)

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    collection_name="json_rag"
)


retriever = vectorstore.as_retriever(
    search_kwargs={"k": 5}
)

llm = ChatCohere(
    model="command-a-03-2025",
    temperature=0,
    cohere_api_key=key
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a telecom customer-support assistant.
    Answer the customer's question using only the provided context.
    If the context does not contain the answer, say "I don't know."
    If the User enter any strange charachter without question , say "you maybe have a question but you didn't write anything!"
    Be concise, clear, and helpful.
    Do not invent information.
    Respond in the same language as the customer's question.

    Context:
    {context}"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{question}")
])


def format_docs(docs):
    return "\n\n".join(doc.page_content
                       for doc in docs)

rag_chain = (
RunnablePassthrough.assign(
        context=lambda x: format_docs(retriever.invoke(x["question"]))
    )
    | prompt
    | llm
)


def ask_question(question,chat_history=[]):
    response = rag_chain.invoke({
        "question": question,
        "chat_history": chat_history
    })
    return response.content

def get_sources(question):
    docs = retriever.invoke(question)
    return docs