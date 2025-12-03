import json
import re
import time
import random
import logging
from openai import OpenAI
from config import OPENAI_API_KEY

# -------------------------------------------
# Initialization
# -------------------------------------------
client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)

# -------------------------------------------
# Utility helpers
# -------------------------------------------
def normalize(text: str) -> str:
    """Normalize strings for safe comparison."""
    if not text:
        return ""
    return text.strip().strip(".").strip()


def cleanup_text(text: str) -> str:
    """
    Remove common leading prefixes like:
    Q1., Question:, 1), A), etc.
    Avoid removing internal abbreviations like "A.C. Milan".
    """
    if not text:
        return ""

    pattern = r"""
        ^(
            Q\d+[:.]? |                 # Q1. or Q1:
            Question\s*\d*[:.]? |       # Question 1:
            Option\s+[A-D][:.)]? |      # Option A)
            \d+[:.)] |                  # 1. or 2)
            [A-D][.)]                   # A. or B)
        )
        \s+
    """

    return re.sub(pattern, "", text, flags=re.IGNORECASE | re.VERBOSE).strip()


# -------------------------------------------
# Manual / Structural Validation
# -------------------------------------------
def validate_and_fix_quiz(quiz_obj: dict) -> tuple[dict, bool]:
    try:
        if "questions" not in quiz_obj:
            logger.warning("Validation Failed: Missing 'questions' key.")
            return None, False

        raw_questions = quiz_obj["questions"]
        if not isinstance(raw_questions, list) or len(raw_questions) != 2:
            logger.warning("Validation Failed: Expected 2 questions.")
            return None, False

        cleaned_questions = []

        for i, q in enumerate(raw_questions):
            if not all(k in q for k in ["question", "options", "answer"]):
                logger.warning(f"Validation Failed: Q{i+1} missing keys.")
                return None, False

            q_text = cleanup_text(q["question"])

            if len(q_text.split()) > 11:
                logger.warning(f"Validation Failed: Q{i+1} too long.")
                return None, False

            clean_options = [cleanup_text(opt) for opt in q["options"]]

            if len(clean_options) != 4:
                logger.warning(
                    f"Validation Failed: Q{i+1} must have 4 options (got {len(clean_options)})."
                )
                return None, False

            # Word count check (allowing one extra)
            for opt in clean_options:
                if len(opt.split()) > 6:
                    logger.warning(
                        f"Validation Failed: Option '{opt}' too long in Q{i+1}."
                    )
                    return None, False

            # Unique options (case-insensitive)
            if len({normalize(o) for o in clean_options}) != 4:
                logger.warning(
                    f"Validation Failed: Duplicate options detected in Q{i+1}."
                )
                return None, False

            raw_answer = q["answer"]

            # Try exact match
            final_answer = None

            # Try normalized match
            na = normalize(raw_answer)
            for opt in clean_options:
                if normalize(opt) == na:
                    final_answer = opt
                    break

            # Try letter A/B/C/D
            if not final_answer and len(raw_answer) == 1:
                letter = raw_answer.upper()
                if letter in "ABCD":
                    idx = ord(letter) - 65
                    final_answer = clean_options[idx]

            if not final_answer:
                logger.warning(
                    f"Validation Failed: Answer '{raw_answer}' not found in Q{i+1} options."
                )
                return None, False

            cleaned_questions.append(
                {
                    "question": q_text,
                    "options": clean_options,
                    "answer": final_answer,
                }
            )

        result = {"questions": cleaned_questions}
        return result, True

    except Exception as e:
        logger.error(f"Code Validation Crashed: {e}")
        return None, False


# -------------------------------------------
# AI Fact Check
# -------------------------------------------
def validate_with_ai(quiz_data: dict, topic: str) -> bool:
    quiz_text = json.dumps(quiz_data, indent=2)

    validation_prompt = f"""
        You are an expert factual validator. Check this trivia quiz:

        TOPIC: "{topic}"

        JSON:
        {quiz_text}

        Check these FATAL conditions:
        1. **False Information**: Any option or answer factually wrong (up to Sept 2024).
        2. **Ambiguity**: More than one potentially correct answer.
        3. **Topic Relevance**: Are the questions strictly about "{topic}"?
        4. **Future Content**: Reject if referencing events AFTER Sept 2024.

        Respond ONLY with JSON:
        {{
        "valid": boolean,
        "reason": "Explain if invalid; empty if valid."
        }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You output strict JSON only."},
                {"role": "user", "content": validation_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        result = json.loads(response.choices[0].message.content)

        if result.get("valid") is True:
            return True

        logger.warning(f"   AI Critic Rejected:")
        logger.warning(f"   Reason: {result.get('reason')}")
        logger.warning(f"   Rejected Quiz Content:")
        logger.warning(f"   Question: {quiz_data.get('question')}")
        logger.warning(f"   Options: {quiz_data.get('options')}")
        logger.warning(f"   Answer: {quiz_data.get('answer')}")

        return False

    except Exception as e:
        logger.error(f"AI Validation Error: {e}")
        return False


# -------------------------------------------
# Quiz Generator
# -------------------------------------------
def create_quizzes(topic: str, max_trial=3) -> dict:
    prompt = f"""
        You are a creator who makes fun and engaging sports quiz content for YouTube.
        Create TWO multiple-choice questions about "{topic}" that include interesting and relevant information for casual fans — such as recent performances, head-to-head results, notable storylines, key players, injuries, momentum, or trending news.

        Rules:
        - The two questions must be different.
        - Limit the word count, 10 words for a question and 5 words for an option.
        - Ensure each "answer" matches exactly one of its "options".
        - Must reference "{topic}" directly in the question text.
        - Use only factual info up to Sept 2024.
        - Prefer long-term records or achievements, famous moments or storylines that happened before September 2024.
        - No fictional future events and references to information after Sept 2024.
        - Output EXACTLY this JSON structure - no explanations, no markdown like the following:

        {{
          "questions": [
            {{
              "question": "<max 10 words>",
              "options": ["<max 5 words>", "<max 5 words>", "<max 5 words>", "<max 5 words>"],
              "answer": "<one option>"
            }},
            {{
              "question": "<max 10 words>",
              "options": ["<max 5 words>", "<max 5 words>", "<max 5 words>", "<max 5 words>"],
              "answer": "<one option>"
            }}
          ]
        }}

        Examples: 
        - "question": “During the 2023–24 season, Jokic averaged…”, options: []"26.4", "25.1", 27", "27.4"], answer: "26.4"
        - "question": "Which team won 2019 West Finals sweep?", "options": ["Trail Blazers", "Warriors", "Both tied", "Neither"], "answer": "Warriors"

    """

    for attempt in range(max_trial):
        try:
            logger.info(f"Generation attempt {attempt+1} for '{topic}'")

            # Exponential backoff
            if attempt > 0:
                delay = 0.5 * (2 ** attempt) + random.random() * 0.3
                time.sleep(delay)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Output valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content.strip()

            try:
                raw_data = json.loads(content)
            except Exception:
                logger.warning("JSON parsing failed — retrying.")
                continue

            cleaned_data, ok = validate_and_fix_quiz(raw_data)
            if not ok:
                continue

            logger.info("Running AI Fact Check...")
            if validate_with_ai(cleaned_data, topic):
                return cleaned_data

        except Exception as e:
            logger.error(f"API Error: {e}")

    logger.error(f"Failed to generate valid quiz for '{topic}' after {max_trial} attempts.")
    return {}


# -------------------------------------------
# CLI testing
# -------------------------------------------
if __name__ == "__main__":
    result = create_quizzes("Lionel Messi")
    print(json.dumps(result, indent=2))
