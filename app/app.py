import streamlit as st
import json
import re
from langchain_core.messages import HumanMessage, AIMessage
from src.rag import (
    ask_question,
    get_sources,
    get_technician_by_category,
    send_escalation_email,
)

def is_arabic(text):
    if re.search("[\u0600-\u06FF]", text):
        return True
    return False

def save_feedback(question, answer, rating):
    sentiment = "Positive" if rating == 1 else "Negative"
    log_entry = {
        "question": question,
        "answer": answer,
        "sentiment": sentiment
    }
    with open("feedback_logs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


st.set_page_config(
    page_title="Telecom Support AI",
    page_icon="📡",
    layout="centered"
)

st.title("Telecom Support AI")
st.caption(
    "AI-powered customer support assistant using RAG"
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_escalation" not in st.session_state:
    st.session_state.pending_escalation = None


with st.sidebar:
    st.header("Options")
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.session_state.pending_escalation = None
        st.rerun()
    st.divider()
    st.markdown("### About")

    st.write(
        """
        This assistant uses Retrieval-Augmented Generation
        to answer customer questions using the provided
        telecom knowledge base.
        """
    )

for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            if "sources" in message:
                with st.expander("📚 Retrieved Sources"):
                    for j, doc in enumerate(message["sources"]):
                        st.markdown(f"**{j + 1}. {doc.metadata.get('title', 'Unknown')}**")
                        st.caption(f"Category: {doc.metadata.get('category', 'Unknown')}")
                        st.write(doc.page_content)
                        st.divider()
            feedback_key = f"feedback_{i}"
            feedback_result = st.feedback("thumbs", key=feedback_key)
            if feedback_result is not None and message.get("feedback_value") != feedback_result:
                st.session_state.messages[i]["feedback_value"] = feedback_result
                user_question = st.session_state.messages[i-1]["content"]
                save_feedback(user_question, message["content"], feedback_result)
                if is_arabic(user_question):
                    toast_message = "شكراً على تقييمك! رأيك يفيدنا في تحسين النظام."
                else:
                    toast_message = "Thank you for your feedback! It helps us improve."
                st.toast(toast_message, icon="✅")


if st.session_state.pending_escalation:
    esc = st.session_state.pending_escalation
    with st.chat_message("assistant"):
        st.markdown(
            "I need an email or phone number before I can forward this "
            "to a technician, so they have a way to reach you."
        )
        with st.form(key="escalation_contact_form", clear_on_submit=False):
            contact = st.text_input("Email or phone number", key="escalation_contact_input")
            submitted = st.form_submit_button("Send")

        if submitted:
            contact_value = contact.strip() if contact else ""
            if not contact_value:
                st.warning("Please enter an email or phone number to continue — this is required to escalate.")
            else:
                technician = get_technician_by_category(esc["category"])
                sent, error = send_escalation_email(
                    technician, esc["question"], esc["category"], esc["history"],
                    contact=contact_value,
                )
                if sent:
                    confirmation = (
                        f"Thanks! I've forwarded your issue to {technician['name']} "
                        f"along with your contact info."
                    )
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": confirmation,
                        "escalated": True,
                        "technician_name": technician["name"],
                    })
                else:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": (
                            f"I couldn't reach a technician automatically "
                            f"({error}). Please contact support directly."
                        ),
                        "escalated": False,
                    })
                st.session_state.pending_escalation = None
                st.rerun()

question = None
if not st.session_state.pending_escalation:
    question = st.chat_input(
        "Describe your problem..."
    )

if question:
    lc_history = []
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            lc_history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_history.append(AIMessage(content=msg["content"]))

    st.session_state.messages.append({
        "role": "user",
        "content": question
    })
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = ask_question(question, lc_history)
            sources = get_sources(question)

        answer = result["answer"]
        status = result["status"]
        category = result["category"]

        st.markdown(answer)
        with st.expander("📚 Retrieved Sources"):
            for i, doc in enumerate(sources):
                st.markdown(
                    f"**{i + 1}. {doc.metadata.get('title', 'Unknown')}**"
                )
                st.caption(
                    f"Category: {doc.metadata.get('category', 'Unknown')}  \n"
                    f"Language: {doc.metadata.get('language', 'Unknown')}"
                )
                st.write(doc.page_content)
                st.divider()
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "feedback_value": None
    })

    if status == "no_solution":
        st.session_state.pending_escalation = {
            "question": question,
            "category": category,
            "history": lc_history + [HumanMessage(content=question)],
        }


    st.rerun()