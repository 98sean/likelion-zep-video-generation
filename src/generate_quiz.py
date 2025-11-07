from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def create_quizzes(keyword: str) -> str:
    """
    Ask the OpenAI model to generate three YouTube quiz ideas for the keyword.
    """
    prompt = f"""
    You are a quiz content creator on YouTube.
    Please create three engaging quizzes about "{keyword}".
    Each quiz should have 3–5 questions and be suitable for a short YouTube video.
    """
    response = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )
    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    print(create_quizzes("Taylor Swift"))
