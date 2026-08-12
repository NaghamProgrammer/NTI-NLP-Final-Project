import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage


from src.rag import (
    ask_question,
    get_sources,
    get_technician_by_category,
    send_escalation_email,
)

app = FastAPI(title="Telecom Support AI API")


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str
    history: List[ChatMessage]

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
@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    lc_history = []
    for msg in req.history:
        if msg.role == "user":
            lc_history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_history.append(AIMessage(content=msg.content))
    result = ask_question(req.question, lc_history)
    formatted_sources = []
    if result["status"] == "answered":
        sources = get_sources(req.question)
        for doc in sources:
            formatted_sources.append({
                "title": doc.metadata.get('title', 'Unknown'),
                "category": doc.metadata.get('category', 'Unknown'),
                "content": doc.page_content
            })

    return {
        "status": result["status"],
        "answer": result["answer"],
        "category": result["category"],
        "sources": formatted_sources
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
    if not os.path.exists("feedback_logs.jsonl"):
        return {"total": 0, "positive": 0, "negative": 0, "rate": 0.0, "negative_logs": []}

    df_records = []
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
    total = len(records)
    pos = sum(1 for r in records if r.get("sentiment") == "Positive")
    neg = total - pos
    rate = (pos / total * 100) if total > 0 else 0.0

    neg_logs = [{"question": r.get("question"), "answer": r.get("answer")} for r in records if r.get("sentiment") == "Negative"]

    return {
        "total": total,
        "positive": pos,
        "negative": neg,
        "rate": round(rate, 1),
        "negative_logs": neg_logs
    }

@app.delete("/api/analytics/clear")
async def clear_analytics():
    import os
    if os.path.exists("feedback_logs.jsonl"):
        os.remove("feedback_logs.jsonl")
    return {"success": True}
@app.post("/api/feedback/delete")
async def delete_specific_feedback(req: DeleteSpecificFeedbackRequest):
    import os, json
    if not os.path.exists("feedback_logs.jsonl"):
        return {"success": True}

    remaining_logs = []
    questions_to_delete = set(req.questions)
    with open("feedback_logs.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    log = json.loads(line)
                    if log.get("question") not in questions_to_delete:
                        remaining_logs.append(line)
                except:
                    remaining_logs.append(line)
    with open("feedback_logs.jsonl", "w", encoding="utf-8") as f:
        f.writelines(remaining_logs)
    return {"success": True}
app.mount("/", StaticFiles(directory="static", html=True), name="static")

