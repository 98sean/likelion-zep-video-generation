from pytrends.request import TrendReq

def get_top_google_trends(n=10, geo="US"):
    """
    Fetch top trending search queries from Google Trends.
    """
    pytrends = TrendReq(hl='en-US', tz=360)
    trending_searches_df = pytrends.trending_searches(pn='united_states')
    top_trends = trending_searches_df[0].tolist()[:n]
    return top_trends

if __name__ == "__main__":
    print(get_top_google_trends())
