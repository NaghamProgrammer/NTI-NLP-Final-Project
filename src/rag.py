import json
import os
import dotenv
from langchain_core.documents import Document
from langchain_cohere import CohereEmbeddings, ChatCohere
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain_core.messages import HumanMessage, AIMessage


dotenv.load_dotenv()
key = os.getenv("COHERE_API_KEY")

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

VALID_CATEGORIES = {"Technical_Solutions", "Billing_Policies", "Customer_Calls_Dataset"}


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

documents = load_json_documents(r"data\processed\processed_knowledge_base.json")
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

Use the provided context to answer the customer's question when possible.
Be concise, clear, and helpful. Do not invent information.
Respond in the same language as the customer's question.

Respond ONLY with a valid JSON object (no markdown, no code fences, no extra
text before or after it) with exactly these fields:
- "status": one of "answered", "clarify", "no_solution", "unknown", "irrelevant"
- "answer": the text to show the customer
- "category": one of "Technical_Solutions", "Billing_Policies",
  "Customer_Calls_Dataset", or null

Rules for choosing "status":

- "answered": the context contains the answer to the customer's question.
  Set "answer" to that answer. Set "category" to null.

- "clarify": the customer has raised a real support topic, but their
  message is too vague to tell what's actually going on, OR the customer
  is just saying hello, greeting you, or making casual small talk.
  Do NOT escalate yet. Set "answer" to a polite greeting or one short,
  specific clarifying question. Set "category" to null.

- "no_solution": escalate to a technician. Use this ONLY when the
  customer's issue (once specific enough to judge) clearly matches one of
  the escalation scenarios listed below for its category, AND the context
  does not already resolve it. Set "answer" to a short message telling
  the customer you could not find a self-service solution and their issue
  will be forwarded to a technician. Set "category" to the matching
  department:

  * "Technical_Solutions" — escalate for things a customer or the bot
    cannot fix remotely, such as: a physically cut, damaged, or exposed
    cable/line; complete loss of signal or dial tone after basic
    troubleshooting doesn't apply; a modem/router that is physically
    broken or needs on-site replacement; a suspected outage affecting a
    specific address/area; a new line or equipment installation.
  * "Billing_Policies" — escalate for things that need a human with
    account access, such as: a disputed or incorrect charge that needs
    manual investigation; a refund request; money deducted without the
    expected result (e.g. failed payment still charged); a plan/contract
    change that requires backend approval.
  * "Customer_Calls_Dataset" — escalate for things needing a human agent,
    such as: a formal complaint the customer wants escalated; a service
    cancellation or account closure request; a legal/regulatory
    complaint; the customer explicitly asking to speak to a person after
    the bot couldn't help.

- "unknown": the question is a genuine telecom support topic and specific
  enough to judge, the context does not contain the answer, but it does
  NOT match any of the escalation scenarios above. In this case do NOT
  escalate — just set "answer" to "I don't know." Set "category" to null.

- "irrelevant": the question is unrelated to telecom customer support
  altogether (e.g. general knowledge questions), OR the user entered
  strange characters / no real question. Set "answer" to "I don't know."
  (or, for the no-real-question case, "you maybe have a question but you
  didn't write anything!"). Set "category" to null.

Escalation is the exception, not the default: only use "no_solution" when
the issue clearly matches a listed scenario. Everything else the context
doesn't cover should be "unknown" (or "clarify" if too vague to judge
yet), never a silent escalation.

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


def _strip_code_fence(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    return raw.strip()


def ask_question(question, chat_history=None):

    if chat_history is None:
        chat_history = []

    response = rag_chain.invoke({
        "question": question,
        "chat_history": chat_history
    })

    raw = _strip_code_fence(response.content)
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):

        parsed = {"status": "answered", "answer": raw, "category": None}

    status = parsed.get("status", "answered")
    if status not in ("answered", "clarify", "no_solution", "unknown", "irrelevant"):
        status = "answered"

    category = parsed.get("category")
    if category not in VALID_CATEGORIES:
        category = None

    return {
        "status": status,
        "answer": parsed.get("answer", raw),
        "category": category,
    }


def get_sources(question):
    docs = retriever.invoke(question)
    return docs




def load_technicians(json_file_path="technicians.json"):
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("technicians", [])


def get_technician_by_category(category, json_file_path="technicians.json"):
    """Returns the first technician matching the category, or a fallback
    technician if no exact match is found."""
    technicians = load_technicians(json_file_path)
    if not technicians:
        return None
    matches = [t for t in technicians if t.get("category") == category]
    return matches[0] if matches else technicians[0]


def _format_conversation(chat_history, question):
    lines = []
    for msg in chat_history:
        if isinstance(msg, HumanMessage):
            lines.append(f"Customer: {msg.content}")
        elif isinstance(msg, AIMessage):
            lines.append(f"Assistant: {msg.content}")
    lines.append(f"Customer: {question}")
    return "\n".join(lines)


def send_escalation_email(technician, question, category, chat_history=None, contact=None):

    if not technician:
        return False, "No technician available for this category."
    if not SENDER_EMAIL or not SENDER_APP_PASSWORD:
        return False, "Sender email credentials are not configured (check .env)."

    conversation_summary = _format_conversation(chat_history or [], question)
    category_label = (category or "General").replace("_", " ")
    contact_line = f"Contact the customer at: {contact}" if contact else "Customer contact info: not provided."

    subject = f"[Support Escalation] {category_label} — Unresolved Customer Issue"
    body = (
        f"Hello {technician.get('name', '')},\n\n"
        f"Our AI support assistant was unable to find a solution for a "
        f"customer issue in the \"{category_label}\" category and is "
        f"escalating it to you for review.\n\n"
        f"{contact_line}\n\n"
        f"Conversation summary:\n"
        f"{conversation_summary}\n\n"
        f"Please follow up on this issue at your earliest convenience.\n\n"
        f"Best regards,\n"
        f"Telecom Support AI"
    )

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = technician["email"]
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, technician["email"], msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)