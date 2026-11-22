import logging
import os
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from interview_engine import (
    ask_ques,
    evaluate_answer_and_extract_keywords
)
from schemas import InterviewRequest, AnswerRequest


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("intervuex")

app = FastAPI(
    title="IntervueX API",
    description="AI-powered Interview Preparation and Evaluation Platform",
    version="1.0.0"
)

# For local frontend development, these are common development origins.
# Add your deployed frontend URL to INTERVUEX_FRONTEND_ORIGINS when hosting.
origins_from_env = os.getenv("INTERVUEX_FRONTEND_ORIGINS", "")
allowed_origins = [
    origin.strip()
    for origin in origins_from_env.split(",")
    if origin.strip()
]

if not allowed_origins:
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"]
)

# Temporary in-memory storage for development/testing.
# Replace with Redis or a database before production deployment.
sessions = {}


@app.get("/")
def root():
    return {
        "message": "Welcome to IntervueX API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health_check():
    return {
        "status": "running",
        "service": "IntervueX API"
    }


@app.post("/interviews/start")
def start_interview(data: InterviewRequest):
    user_details = data.model_dump()
    session_id = str(uuid4())

    ques_history = []
    answer_history = []
    keyword_history = []

    try:
        first_question = ask_ques(
            user_details,
            ques_history,
            answer_history,
            keyword_history
        )
    except Exception:
        logger.exception("Could not generate the first interview question.")
        raise HTTPException(
            status_code=503,
            detail=(
                "Question generation is currently unavailable. "
                "Check that Ollama is running and phi3:latest is installed."
            )
        )

    ques_history.append(first_question)

    sessions[session_id] = {
        "user_details": user_details,
        "ques_history": ques_history,
        "answer_history": answer_history,
        "keyword_history": keyword_history,
        "score": 0,
        "question_count": 1,
        "current_question": first_question,
        "completed": False
    }

    return {
        "session_id": session_id,
        "question": first_question,
        "question_number": 1,
        "total_questions": user_details["interview_length"]
    }


@app.post("/interviews/{session_id}/answer")
def submit_answer(session_id: str, data: AnswerRequest):
    session = sessions.get(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Interview session not found."
        )

    if session["completed"]:
        raise HTTPException(
            status_code=409,
            detail="This interview has already been completed."
        )

    current_question = session["current_question"]
    answer = data.answer

    try:
        evaluation, keywords = evaluate_answer_and_extract_keywords(
            current_question,
            answer
        )
    except Exception:
        logger.exception("Answer evaluation failed.")
        raise HTTPException(
            status_code=503,
            detail=(
                "Answer evaluation is currently unavailable. "
                "Check that Ollama is running and llama3.2:latest is installed."
            )
        )

    # Calculate the proposed score without changing session state yet.
    updated_score = session["score"]

    if evaluation == "Correct":
        updated_score += 4
    elif evaluation == "Incorrect":
        updated_score -= 1
    # Unattempted adds 0.

    total_questions = session["user_details"]["interview_length"]
    current_question_number = session["question_count"]

    # If this was the last question, finish the interview.
    if current_question_number >= total_questions:
        session["answer_history"].append(answer)
        session["keyword_history"].append(keywords)
        session["score"] = updated_score
        session["completed"] = True

        total_score = total_questions * 4
        percentage = (updated_score / total_score) * 100

        return {
            "evaluation": evaluation,
            "keywords": keywords,
            "interview_completed": True,
            "total_score": total_score,
            "score_attained": updated_score,
            "percentage": round(percentage, 2)
        }

    # Prepare updated history for the next question.
    # Commit it only after the next question is generated successfully.
    updated_answer_history = session["answer_history"] + [answer]
    updated_keyword_history = session["keyword_history"] + [keywords]

    try:
        next_question = ask_ques(
            session["user_details"],
            session["ques_history"],
            updated_answer_history,
            updated_keyword_history
        )
    except Exception:
        logger.exception("Could not generate the next interview question.")
        raise HTTPException(
            status_code=503,
            detail=(
                "The answer was received, but the next question could not "
                "be generated. Please retry the request."
            )
        )

    # Save the completed answer and the newly generated question.
    session["answer_history"].append(answer)
    session["keyword_history"].append(keywords)
    session["score"] = updated_score
    session["ques_history"].append(next_question)
    session["question_count"] += 1
    session["current_question"] = next_question

    return {
        "evaluation": evaluation,
        "keywords": keywords,
        "interview_completed": False,
        "next_question": next_question,
        "question_number": session["question_count"],
        "total_questions": total_questions,
        "current_score": session["score"]
    }


@app.get("/interviews/{session_id}/status")
def interview_status(session_id: str):
    session = sessions.get(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Interview session not found."
        )

    return {
        "session_id": session_id,
        "completed": session["completed"],
        "question_number": session["question_count"],
        "total_questions": session["user_details"]["interview_length"],
        "score": session["score"]
    }
