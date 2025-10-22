import os
import time
import datetime
from generate_quiz_video import make_video as gen_quiz_video, quiz_json_str

# 🔧 설정
DEST_DIR = "videos_out"           # 출력(생성된 영상) 저장 폴더
INTERVAL_SECONDS = 3             # 주기 (3초마다 실행)

def make_video():
    """
    진짜 영상 생성 함수로 교체 버전
    generate_quiz_video.make_video() 는 파일을 생성하고
    파일명을 OUTPUT에 저장한다고 가정한다.
    """
    path = gen_quiz_video(quiz_json_str)  # ← 기존 quiz 생성 함수 호출
    with open(path, "rb") as f:
        data = f.read()
    base = os.path.basename(path)
    return data, base

def save_output(video_bytes, base_name):
    """
    날짜별 폴더(YYYY-MM-DD)에 저장.
    파일 이름에 시분초 붙여서 중복 방지.
    """
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join(DEST_DIR, date_str)
    os.makedirs(out_dir, exist_ok=True)

    ts = datetime.datetime.now().strftime("%H%M%S")
    root, _ = os.path.splitext(base_name)
    out_path = os.path.join(out_dir, f"{root}_{ts}.mp4")

    with open(out_path, "wb") as f:
        f.write(video_bytes)

    print(f"✅ 저장 완료: {out_path}\n")
    return out_path

def tick():
    data, name = make_video()
    save_output(data, name)

def main():
    print(f"⏱ 주기적 실행 시작 (매 {INTERVAL_SECONDS}CH) — 종료: Ctrl + C")
    tick()  # 최초 1회 실행

    try:
        while True:
            time.sleep(INTERVAL_SECONDS)
            tick()
    except KeyboardInterrupt:
        print("\n👋 종료합니다.")

if __name__ == "__main__":
    main()
