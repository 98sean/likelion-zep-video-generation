import json

from fetch_trends import get_top_google_trends
from generate_quiz import create_quizzes
from fetch_trends_serpapi import fetch_trending_topics


def main():
    print("Fetching top Google Trends...")
    # trends = get_top_google_trends()
    trends = fetch_trending_topics()

    # This list will store each quiz question as a flat object
    all_quizzes = []

    for i, topic in enumerate(trends, start=1):
        print(f"\n=== Trend #{i}: {topic} ===")
        try:
            quizzes = create_quizzes(topic)  # Expected: dict or JSON string
            print(quizzes)

            # If the output is a JSON string → parse it into a dict
            if isinstance(quizzes, str):
                try:
                    quiz_obj = json.loads(quizzes)
                except json.JSONDecodeError:
                    print(f"Warning: quizzes for '{topic}' is not valid JSON, skipping.")
                    continue
            else:
                # If it's already a dict → use it as-is
                quiz_obj = quizzes

            # Must be a dict like: {"category": "...", "questions": [ {...}, {...} ]}
            if not isinstance(quiz_obj, dict):
                print(f"Warning: quizzes for '{topic}' is not a dict, skipping.")
                continue

            questions = quiz_obj.get("questions", [])
            if not isinstance(questions, list):
                print(f"Warning: 'questions' for '{topic}' is not a list, skipping.")
                continue

            # Convert each question into a flat object
            for q in questions:
                if not isinstance(q, dict):
                    continue

                flat_item = {
                    "category": "Sports",  # category is fixed
                    "topic": str(topic),  # original trending topic
                    "question": q.get("question"),
                    "options": q.get("options"),
                    "answer": q.get("answer"),
                }

                # Add only fully valid quiz items
                if flat_item["question"] and flat_item["options"] and flat_item["answer"]:
                    all_quizzes.append(flat_item)
                else:
                    print(f"Warning: incomplete question object for '{topic}', skipping.")

        except Exception as e:
            print(f"Error generating quiz for {topic}: {e}")

    # Save all flat quiz items into a single JSON file
    output_filename = "quizzes_output.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(all_quizzes, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(all_quizzes)} flat quiz items to {output_filename}")


if __name__ == "__main__":
    main()