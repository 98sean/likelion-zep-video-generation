from fastapi import FastAPI, HTTPException
from .quiz_batch import run_quiz_batch

app = FastAPI()


# -----------------------------
# Health Check
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# -----------------------------
# Batch Quiz Generation (Google Trends)
# -----------------------------
@app.post("/quiz-batch")
def run_batch_from_trends():
    """
    Run one full quiz batch cycle from quiz_batch.py:
    - fetch trending topics
    - create quizzes for each topic
    - flatten quiz items + save results to quizzes_output.json
    """
    result = run_quiz_batch()

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Unknown error")
        )

    return result