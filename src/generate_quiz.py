from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def create_quizzes(keyword: str) -> str:
    prompt = f"""
    You are a professional quiz content creator on YouTube.
    Create ONE multiple-choice question about "{keyword}".

    Output strictly one JSON object with the following keys:
    - category: a short label representing the quiz topic (e.g., "Music", "Movies", "Sports")
    - question: a clear and engaging question related to "{keyword}"
    - options: a list of exactly 4 answer choices
    - answer: the correct answer, exactly matching one of the options

    Rules:
    - Output ONLY the JSON object — no explanations, markdown, or extra text.
    - Ensure "answer" matches exactly one of the "options".
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )

    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    print(create_quizzes("Taylor Swift"))
