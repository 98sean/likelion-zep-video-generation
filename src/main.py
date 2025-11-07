from fetch_trends import get_top_google_trends
from generate_quizzes import create_quizzes

def main():
    print("Fetching top Google Trends...")
    trends = get_top_google_trends()
    
    for i, topic in enumerate(trends, start=1):
        print(f"\n=== Trend #{i}: {topic} ===")
        try:
            quizzes = create_quizzes(topic)
            print(quizzes)
        except Exception as e:
            print(f"Error generating quiz for {topic}: {e}")

if __name__ == "__main__":
    main()
