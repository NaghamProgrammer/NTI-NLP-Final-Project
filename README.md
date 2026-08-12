# KhedmaBot — AI-Powered Telecom Customer Support

**KhedmaBot** is an AI-powered customer support assistant designed to help telecom customers resolve billing and technical issues through natural language conversations.

Built as an **NLP and Retrieval-Augmented Generation (RAG)** project, KhedmaBot retrieves relevant information from a telecom knowledge base and uses a Cohere language model to generate accurate, context-aware responses.

KhedmaBot supports **English and Arabic**, provides retrieved sources, collects customer feedback, and can escalate unresolved issues to human technicians.

---

## Features

* **AI Customer Support** : Conversational assistant for telecom customers
* **RAG-based Question Answering** : Answers are grounded in the telecom knowledge base
* **Multilingual Support** : Supports both English and Arabic
* **Billing Support** : Handles questions about plans, billing cycles, upgrades, downgrades, prorated charges, and discounts
* **Technical Support** : Provides troubleshooting steps for common internet and Wi-Fi problems
* **Source Retrieval** : Displays relevant knowledge-base information used for the response
* **Smart Escalation** : Identifies issues that require human intervention
* **Technician Notifications** : Can send unresolved cases to technicians through email
* **Customer Feedback** : Collects positive and negative feedback
* **Analytics Dashboard** : Tracks customer satisfaction and feedback
* **Conversation History** : Maintains the context of the conversation

---

## How KhedmaBot Works

KhedmaBot uses a **Retrieval-Augmented Generation (RAG)** pipeline instead of relying solely on the language model's general knowledge.

```text
                 Customer Question
                        │
                        ▼
              ┌───────────────────┐
              │   KhedmaBot       │
              │  Chat Interface   │
              └─────────┬─────────┘
                        │
                        ▼
              ┌───────────────────┐
              │ Semantic Search   │
              │     Chroma        │
              └─────────┬─────────┘
                        │
                        ▼
              ┌───────────────────┐
              │ Relevant Context  │
              │   Top 5 Chunks    │
              └─────────┬─────────┘
                        │
                        ▼
              ┌───────────────────┐
              │    Cohere LLM     │
              │    Generation     │
              └─────────┬─────────┘
                        │
                        ▼
              ┌───────────────────┐
              │    KhedmaBot      │
              │     Response     │
              └─────────┬─────────┘
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
         Answered              Escalation
                                   │
                                   ▼
                              Technician
```

### RAG Pipeline

```text
Knowledge Base
      ↓
Load JSON
      ↓
LangChain Documents
      ↓
Text Splitting
      ↓
Cohere Embeddings
      ↓
Chroma Vector Store
      ↓
Semantic Retrieval
      ↓
Top 5 Relevant Chunks
      ↓
Prompt + Retrieved Context
      ↓
Cohere LLM
      ↓
Generated Response
```

The current implementation uses:

* **Cohere ****`embed-v4.0`** for embeddings
* **Cohere ****`command-a-03-2025`** for response generation
* **Chroma** as the vector database
* **LangChain** for the RAG pipeline
* **Top 5** retrieved documents
* Chunk size of **800**
* Chunk overlap of **100**

---

## Multilingual Support

KhedmaBot is designed to handle both **English and Arabic** customer questions.

The assistant is instructed to respond in the **same language used by the customer**.

### English

```text
What happens when I change my plan in the middle of a billing cycle?
```

### Arabic

```text
ماذا يحدث إذا غيرت الباقة أثناء دورة الفاتورة؟
```

KhedmaBot should retrieve the relevant information and respond in the corresponding language.

---

## Billing Support

KhedmaBot can answer questions related to:

* Changing plans
* Upgrading and downgrading
* Billing cycles
* Prorated charges
* Unused days
* Promotional discounts
* Additional fees
* Credits
* Unexpected bills

Example:

```text
Why is my first bill after upgrading higher than my normal monthly bill?
```

---

## Technical Support

KhedmaBot can help customers troubleshoot common connectivity problems such as:

* Internet disconnections
* Slow Wi-Fi
* Router problems
* Device-specific connection issues
* Repeated connection drops
* Internet connection failures

Example:

```text
My internet keeps disconnecting. What should I do?
```

---

## Intelligent Escalation

Not every customer problem can be solved automatically.

KhedmaBot classifies customer requests and determines whether they can be answered using the available knowledge base or require human intervention.

