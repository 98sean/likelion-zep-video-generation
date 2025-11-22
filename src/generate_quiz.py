from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def create_quizzes(topic: str) -> str:
    prompt = f"""
    You are a creator who makes fun and engaging sports quiz content for YouTube.
    Create TWO multiple-choice questions about "{topic}" that include interesting and relevant information for casual fans — such as recent performances, head-to-head results, notable storylines, key players, injuries, momentum, or trending news.

    Output strictly ONE JSON object with the following EXACT structure:

    {{
      "questions": [
        {{
          "question": "<max 10 words>",
          "options": ["<max 5 words>", "<max 5 words>", "<max 5 words>", "<max 5 words>"],
          "answer": "<one of the options>"
        }},
        {{
          "question": "<max 10 words>",
          "options": ["<max 5 words>", "<max 5 words>", "<max 5 words>", "<max 5 words>"],
          "answer": "<one of the options>"
        }}
      ]
    }}

    Rules:
    - The two questions must be different.
    - Each question must strictly follow the word limits.
    - Use real, up-to-date information retrieved via browsing.
    - Output ONLY the JSON object — no explanations, no markdown.
    - Ensure each "answer" matches exactly one of its "options".
    - Each question must naturally and explicitly reference the topic "{topic}" within the question text.
    IMPORTANT:
    - Do NOT ask about games, odds, injuries, trades, or records that depend on events after September 2024.
    - When referring to stats or records, phrase them as being
      "through the end of the 2023–24 season" or earlier.
    - Prefer:
      - long-term records or achievements,
      - famous moments or storylines that happened before September 2024.
    - Example: 
      - "question": “During the 2023–24 season, Jokic averaged…”, options: []"26.4", "25.1", 27", "27.4"], answer: "26.4"
      - "question": "Which team won 2019 West Finals sweep?", "options": ["Trail Blazers", "Warriors", "Both tied", "Neither"], "answer": "Warriors"
    """

    response = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}],
        # temperature=0.8,
    )

    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    print(create_quizzes("Taylor Swift"))