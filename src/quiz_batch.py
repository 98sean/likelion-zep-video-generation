import json
from pathlib import Path

from generate_quiz import create_quizzes
from fetch_trends_serpapi import fetch_trending_topics
from config import DATA_DIR


def load_quiz_json(raw_output):
    """Load quiz JSON safely."""
    if isinstance(raw_output, dict):
        return raw_output
    if isinstance(raw_output, str):
        return json.loads(raw_output)
    raise ValueError("Quiz output is neither dict nor JSON string.")


def flatten_questions(topic, quiz_obj):
    """Convert a structured quiz into a list of flat quiz entries."""
    flat_items = []
    questions = quiz_obj.get("questions", [])

    if not isinstance(questions, list):
        print(f"Warning: 'questions' for '{topic}' is not a list, skipping.")
        return []

    for q in questions:
        if not isinstance(q, dict):
            continue

        item = {
            "category": "Sports",
            "topic": str(topic),
            "question": q.get("question"),
            "options": q.get("options"),
            "answer": q.get("answer"),
        }

        if item["question"] and item["options"] and item["answer"]:
            flat_items.append(item)
        else:
            print(f"Warning: incomplete question object for '{topic}', skipping.")

    return flat_items


def run_quiz_batch() -> dict:
    print("Fetching top Google Trends...")

    try:
        trends = fetch_trending_topics(n = 15)
    except Exception as e:
        error_msg = f"Error fetching trends: {e}"
        print(error_msg)
        return {"success": False, "error": error_msg}

    all_quizzes = []

    for i, topic in enumerate(trends, start=1):
        print(f"\n=== Trend #{i}: {topic} ===")

        try:
            raw_quiz = create_quizzes(topic)
            print("Raw quiz output:", raw_quiz)

            # ------ FIX HERE ------
            quiz_obj = load_quiz_json(raw_quiz)
            # ----------------------

            # Flatten into individual quiz entries
            flat_items = flatten_questions(topic, quiz_obj)
            all_quizzes.extend(flat_items)

        except Exception as e:
            print(f"❌ Error generating quiz for '{topic}': {e}")

    # Save results
    data_dir = Path(DATA_DIR)
    data_dir.mkdir(exist_ok=True)

    # 기존 quizzes_output_*.json 파일 찾아서 다음 번호 결정
    existing_files = list(data_dir.glob("quizzes_output_*.json"))
    if existing_files:
        indices = []
        for f in existing_files:
            try:
                idx_str = f.stem.split("_")[-1]
                indices.append(int(idx_str))
            except (ValueError, IndexError):
                pass
        next_index = max(indices) + 1 if indices else 1
    else:
        next_index = 1

    output_path = data_dir / f"quizzes_output_{next_index}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(all_quizzes, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(all_quizzes)} quizzes to {output_path}")

    return {
        "success": True,
        "output_file": str(output_path),
        "quiz_count": len(all_quizzes),
        "topics": trends,
    }

def main():
    run_quiz_batch()

if __name__ == "__main__":
    main()
