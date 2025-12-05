import json
import re
import time
import random
import logging
from openai import OpenAI
from .config import OPENAI_API_KEY

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

            if len(q_text.split()) > 12:
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
def validate_with_ai(quiz_data: dict, topic: str) -> tuple[bool, str]:
    quiz_text = json.dumps(quiz_data, indent=2)

    validation_prompt = f"""
        You are an expert factual validator. Check this trivia quiz:

        TOPIC: "{topic}"

        JSON:
        {quiz_text}

        Check these **FATAL conditions**:
        1. **Factual correctness**: **REJECT ONLY** if the **correct answer provided is provably false** as a stable, verifiable fact (up to Sept 2024). Do not reject if the question is "misleading" but the provided answer is factually correct (e.g., Toluca has 10 titles, Monterrey has 5; rejecting the answer "Toluca" is incorrect).
        2. **Ambiguity**: **REJECT ONLY** if the correct answer is subjective (e.g., 'most important') or if multiple options could also be the single correct answer based on stable facts. **Questions about relative counts/rankings (e.g., "who has more titles?") are allowed if the answer is factually correct.**
        3. **Future content**: Reject if referencing events after **September 2024**.
        4. **Topic relevance**: Reject only if the question is completely unrelated to any main entity or component mentioned in the TOPIC: "{topic}".

        - The two questions must be different.
        - Ensure each "answer" matches exactly one of its "options".
        - Use only widely-known, verifiable sports facts up to **September 2024**.

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
        reason = result.get("reason", "Unknown AI rejection reason.")

        if result.get("valid") is True:
            return True, ""

        logger.warning(f"    AI Critic Rejected:")
        logger.warning(f"    Reason: {reason}")
        logger.warning(f"    Rejected Quiz Content:")
        for i, q in enumerate(quiz_data.get("questions", []), start=1):
            logger.warning(f"    Q{i}: {q.get('question')}")
            logger.warning(f"        Options: {q.get('options')}")
            logger.warning(f"        Answer: {q.get('answer')}")

        return False, reason

    except Exception as e:
        logger.error(f"AI Validation Error: {e}")
        return False, f"AI Validation Error: {e}"

# -------------------------------------------
# Prompt Builder
# -------------------------------------------
def build_quiz_prompt(topic: str, feedback: str) -> str:
    # This block is injected only if a previous attempt failed
    feedback_block = ""
    if feedback:
        feedback_block = f"""
        **!!! CRITICAL FEEDBACK - PRIOR ATTEMPT FAILED !!!**
        The last quiz attempt failed validation. **You must strictly avoid the mistake mentioned below and generate two entirely new questions.**
        
        **REASON FOR REJECTION:** {feedback}
        
        **New Questions MUST be factually correct as of Sept 2024 and completely unique from the rejected set.**
        """

    base_prompt = f"""
        You are a creator who makes **fun and engaging** sports quiz content for YouTube.
        Create TWO multiple-choice questions about "{topic}" that include interesting and relevant information for casual fans.

        {feedback_block}

        **Rules:**
        - The two questions must be different.
        - **Limit the word count:** max 12 words for a question and max 6 words for an option.
        - **Verifiable Facts:** Use **widely-known, verifiable sports facts** (e.g., team titles, main stadium names, career totals, draft year, team roster moves).
        - **INFORMATION CUTOFF: All facts MUST be verifiable as of September 2024.** Do NOT include any information about events, stats, or team changes that occurred after this date.
        - **Topic Relevance:** Questions must relate to at least one primary component of the TOPIC: "{topic}".
        - **Answer Clarity:** Ensure there is **one clear, correct answer** that exactly matches one option.
        - Avoid overly detailed statistics or rare events unless widely known.
        - Questions must reference the given sports topic directly.
        - Do not generate questions with multiple potentially correct answers.
        - Focus on fun, engaging, and factual sports trivia.

        Output **EXACTLY** this JSON structure - no explanations, no preamble:
        
        {{
          "questions": [
            {{
              "question": "<max 12 words>",
              "options": ["<max 6 words>", "<max 6 words>", "<max 6 words>", "<max 6 words>"],
              "answer": "<one option>"
            }},
            {{
              "question": "<max 12 words>",
              "options": ["<max 6 words>", "<max 6 words>", "<max 6 words>", "<max 6 words>"],
              "answer": "<one option>"
            }}
          ]
        }}
    """
    return base_prompt

# -------------------------------------------
# Quiz Generator (Modified)
# -------------------------------------------
def create_quizzes(topic: str, max_trial=3) -> dict:
    # Initialize the feedback message for the first attempt
    rejection_feedback = "" 
    
    for attempt in range(max_trial):
        try:
            logger.info(f"Generation attempt {attempt+1} for '{topic}'")

            # Exponential backoff
            if attempt > 0:
                delay = 0.5 * (2 ** attempt) + random.random() * 0.3
                time.sleep(delay)

            # --- Build the prompt dynamically
            current_prompt = build_quiz_prompt(topic, rejection_feedback)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Output valid JSON only."},
                    {"role": "user", "content": current_prompt},
                ],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content.strip()

            try:
                raw_data = json.loads(content)
            except Exception:
                # If JSON parsing fails, set generic feedback for regeneration
                rejection_feedback = "The model outputted invalid or unparseable JSON. You must strictly adhere to the requested JSON format."
                logger.warning("JSON parsing failed — retrying.")
                continue

            cleaned_data, ok = validate_and_fix_quiz(raw_data)
            if not ok:
                # If structural validation fails, set generic feedback
                rejection_feedback = "Structural or format issue found (e.g., question too long, wrong number of options, answer not matching option). Ensure all length and format rules are strictly followed."
                continue

            logger.info("Running AI Fact Check...")
            valid, reason = validate_with_ai(cleaned_data, topic) # New: Captures the reason
            
            if valid:
                return cleaned_data
            else:
                # Store the rejection reason and the rejected questions for the next attempt
                q1_details = f"Q1: {cleaned_data['questions'][0]['question']} -> Answer was '{cleaned_data['questions'][0]['answer']}'."
                q2_details = f"Q2: {cleaned_data['questions'][1]['question']} -> Answer was '{cleaned_data['questions'][1]['answer']}'."
                rejection_feedback = f"Critic Reason: {reason}. Rejected Questions: {q1_details} {q2_details}"
                logger.warning("Critic rejected — regenerating...")
                continue


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
