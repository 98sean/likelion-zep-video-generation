import httpx
import logging
import uuid
from typing import Optional
from .config import QUIZ_API_URL, QUIZ_API_KEY

logger = logging.getLogger(__name__)


# 하드코딩된 기본값 (필요에 따라 수정)
DEFAULT_TEMPLATE_ID = "6943ae0d24f94d56d7e43dc1"
DEFAULT_CATEGORY_TREE_ID = "1090027"
DEFAULT_SCHOOL_SEMESTER = None
DEFAULT_PUBLISHER = None


def build_quiz_request(
    topic: str,
    questions: list[dict],
    title: Optional[str] = None,
    template_id: str = DEFAULT_TEMPLATE_ID,
    category_tree_id: str = DEFAULT_CATEGORY_TREE_ID,
) -> dict:
    """
    생성된 퀴즈 데이터를 외부 API 형식으로 변환합니다.

    Args:
        topic: 퀴즈 주제
        questions: 퀴즈 리스트 (quiz_batch.py에서 생성된 형식, 2문제 고정)
        title: 퀴즈셋 제목 (None이면 topic 사용)
        template_id: 템플릿 ID
        category_tree_id: 카테고리 트리 ID

    Returns:
        API 요청 형식의 dict
    """
    if len(questions) != 2:
        logger.warning(f"⚠️ 퀴즈는 2문제여야 합니다. 현재: {len(questions)}문제")

    quiz_list = []

    for idx, q in enumerate(questions):
        # 정답의 인덱스 찾기 (0, 1, 2, 3)
        answer_text = q["answer"]
        try:
            answer_index = str(q["options"].index(answer_text))
        except ValueError:
            # 정답이 options에 없으면 첫 번째를 정답으로 처리
            logger.warning(f"⚠️ 정답 '{answer_text}'이 options에 없습니다. 첫 번째를 정답으로 처리합니다.")
            answer_index = "0"

        quiz_item = {
            "id": str(uuid.uuid4()),
            "type": "multiple",  # 객관식
            "order": idx,
            "subjectiveData": None,
            "multipleData": {
                "question": q["question"],
                "questionRichText": f'<p>{q["question"]}</p>',
                "answerList": [answer_index],  # 정답 인덱스 ("0", "1", "2", "3")
                "choiceListV2": [
                    {
                        "key": str(uuid.uuid4()),  # 고유 key 생성
                        "text": opt,
                        "richText": f"<p>{opt}</p>",
                        "isAnswer": (str(i) == answer_index)  # 정답 여부
                    }
                    for i, opt in enumerate(q["options"])
                ]
            },
            "oxData": None,
            "imageUrl": "",
            "hint": {}
        }
        quiz_list.append(quiz_item)

    request_body = {
        "title": title or f"{topic} Quiz",
        "templateId": template_id,
        "categoryTreeData": {
            "categoryTreeId": category_tree_id,
            "schoolSemester": None,
            "publisher": None
        },
        "quizsetOptions": {
            "isPublic": True,
            "isAllowPass": True,
            "showIncorrectAnswer": False,
            "isLastSchoolInfoSaved": False,
            "isAiTranslationEnabled": False
        },
        "quizList": quiz_list,
        "originQuizSetId": None,
        "materials": [],
        "isNextQuizsetAvailable": False,
        "nextQuizsetId": None,
        "aiTranslationLanguages": [],
        "aiTutorId": None
    }

    return request_body


async def save_quizzes_to_api(
    topic: str,
    questions: list[dict],
    title: Optional[str] = None,
    template_id: str = DEFAULT_TEMPLATE_ID,
    category_tree_id: str = DEFAULT_CATEGORY_TREE_ID,
) -> dict:
    """
    퀴즈를 외부 API에 저장합니다.

    Args:
        topic: 퀴즈 주제
        questions: 퀴즈 리스트
        title: 퀴즈셋 제목
        template_id: 템플릿 ID
        category_tree_id: 카테고리 트리 ID

    Returns:
        API 응답 결과
    """
    request_body = build_quiz_request(
        topic=topic,
        questions=questions,
        title=title,
        template_id=template_id,
        category_tree_id=category_tree_id,
    )

    # 요청 데이터 로깅
    import json
    logger.info(f"📤 Sending quiz to API: {json.dumps(request_body, indent=2, ensure_ascii=False)}")

    # HTTP 헤더 설정
    headers = {
        "Content-Type": "application/json"
    }

    # API Key가 있으면 Authorization 헤더 추가 (Bearer token)
    if QUIZ_API_KEY:
        headers["Authorization"] = f"Bearer {QUIZ_API_KEY}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                QUIZ_API_URL,
                json=request_body,
                headers=headers
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"✅ Quiz saved to API: {result.get('id', 'unknown')}")
            return {
                "success": True,
                "data": result
            }

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ API HTTP Error: {e.response.status_code} - {e.response.text}")
        return {
            "success": False,
            "error": f"HTTP {e.response.status_code}",
            "detail": e.response.text
        }

    except httpx.RequestError as e:
        logger.error(f"❌ API Request Error: {e}")
        return {
            "success": False,
            "error": "Request failed",
            "detail": str(e)
        }

    except Exception as e:
        logger.error(f"❌ Unexpected Error: {e}")
        return {
            "success": False,
            "error": "Unexpected error",
            "detail": str(e)
        }