Possible response statuses include:

```text
answered
clarify
no_solution
unknown
irrelevant
```

### `answered`

The knowledge base contains enough information to answer the customer's question.

### `clarify`

More information is required from the customer before providing a solution.

### `no_solution`

The issue requires human intervention and can be escalated to a technician.

### `unknown`

The question is related to the domain but the knowledge base does not contain enough information to answer it.

### `irrelevant`

The question is unrelated to telecom customer support.

---

## Technician Escalation

When an issue requires human intervention, KhedmaBot can escalate the case to a technician.

The system can:

1. Identify the issue category.
2. Determine the appropriate technician.
3. Collect the relevant customer information.
4. Build a summary of the conversation.
5. Send an email notification through SMTP.

This allows KhedmaBot to act as more than a simple chatbot: it can serve as the first layer of a customer-support workflow.

---

## Customer Feedback

Customers can provide feedback on KhedmaBot's responses using positive or negative ratings.

Feedback is stored locally in:

```text
feedback_logs.jsonl
```

The system records information such as:

* Customer question
* Assistant response
* Sentiment

This feedback can then be analyzed through the dashboard.

---

## Analytics Dashboard

KhedmaBot includes a separate Streamlit dashboard for monitoring customer feedback.

The dashboard provides:

* Total feedback
* Positive feedback
* Negative feedback
* Satisfaction rate
* Satisfaction charts
* Negative-feedback cases
* Feedback logs

---

## Project Structure

```text
KhedmaBot/
│
├── app/
│   ├── app.py
│   └── dashboard.py
│
├── data/
│   ├── raw/
│   │   └── knowledge_base.json
│   │
│   └── processed/
│       └── processed_knowledge_base.json
│
├── src/
│   ├── main.py
│   ├── rag.py
│   └── process_knowledge_base.py
│
├── static/
│   ├── index.html
│   ├── dashboard.html
│   ├── app.js
│   ├── style.css
│   ├── Vector@2x.png
│   └── el_speaker.png
│
├── requirements.txt
└── README.md
```

---

## Installation

## 1. Clone the repository

```bash
git clone https://github.com/NaghamProgrammer/NTI-NLP-Final-Project.git
cd NTI-NLP-Final-Project
```

## 2. Create a virtual environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
COHERE_API_KEY=your_cohere_api_key

SENDER_EMAIL=your_email@gmail.com
SENDER_APP_PASSWORD=your_gmail_app_password

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### Required

The `COHERE_API_KEY` is required for:

* Generating embeddings
* Generating chatbot responses

### Optional

The SMTP variables are required only if you want to use technician email escalation.

> ⚠️ Never commit your `.env` file or API keys to GitHub.

Add the following to `.gitignore`:

```text
.env
venv/
__pycache__/
feedback_logs.jsonl
```

---

## Running KhedmaBot

KhedmaBot contains a **FastAPI backend** and a **Streamlit application**.

## Run the FastAPI Backend

### Important

Run the command from the **project root**, not from inside `src/`.

Your terminal should be located at:

```text
NTI-NLP-Final-Project/
```

Then run:

```bash
uvicorn src.main:app --reload
```

The backend will start at:

```text
http://127.0.0.1:8000
```

You can also open:

```text
http://localhost:8000
```

### Why `src.main:app`?

The FastAPI application is located at:

```text
src/main.py
```

and the FastAPI instance inside it is:

```python
app = FastAPI(...)
```

Therefore, from the project root, Uvicorn uses:

```text
src.main:app
```

which means:

```text
src → main.py → app
```

### About `uvicorn main:app --reload`

You may also see:

```bash
uvicorn main:app --reload
```

This works **only if your current directory is ****`src/`**:

```bash
cd src
uvicorn main:app --reload
```

However, this is **not recommended for this project**, because the application also uses the `static/` directory located in the project root:

```text
NTI-NLP-Final-Project/
├── src/
│   └── main.py
│
└── static/
```

Running from the project root with:

```bash
uvicorn src.main:app --reload
```

keeps the project paths consistent.

---

## Test Questions

The following questions can be used to test KhedmaBot's retrieval, multilingual behavior, and escalation logic.

### Billing Questions

These questions should retrieve information from the **`billing_policies`** category.

