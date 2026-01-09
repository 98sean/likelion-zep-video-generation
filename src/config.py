from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# SerpApi API Key
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# External Quiz API
QUIZ_API_URL = os.getenv("QUIZ_API_URL", "https://dev-3-quiz-api.zep.us/api/quizsets/create")
QUIZ_API_KEY = os.getenv("QUIZ_API_KEY", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkeWRja3NkaWRAZ21haWwuY29tIiwiYXV0aCI6IlJPTEVfTk9STUFMIiwiaWF0IjoxNzY3OTI3NTY1LCJleHAiOjE3Njc5NDkxNjV9.Yu6wAlQ81nZlMXPyLUCe0jM5_Zv84wqtAvwGtfuyYb4")  # Bearer token or API key if needed

# Directory paths
DATA_DIR = "data"           # 퀴즈 JSON 저장 디렉토리
VIDEOS_DIR = "videos"       # 비디오 저장 디렉토리