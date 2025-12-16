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
KNOWLEDGE_CUTOFF = "May 2024"

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

        # Ensure there's at least one question
        if not isinstance(raw_questions, list) or len(raw_questions) == 0:
            logger.warning("Validation Failed: Output is not a list or is empty.")
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
def validate_with_ai(quiz_data: dict, topic: str) -> tuple[list, str]:
    """
    Validates questions individually.
    Returns: (list_valid_question, )
    """
    questions = quiz_data.get("questions", [])
    
    for idx, q in enumerate(questions):
        q["_id"] = idx

    quiz_text = json.dumps(questions, indent=2)

    validation_prompt = f"""
        You are an expert factual validator. Check this trivia quiz:

        TOPIC: "{topic}"

        JSON:
        {quiz_text}

        Check these **FATAL conditions**:
        1. **Factual correctness**: **REJECT ONLY** if the **correct answer provided is provably false** as a stable, verifiable fact (up to {KNOWLEDGE_CUTOFF}). Do not reject if the question is "misleading" but the provided answer is factually correct (e.g., Toluca has 10 titles, Monterrey has 5; rejecting the answer "Toluca" is incorrect).
        2. **Ambiguity**: **REJECT ONLY** if the correct answer is subjective (e.g., 'most important') or if multiple options could also be the single correct answer based on stable facts. **Questions about relative counts/rankings (e.g., "who has more titles?") are allowed if the answer is factually correct.**
        3. **Future content**: Reject if referencing events after **{KNOWLEDGE_CUTOFF}**.
        4. **Topic relevance**: Reject only if the question is completely unrelated to any main entity or component mentioned in the TOPIC: "{topic}".

        - The ten questions must be different.
        - Use only widely-known, verifiable sports facts up to **{KNOWLEDGE_CUTOFF}**.

        Output **strictly** this JSON format:
        {{
            "results": [
                {{ "id": 0, "valid": true, "reason": "" }},
                {{ "id": 1, "valid": false, "reason": "Answer is actually 5, not 4" }}
            ]
        }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-5.1",
            messages=[
                {"role": "system", "content": "You output strict JSON only."},
                {"role": "user", "content": validation_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = response.choices[0].message.content
        result = json.loads(content)
        
        valid_indices = set()
        rejection_notes = []

        # Parse AI results
        for res in result.get("results", []):
            q_id = res.get("id")
            is_valid = res.get("valid")
            reason = res.get("reason", "")
            
            if is_valid:
                valid_indices.add(q_id)
            else:
                rejection_notes.append(f"Q (ID {q_id}) rejected: {reason}")

        # Filter the original list
        final_valid_questions = [q for q in questions if q["_id"] in valid_indices]

        # Cleanup internal ID
        for q in final_valid_questions:
            q.pop("_id", None)

        if len(final_valid_questions) >= 8:
            logger.info(f"AI Check Passed: {len(final_valid_questions)} questions valid.")
            return final_valid_questions, ""
        else:
            logger.warning(f"AI Check Failed: Only {len(final_valid_questions)} valid. Reasons: {'; '.join(rejection_notes)}")
            return [], "; ".join(rejection_notes)

    except Exception as e:
        logger.error(f"AI Validation Error: {e}")
        return [], f"AI Validation Error: {e}"


# -------------------------------------------
# Prompt Builder
# -------------------------------------------
def build_quiz_prompt(topic: str, count: int, existing_questions: list[dict], feedback: str) -> str:
    # Create a summary of what we already have to prevent duplicates
    existing_summaries = ""
    if existing_questions:
        titles = [q['question'] for q in existing_questions]
        existing_summaries = f"""
        **CONTEXT - ALREADY GENERATED QUESTIONS (DO NOT REPEAT THESE):**
        {json.dumps(titles, indent=2)}
        """
    
    # This block is injected only if a previous attempt failed
    feedback_block = ""
    if feedback:
        feedback_block = f"""
        **!!! CRITICAL FEEDBACK - PRIOR ATTEMPT FAILED !!!**
        The last quiz attempt failed validation. **You must strictly avoid the mistake mentioned below and generate two entirely new questions.**
        
        **REASON FOR REJECTION:** {feedback}
        
        **New Questions MUST be factually correct as of {KNOWLEDGE_CUTOFF} and completely unique from the rejected set.**
        """

    base_prompt = f"""
        You are a creator who makes **fun and engaging** sports quiz content for YouTube.
        Create **{count}** NEW multiple-choice questions about "{topic}" that include interesting and relevant information for casual fans.

        {feedback_block}

        **Rules:**
        - The **{count}** questions must be different.
        - **Uniqueness:** Do NOT repeat the content of the "ALREADY GENERATED QUESTIONS".
        - **Limit the word count:** max 12 words for a question and max 6 words for an option.
        - **Verifiable Facts:** Use **widely-known, verifiable sports facts** (e.g., team titles, main stadium names, career totals, draft year, team roster moves).
        - **INFORMATION CUTOFF: All facts MUST be verifiable as of {KNOWLEDGE_CUTOFF}.** Do NOT include any information about events, stats, or team changes that occurred after this date.
        - **Topic Relevance:** Questions must relate to at least one primary component of the TOPIC: "{topic}".
        - **Answer Clarity:** Ensure there is **one clear, correct answer** that exactly matches one option.
        - Avoid overly detailed statistics or rare events unless widely known.
        - Questions must reference the given sports topic directly.
        - Do not generate questions with multiple potentially correct answers.
        - Focus on fun, engaging, and factual sports trivia.
        - All questions and answers MUST be in English

        Output **EXACTLY** this JSON structure - no explanations, no preamble:
        
        {{
          "questions": [
            {{
              "question": "<max 15 words>",
              "options": ["<max 6 words>", "<max 6 words>", "<max 6 words>", "<max 6 words>"],
              "answer": "<one option>"
            }},
            // ... repeat for all {count} items in this list
          ]
        }}
    """
    return base_prompt

# -------------------------------------------
# Quiz Generator (Modified)
# -------------------------------------------
def create_quizzes(topic: str, max_trial=3) -> dict:
    TARGET_COUNT = 10
    collected_questions = []
    rejection_feedback = ""
    
    for attempt in range(max_trial):
        # Check if we desired num of quizzes
        current_count = len(collected_questions)
        if current_count >= TARGET_COUNT:
            break
            
        needed = TARGET_COUNT - current_count
        
        logger.info(f"Attempt {attempt+1}: Have {current_count}, need {needed} more for '{topic}'")

        if attempt > 0:
            time.sleep(1)

        # Build prompt asking only for needed amount
        current_prompt = build_quiz_prompt(topic, needed, collected_questions, rejection_feedback)

        try:
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": "Output valid JSON only."},
                    {"role": "user", "content": current_prompt},
                ],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content.strip()
            raw_data = json.loads(content)
        
        except Exception as e:
            rejection_feedback = f"JSON/API Error: {e}"
            continue
        
        # Structural Validation
        cleaned_data, ok = validate_and_fix_quiz(raw_data)
        if not ok:
            rejection_feedback = "Structural or format issue found (e.g., question too long, wrong number of options, answer not matching option). Ensure all format rules are strictly followed."
            continue

        # AI Fact Check
        new_valid_questions, reason = validate_with_ai(cleaned_data, topic)
        
        if new_valid_questions:
            collected_questions.extend(new_valid_questions)
            rejection_feedback = "" 
        else:
            rejection_feedback = f"Critic rejected batch: {reason}"

    # Final Check
    if len(collected_questions) >= TARGET_COUNT:
        return {"questions": collected_questions[:TARGET_COUNT]}
    
    # Save all valid questions
    if len(collected_questions) > 0: 
        logger.warning(f"Partial success: Returning {len(collected_questions)} questions.")
        return {"questions": collected_questions}
        
    logger.error(f"Failed to generate any valid quizzes for '{topic}'.")
    return {}


# -------------------------------------------
# CLI testing
# -------------------------------------------
if __name__ == "__main__":
    result = create_quizzes("Lionel Messi")
    print(json.dumps(result, indent=2))
