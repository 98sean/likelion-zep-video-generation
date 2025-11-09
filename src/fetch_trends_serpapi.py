from serpapi import GoogleSearch
from config import SERPAPI_API_KEY


def fetch_trending_topics(n: int = 3, geo: str = "US", category_id: int = 17):
    """
    Fetch trending topics from Google Trends 'Trending Now' section
    for a specific category and region.

    Args:
        n (int): Number of topics to return (default: 3)
        geo (str): Region code, e.g. "US" or "KR"
        category_id (int): Google Trends category ID
            (e.g., 17 for Sports, 16 for Entertainment)

    Returns:
        list[str]: A list of trending topic strings
    """
    params = {
        "api_key": SERPAPI_API_KEY,
        "engine": "google_trends_trending_now",
        "geo": geo,          # Region code
        "hl": "en",          # Language setting
        "hours": 24,         # Time window in hours (4, 24, 48, 168)
        "category_id": category_id,
        "only_active": True, # Include only currently active trends
    }

    search = GoogleSearch(params)
    result = search.get_dict()

    # Extract topics (queries) from the result
    trending = result.get("trending_searches", [])
    topics = []

    for item in trending:
        query = item.get("query")
        if query:
            topics.append(query)
        if len(topics) >= n:
            break

    return topics


# Example test run
if __name__ == "__main__":
    print("Sports:", fetch_trending_topics(n=3, geo="US", category_id=17))
    print("Entertainment:", fetch_trending_topics(n=3, geo="US", category_id=16))
