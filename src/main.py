import json
import os
import time
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel


from src.rag import (
    ask_question,
    get_sources,
    get_technician_by_category,
    send_escalation_email,
    classify_resolution_intent,
)

app = FastAPI(title="Telecom Support AI API")
HANDLING_LOG_FILE = "handling_logs.jsonl"
conversation_state: Dict[str, Dict[str, Any]] = {}

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str
    history: List[ChatMessage]
    conversation_id: str

class EscalationRequest(BaseModel):
    contact: str
    question: str
    category: str
    history: List[ChatMessage]

class FeedbackRequest(BaseModel):
    question: str
    answer: str
    rating: int

class DeleteSpecificFeedbackRequest(BaseModel):
    questions: List[str]
    conversation_id: Optional[str] = None
def _close_conversation(conversation_id: str, state: Dict[str, Any], now: float, outcome: str):

    handling_time_seconds = round(now - state["first_message_time"], 1)
    log_entry = {
        "conversation_id": conversation_id,
        "outcome": outcome,
        "handling_time_seconds": handling_time_seconds,
        "closed_at": now,
    }
    with open(HANDLING_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    state["closed"] = True
    return handling_time_seconds


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    now = time.time()
    state = conversation_state.setdefault(
        req.conversation_id, {"first_message_time": now, "closed": False}
    )
    lc_history = []
    for msg in req.history:
        if msg.role == "user":
            lc_history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_history.append(AIMessage(content=msg.content))

    if lc_history and not state.get("closed"):
        intent = classify_resolution_intent(req.question)
        if intent == "resolved":
            _close_conversation(req.conversation_id, state, now, outcome="success")
            return {
                "status": "resolved",
                "answer": "Glad to hear that fixed it! Let me know if anything else comes up.",
                "category": None,
                "sources": [],
                "evaluation_score": None,
            }
        if intent == "unresolved":
            _close_conversation(req.conversation_id, state, now, outcome="fail")
            return {
                "status": "unresolved",
                "answer": "I'm sorry that didn't solve it. Tell me more about what's still happening and I'll keep helping, or I can forward this to a technician.",
                "category": None,
                "sources": [],
                "evaluation_score": None,
            }
    result = ask_question(req.question, lc_history)
    formatted_sources = []
    context_texts = []
    if result["status"] == "answered":
        sources = get_sources(req.question)
        for doc in sources:
            context_texts.append(doc.page_content)
            formatted_sources.append({
                "title": doc.metadata.get('title', 'Unknown'),
                "category": doc.metadata.get('category', 'Unknown'),
                "content": doc.page_content
            })
    eval_score = evaluate_groundedness(req.question, result["answer"], context_texts)
    log_entry = {
        "question": req.question,
        "answer": result["answer"],
        "status": result["status"],
        "accuracy_score": int(eval_score * 100)
    }

    with open("live_evaluations.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    return {
        "status": result["status"],
        "answer": result["answer"],
        "category": result["category"],
        "sources": formatted_sources,
        "evaluation_score": int(eval_score * 100)
    }

@app.post("/api/escalate")
async def escalate_endpoint(req: EscalationRequest):
    lc_history = []
    for msg in req.history:
        if msg.role == "user":
            lc_history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_history.append(AIMessage(content=msg.content))

    technician = get_technician_by_category(req.category)
    sent, error = send_escalation_email(
        technician, req.question, req.category, lc_history, contact=req.contact
    )

    if sent:
        return {"success": True, "message": f"Forwarded to {technician['name']}"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to send: {error}")

@app.post("/api/feedback")
async def feedback_endpoint(req: FeedbackRequest):
    sentiment = "Positive" if req.rating == 1 else "Negative"
    log_entry = {
        "question": req.question,
        "answer": req.answer,
        "sentiment": sentiment
    }
    with open("feedback_logs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    return {"success": True}

@app.get("/api/analytics")
async def get_analytics():
    import os, json
    df_records = []
    if os.path.exists("feedback_logs.jsonl"):
        with open("feedback_logs.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        df_records.append(json.loads(line))
                    except:
                        pass

    deduped = {}
    for r in df_records:
        key = f"{r.get('question')}|{r.get('answer')}"
        deduped[key] = r

    records = list(deduped.values())
    total_feedback = len(records)
    pos = sum(1 for r in records if r.get("sentiment") == "Positive")
    neg = total_feedback - pos
    rate = (pos / total_feedback * 100) if total_feedback > 0 else 0.0
    neg_logs = [{"question": r.get("question"), "answer": r.get("answer")} for r in records if r.get("sentiment") == "Negative"]

    eval_scores = []
    if os.path.exists("live_evaluations.jsonl"):
        with open("live_evaluations.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if "accuracy_score" in data:
                            eval_scores.append(data["accuracy_score"])
                    except:
                        pass

    total_chats = len(eval_scores)
    avg_groundedness = round(sum(eval_scores) / total_chats, 1) if total_chats > 0 else 0.0
    high_alignment = sum(1 for s in eval_scores if s >= 75)
    low_alignment = total_chats - high_alignment

    handling_records = []
    if os.path.exists(HANDLING_LOG_FILE):
        with open(HANDLING_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        handling_records.append(json.loads(line))
                    except:
                        pass
    successful_issues = sum(1 for r in handling_records if r.get("outcome") == "success")
    failed_issues = sum(1 for r in handling_records if r.get("outcome") == "fail")
    handling_times = [r.get("handling_time_seconds", 0) for r in handling_records]
    avg_handling_time_minutes = (
        round(sum(handling_times) / len(handling_times) / 60, 1) if handling_times else 0.0
    )

    return {
        "total": total_feedback,
        "positive": pos,
        "negative": neg,
        "rate": round(rate, 1),
        "negative_logs": neg_logs,
        "total_chats": total_chats,
        "avg_groundedness": avg_groundedness,
        "high_alignment": high_alignment,
        "low_alignment": low_alignment,
        "successful_issues": successful_issues,
        "failed_issues": failed_issues,
        "avg_handling_time_minutes": avg_handling_time_minutes
    }

@app.delete("/api/analytics/clear")
async def clear_analytics():
    import os
    if os.path.exists("feedback_logs.jsonl"):
        os.remove("feedback_logs.jsonl")
    if os.path.exists("live_evaluations.jsonl"):
        os.remove("live_evaluations.jsonl")
    if os.path.exists(HANDLING_LOG_FILE):
        os.remove(HANDLING_LOG_FILE)
    conversation_state.clear()
    return {"success": True}

@app.post("/api/feedback/delete")
async def delete_specific_feedback(req: DeleteSpecificFeedbackRequest):
    import os, json
    questions_to_delete = set(req.questions)
    if os.path.exists("feedback_logs.jsonl"):
        remaining_feedback = []
        with open("feedback_logs.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        log = json.loads(line)
                        if log.get("question") not in questions_to_delete:
                            remaining_feedback.append(line)
                    except:
                        remaining_feedback.append(line)
        with open("feedback_logs.jsonl", "w", encoding="utf-8") as f:
            f.writelines(remaining_feedback)
    if os.path.exists("live_evaluations.jsonl"):
        remaining_evals = []
        with open("live_evaluations.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        log = json.loads(line)
                        if log.get("question") not in questions_to_delete:
                            remaining_evals.append(line)
                    except:
                        remaining_evals.append(line)
        with open("live_evaluations.jsonl", "w", encoding="utf-8") as f:
            f.writelines(remaining_evals)

    if req.conversation_id and os.path.exists(HANDLING_LOG_FILE):
        remaining_handling = []
        with open(HANDLING_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        log = json.loads(line)
                        if log.get("conversation_id") != req.conversation_id:
                            remaining_handling.append(line)
                    except:
                        remaining_handling.append(line)
        with open(HANDLING_LOG_FILE, "w", encoding="utf-8") as f:
            f.writelines(remaining_handling)
    return {"success": True}

app.mount("/", StaticFiles(directory="static", html=True), name="static")

def evaluate_groundedness(question: str, answer: str, contexts: List[str]) -> float:
    """
    Compares the AI generated answer directly against the retrieved Knowledge Base contexts.
    Returns a score from 0.0 to 1.0 (0% to 100% grounded).
    """
    if not contexts or not answer:
        return 1.0 if not contexts and "hello" in question.lower() else 0.0
    combined_context = " ".join(contexts).lower()
    answer_words = [w.lower() for w in answer.split() if len(w) > 3]
    if not answer_words:
        return 1.0
    matches = sum(1 for word in answer_words if word in combined_context)
    score = round(matches / len(answer_words), 2)
    return min(max(score * 1.2, 0.25 if score > 0 else 0.0), 1.0)