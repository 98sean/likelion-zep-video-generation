import os
import json
import time
import datetime

from fetch_trends_serpapi import fetch_trending_topics
from generate_quiz import create_quizzes
from generate_quiz_video import make_video

# -----------------------------
# 설정
# -----------------------------
NUM_TOPICS = 3              # 한 번에 가져올 트렌드 수
QUESTIONS_PER_TOPIC = 2     # 토픽 당 문제 수 → 총 6문제
LOOP_INTERVAL = 420         # 7분(초 단위) 간격으로 배치 시작
MAX_QUIZZES_PER_FILE = 60   # 한 JSON 파일당 최대 문제 수


def generate_quiz_batch():
    """
    1) 트렌드 3개 가져오기
    2) 각 토픽별 2문제씩 생성하여 flat quiz 리스트 반환
    3) quizzes_output_*.json 파일들에 누적 저장
       - 한 파일당 최대 MAX_QUIZZES_PER_FILE 문제
    """
    print("\n==============================")
    print("📈 Fetching trending topics...")
    topics = fetch_trending_topics(n=NUM_TOPICS, geo="US", category_id=17)
    print(f"✅ Got topics: {topics}")

    new_quizzes = []

    for i, topic in enumerate(topics, start=1):
        print(f"\n=== Topic #{i}: {topic} ===")
        try:
            raw = create_quizzes(topic)
            quiz_obj = json.loads(raw)

            questions = quiz_obj.get("questions", [])
            if not isinstance(questions, list):
                print(f"⚠️ 'questions' is not a list for topic '{topic}', skipping.")
                continue

            for q in questions:
                if not isinstance(q, dict):
                    continue

                flat_item = {
                    "category": "Sports",
                    "topic": str(topic),
                    "question": q.get("question"),
                    "options": q.get("options"),
                    "answer": q.get("answer"),
                }

                if flat_item["question"] and flat_item["options"] and flat_item["answer"]:
                    new_quizzes.append(flat_item)
                else:
                    print(f"⚠️ Incomplete question for topic '{topic}', skipping.")

        except Exception as e:
            print(f"❌ Error generating quiz for topic '{topic}': {e}")

    # 6문제로 제한 (안전장치)
    max_quizzes = NUM_TOPICS * QUESTIONS_PER_TOPIC
    if len(new_quizzes) > max_quizzes:
        new_quizzes = new_quizzes[:max_quizzes]

    if not new_quizzes:
        print("⚠️ No quizzes generated in this batch.")
        return [], None

    # ----------------------------------------------------
    # quizzes_output_*.json 파일들 관리
    #   - 한 파일당 MAX_QUIZZES_PER_FILE 문제
    #   - 넘치면 다음 번호 파일 생성
    # ----------------------------------------------------
    # 1) 기존 quizzes_output_*.json 목록 찾기
    existing_files = [
        f for f in os.listdir(".")
        if f.startswith("quizzes_output_") and f.endswith(".json")
    ]

    def extract_index(name: str) -> int:
        # quizzes_output_숫자.json 에서 숫자만 뽑기
        try:
            base = os.path.splitext(name)[0]          # quizzes_output_3
            idx_str = base.split("_")[-1]             # "3"
            return int(idx_str)
        except Exception:
            return 0

    if existing_files:
        existing_files.sort(key=extract_index)
        last_file = existing_files[-1]
        current_index = extract_index(last_file)
        current_filename = last_file

        # 마지막 파일 내용 읽기
        try:
            with open(current_filename, "r", encoding="utf-8") as f:
                current_data = json.load(f)
            if not isinstance(current_data, list):
                print(f"⚠️ {current_filename} is not a list. Overwriting it.")
                current_data = []
        except Exception:
            print(f"⚠️ Failed to read {current_filename}. Overwriting it.")
            current_data = []
    else:
        # 아직 아무 파일도 없으면 1번부터 시작
        current_index = 1
        current_filename = f"quizzes_output_{current_index}.json"
        current_data = []

    touched_files = set()

    # 2) 현재 파일에 먼저 채우고, 넘치면 다음 파일로 넘기기
    remaining_new = list(new_quizzes)  # 복사본

    while remaining_new:
        remaining_capacity = MAX_QUIZZES_PER_FILE - len(current_data)

        if remaining_capacity <= 0:
            # 현재 파일 꽉 찼으면 저장하고 다음 파일로
            with open(current_filename, "w", encoding="utf-8") as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
            touched_files.add(current_filename)

            current_index += 1
            current_filename = f"quizzes_output_{current_index}.json"
            current_data = []
            remaining_capacity = MAX_QUIZZES_PER_FILE

        # 이번 파일에 들어갈 만큼 잘라서 넣기
        to_take = remaining_new[:remaining_capacity]
        current_data.extend(to_take)
        remaining_new = remaining_new[remaining_capacity:]

    # 마지막으로 사용한 파일 저장
    with open(current_filename, "w", encoding="utf-8") as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)
    touched_files.add(current_filename)

    total_in_last_file = len(current_data)
    print(
        f"\n✅ This batch generated {len(new_quizzes)} quizzes."
        f" Last file: {current_filename} (now {total_in_last_file} quizzes)."
    )

    # 마지막에 손 댄 파일 하나의 이름만 리턴 (원래 output_filename 역할)
    return new_quizzes, current_filename


def generate_videos_from_quizzes(quizzes, output_dir="videos"):
    """
    주어진 퀴즈 리스트(each: {category, topic, question, options, answer})로
    각각에 대해 하나씩 영상 생성.
    """
    os.makedirs(output_dir, exist_ok=True)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    created_files = []

    for idx, quiz in enumerate(quizzes, start=1):
        safe_topic = quiz.get("topic", "topic").replace(" ", "_")[:20]
        filename = f"quiz_{ts}_{idx}_{safe_topic}.mp4"
        output_path = os.path.join(output_dir, filename)

        print(f"\n🎬 Generating video {idx}/{len(quizzes)} → {output_path}")
        try:
            make_video(quiz, output_path=output_path)
            created_files.append(output_path)
        except Exception as e:
            print(f"❌ Failed to create video for quiz #{idx}: {e}")

    print(f"\n✨ Video generation done. Created {len(created_files)} files.")
    return created_files


def main_loop():
    """
    배치 시작 기준으로 5분 간격 유지:
      - 배치 한 번 수행 (퀴즈 생성 + 영상 생성)
      - 배치에 걸린 시간을 측정
      - (5분 - 걸린 시간) 만큼만 sleep
    """
    batch_num = 1
    while True:
        start_time = time.time()
        print("\n=======================================")
        print(f"🚀 Starting batch #{batch_num} at {datetime.datetime.now()}")

        try:
            quizzes, json_path = generate_quiz_batch()
            if quizzes:
                generate_videos_from_quizzes(quizzes, output_dir="videos")
            else:
                print("⚠️ No quizzes generated in this batch.")
        except Exception as e:
            print(f"❌ Unexpected error in batch #{batch_num}: {e}")

        elapsed = time.time() - start_time
        wait = max(0, LOOP_INTERVAL - elapsed)
        print(f"\n⏱ Batch #{batch_num} took {elapsed:.1f} seconds.")
        print(f"⏳ Waiting {wait:.1f} seconds before next batch...")
        batch_num += 1

        time.sleep(wait)


if __name__ == "__main__":
    main_loop()
