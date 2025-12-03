import json
from generate_quiz import create_quizzes
from fetch_trends_serpapi import fetch_trending_topics


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


def main():
    print("Fetching top Google Trends...")

    try:
        trends = fetch_trending_topics()
    except Exception as e:
        print(f"Error fetching trends: {e}")
        return

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
    output_filename = "quizzes_output.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(all_quizzes, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(all_quizzes)} quizzes to {output_filename}")


if __name__ == "__main__":
    main()
