import os, time, json, random, datetime
from pathlib import Path

# 너의 비디오 생성 코드 import
import generate_quiz_video as gqv

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# =========================
# YouTube API 설정
# =========================
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_youtube_client():
    flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
    creds = flow.run_local_server(port=0)  # 첫 실행 때만 브라우저 뜸
    return build("youtube", "v3", credentials=creds)

def upload_video(youtube, file_path, title, description,
                 tags=None, category_id="27", privacy="public",
                 publish_at_iso=None):
    """
    videos.insert 로 업로드.
    - 업로드 1회 quota cost = 1600 units :contentReference[oaicite:3]{index=3}
    - publishAt 쓰려면 privacyStatus="private" 여야 함 :contentReference[oaicite:4]{index=4}
    """
    if tags is None:
        tags = ["quiz", "shorts", "zepquiz"]

    status = {"privacyStatus": privacy}
    if publish_at_iso:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at_iso

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id
        },
        "status": status
    }

    media = MediaFileUpload(file_path, mimetype="video/*", resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        progress, response = request.next_chunk()
        if progress:
            print(f"Upload progress: {int(progress.progress() * 100)}%")

    print("✅ Uploaded. videoId =", response["id"])
    return response["id"]


# =========================
# 퀴즈 로딩/생성 부분
# =========================
def load_quizzes(path):
    """
    파이프라인에서 생성한 JSON (list of quiz objects) 읽기.
    generate_quiz_video.py 의 스키마와 동일해야 함:
    {category, question, options, answer}
    """
    with open(path, "r", encoding="utf-8") as f:
        quizzes = json.load(f)
    return quizzes

# TODO: 이 부분만 퀴즈 자동 생성 함수 호출로 바꾸면 됨.
def get_quizzes_for_today():
    return load_quizzes("dummy_quizzes.json")


# =========================
# 업로드 스케줄러
# =========================
OUTPUT_DIR = Path("rendered_shorts")
OUTPUT_DIR.mkdir(exist_ok=True)

def render_one_quiz_to_mp4(quiz, idx):
    # generate_quiz_video.py는 OUTPUT 전역 변수로 파일명 결정함 :contentReference[oaicite:5]{index=5}
    out_path = OUTPUT_DIR / f"quiz_{idx:03d}.mp4"
    gqv.OUTPUT = str(out_path)
    return gqv.make_video(quiz)  # mp4 경로 리턴 :contentReference[oaicite:6]{index=6}

def human_safe_sleep(min_minutes=60, max_minutes=240):
    """
    너무 촘촘하면 봇/스팸처럼 보일 수 있으니
    랜덤 간격으로 텀 주기 (예: 1~4시간).
    """
    mins = random.uniform(min_minutes, max_minutes)
    print(f"⏳ Sleeping {mins:.1f} minutes...")
    time.sleep(mins * 60)

def run_upload_cycle(max_uploads_per_day=5):
    """
    하루 업로드 개수 제한:
    기본 quota 10,000/day 기준 uploads.insert(1600) ≈ 6개/일이 상한 :contentReference[oaicite:7]{index=7}
    안전하게 3~5개 추천.
    """
    youtube = get_youtube_client()
    quizzes = get_quizzes_for_today()

    quizzes = quizzes[:max_uploads_per_day]

    for i, quiz in enumerate(quizzes, start=1):
        print(f"\n🎬 Render quiz {i}/{len(quizzes)}")
        mp4_path = render_one_quiz_to_mp4(quiz, i)

        # Shorts로 잘 분류되게: 9:16 세로 + 60초 이하 + #shorts 추천 :contentReference[oaicite:8]{index=8}
        title = f"{quiz.get('category','General')} Quiz #{i} #shorts"
        description = (
            f"Q. {quiz['question']}\n"
            f"Answer reveals in 5 seconds!\n"
            "#shorts #quiz"
        )

        print("🚀 Uploading:", mp4_path)
        upload_video(
            youtube,
            file_path=mp4_path,
            title=title,
            description=description,
            tags=["quiz", "shorts", quiz.get("category","general")]
        )

        if i != len(quizzes):
            human_safe_sleep(60, 240)  # 다음 업로드까지 1~4시간 랜덤


if __name__ == "__main__":
    run_upload_cycle(max_uploads_per_day=5)
