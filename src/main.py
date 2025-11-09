from fetch_trends import get_top_google_trends
from generate_quiz import create_quizzes
from fetch_trends_serpapi import fetch_trending_topics

def main():
    print("Fetching top Google Trends...")
    # trends = get_top_google_trends()
    trends = fetch_trending_topics()
    
    for i, topic in enumerate(trends, start=1):
        print(f"\n=== Trend #{i}: {topic} ===")
        try:
            quizzes = create_quizzes(topic)
            print(quizzes)
        except Exception as e:
            print(f"Error generating quiz for {topic}: {e}")

if __name__ == "__main__":
    main()
