from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .quiz_batch import run_quiz_batch
from .generate_quiz_video import run_video_batch
from .config import DATA_DIR, VIDEOS_DIR


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
    - flatten quiz items + save results to quizzes_output.json (or similar)
    """
    result = run_quiz_batch()

    # run_quiz_batch가 {"success": False, "error": "..."} 이런 식으로 줄 경우 대비
    if not result.get("success", True):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Unknown error"),
        )

    return result


# -----------------------------
# Video Batch Generation
# (Quiz JSON 파일 → 여러 개 mp4 생성)
# -----------------------------
class VideoBatchRequest(BaseModel):
    quiz_file_name: str  # 예: "quiz_2024-12-04_batch1.json"


@app.post("/video-batch")
def create_video_batch(req: VideoBatchRequest):
    """
    1) DATA_DIR / quiz_file_name 에서 퀴즈 리스트를 읽고
    2) 각 퀴즈에 대해 make_video를 실행하여
    3) VIDEOS_DIR 아래에 mp4 여러 개 생성
    """
    try:
        result = run_video_batch(req.quiz_file_name)
        return result

    except FileNotFoundError:
        # 퀴즈 json 파일이 없을 때
        raise HTTPException(
            status_code=404,
            detail=f"Quiz file '{req.quiz_file_name}' not found",
        )

    except Exception as e:
        # 그 외 예외들
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# -----------------------------
# Quiz File List & Download
# -----------------------------
@app.get("/quizzes")
def list_quizzes():
    """DATA_DIR 내 퀴즈 JSON 파일 목록 반환"""
    data_path = Path(DATA_DIR)
    if not data_path.exists():
        return {"files": []}

    files = sorted(
        [f.name for f in data_path.iterdir() if f.is_file() and f.suffix == ".json"],
        reverse=True,
    )
    return {"files": files}


@app.get("/quizzes/{filename}/download")
def download_quiz(filename: str):
    """퀴즈 JSON 파일 다운로드"""
    # 입력 검증을 먼저 수행
    if ".." in filename or filename.startswith("/") or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Invalid file type")

    file_path = Path(DATA_DIR) / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Quiz file '{filename}' not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/json",
    )


# -----------------------------
# Video File List & Download
# -----------------------------
@app.get("/videos")
def list_videos():
    """VIDEOS_DIR 내 비디오 파일 목록 반환"""
    videos_path = Path(VIDEOS_DIR)
    if not videos_path.exists():
        return {"files": []}

    files = sorted(
        [f.name for f in videos_path.iterdir() if f.is_file() and f.suffix == ".mp4"],
        reverse=True,
    )
    return {"files": files}


@app.get("/videos/{filename}/download")
def download_video(filename: str):
    """비디오 MP4 파일 다운로드"""
    # 입력 검증을 먼저 수행
    if ".." in filename or filename.startswith("/") or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not filename.endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Invalid file type")

    file_path = Path(VIDEOS_DIR) / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Video file '{filename}' not found")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="video/mp4",
    )
