from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# SerpApi API Key
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")