```text
- What happens when I change my plan in the middle of a billing cycle?

- Will I be charged for both plans if I upgrade before my billing cycle ends?

- How are prorated charges calculated when changing plans?

- What happens to unused days of my old plan?

- Why is my first bill after upgrading higher than my normal monthly bill?

- If I downgrade my plan, will I receive a credit?

- Can changing my plan affect my promotional discount?

- Are there any additional fees when changing my plan?
```

---

### Technical Problems

These questions should retrieve information from the **`technical_solutions`** category.

```text
- My internet keeps disconnecting. What should I do?

- My Wi-Fi is very slow.

- The internet works on my phone but not on my laptop.

- I restarted my router but the connection is still not working.

- What should I check if my router has a connection problem?

- My internet connection keeps dropping every few minutes.

- What can I do if I cannot connect to the internet?
```

---

## Arabic Questions

These questions are particularly important for testing KhedmaBot's multilingual capabilities.

```text
ماذا يحدث إذا غيرت الباقة أثناء دورة الفاتورة؟

هل سيتم احتساب رسوم إضافية عند تغيير الباقة؟

النت عندي بيفصل كل شوية، أعمل إيه؟

الواي فاي بطيء جدًا، ممكن تساعدني؟

غيرت الباقة والفاتورة الجديدة أعلى من المعتاد، ليه؟

لو نزلت الباقة، هل هاخد رصيد أو خصم؟
```

### Expected behavior

KhedmaBot should:

1. Understand the Arabic query.
2. Retrieve the relevant knowledge-base information.
3. Generate the response in Arabic.

---

### Harder Customer Questions

These questions are closer to real customer conversations and are useful for testing KhedmaBot's reasoning and retrieval behavior.

```text
- I upgraded my plan yesterday and my bill is higher than expected. Can you explain why?

- My internet has been disconnecting since yesterday. I already restarted the router. What should I do next?

- I changed my plan and I'm seeing a charge I don't recognize.

- I've already tried restarting my router but the problem is still happening.
```

These questions test whether KhedmaBot can:

* Understand natural customer language
* Retrieve multiple relevant pieces of information
* Use conversation context
* Distinguish between solvable and unresolved issues
* Provide appropriate troubleshooting steps
* Identify cases requiring escalation

---

##  Knowledge Base

KhedmaBot uses a JSON-based telecom knowledge base stored under:

```text
data/
├── raw/
│   └── knowledge_base.json
│
└── processed/
    └── processed_knowledge_base.json
```

The knowledge base contains information used to answer customer questions about telecom services.

Documents include metadata such as:

```text
doc_id
title
content
category
language
sentiment
```

The processed documents are converted into LangChain `Document` objects before being split and embedded.

---

## Technologies

| Technology | Purpose                        |
| ---------- | ------------------------------ |
| Python     | Main programming language      |
| LangChain  | RAG orchestration              |
| Cohere     | Embeddings and LLM             |
| Chroma     | Vector database                |
| FastAPI    | Backend API                    |
| Uvicorn    | ASGI server                    |
| Streamlit  | Chat application and dashboard |
| Pandas     | Feedback analysis              |
| Plotly     | Data visualization             |
| SMTP       | Technician email escalation    |
| JSON       | Knowledge base storage         |

---

## Complete System Flow

```text
                    ┌─────────────────────┐
                    │      Customer       │
                    │       Query         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     KhedmaBot       │
                    │   Query Processing  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Chroma Retriever  │
                    │   Semantic Search   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Relevant Knowledge  │
                    │       Context       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Cohere LLM       │
                    │ Response Generation │
                    └──────────┬──────────┘
                               │
                         ┌─────┴─────┐
                         ▼           ▼
                    ┌─────────┐ ┌────────────┐
                    │ Answer  │ │ Escalation │
                    └────┬────┘ └──────┬─────┘
                         │              │
                         ▼              ▼
                    Customer       Technician
                    Response        Email Alert
                         │
                         ▼
                    Customer
                    Feedback
                         │
                         ▼
                  Analytics Dashboard
```

---

## NTI NLP Summer Training Final Project

**KhedmaBot** was developed as a Natural Language Processing project focused on applying **Retrieval-Augmented Generation (RAG)** to real-world telecom customer support.

The project demonstrates how NLP, semantic search, vector databases, LLMs, multilingual processing, and automated customer-service workflows can be combined into a complete AI-powered support system.

Huge thanks to my teammates who contributed in this project <3
