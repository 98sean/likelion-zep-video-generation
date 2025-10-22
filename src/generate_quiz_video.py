import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import (
    ImageClip, concatenate_videoclips,
    AudioFileClip, CompositeAudioClip, vfx
)

# ======================
# 기본 설정 (9:16 숏폼)
# ======================
W, H = 1080, 1920
WHITE = (255, 255, 255)
MAIN_COLOR = (103,88,255)
CARD = (238, 242, 245)
CARD_TEXT = (24, 24, 24)
CATEGORY_BG = (92, 225, 230)
ACCENT = (210, 236, 255) # 정답 표시
MUTED = (180, 188, 196) # 정답 외 선택지

# 폰트 경로 (폰트 따로 추가해야 함)
FONT_REG  = "/System/Library/Fonts/SFCompactRounded.ttf"
FONT_BOLD = "/System/Library/Fonts/Suplemental/Arial Rounded Bold.ttf"

# 타이밍
COUNTDOWN_SECONDS = 5
ANSWER_HOLD = 2
FPS = 30
OUTPUT = "quiz_video.mp4"

# 아이콘/오디오 파일
SOCCER_IMG_PATH = "../assets/soccer.png"
SOCCER_ICON_SIZE = 100
BGM_PATH = "../assets/background.mp3"
SFX_CORRECT_PATH = "../assets/correct.wav"

# 레이아웃 간격(픽셀)
LAYOUT_GAP_BUBBLE_TO_BADGE = 60
LAYOUT_GAP_BADGE_TO_CARD = 36
LAYOUT_CARD_SIDE_PADDING = 46
LAYOUT_Q_TO_CHOICES = 36

# 더미 데이터
quiz_json_str = """
{
  "category": "SPORTS",
  "question": "Which country won the FIFA World Cup in 2022?",
  "choices": [
    "1. France",
    "2. Argentina",
    "3. Brazil",
    "4. Croatia"
  ],
  "answerIndex": 1
}
"""

# ----------------------
# 유틸
# ----------------------
def f_reg(sz):
    try: return ImageFont.truetype(FONT_REG, sz)
    except: return ImageFont.load_default()

def f_bold(sz):
    try: return ImageFont.truetype(FONT_BOLD, sz)
    except: return ImageFont.load_default()

def wrap_text(draw, text, font, max_w):
    lines, words = [], text.split()
    cur = ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

# ----------------------
# 상단 말풍선 (? / QUIZ)
# ----------------------
def draw_speech_bubble(img, text_top="?", text_mid="QUIZ"):
    draw = ImageDraw.Draw(img)
    bubble_w, bubble_h = int(W*0.78), int(H*0.18)
    cx, cy = W//2, int(H*0.15)
    x0, y0 = cx - bubble_w//2, cy - bubble_h//2
    x1, y1 = cx + bubble_w//2, cy + bubble_h//2

    # 그림자
    shadow = Image.new("RGBA", (W, H), (0,0,0,0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle((x0+10, y0+14, x1+10, y1+14), radius=60, fill=(0,0,0,90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    img.alpha_composite(shadow)

    # 말풍선 본체/꼬리
    ImageDraw.Draw(img).rounded_rectangle((x0, y0, x1, y1), radius=60, fill=WHITE)
    tail = [(cx+160, y1-26), (cx+88, y1+70), (cx+32, y1-2)]
    ImageDraw.Draw(img).polygon(tail, fill=WHITE)

    # 텍스트 (Bold)
    t_top = f_bold(int(H*0.08))
    t_mid = f_bold(int(H*0.07))
    draw.text((cx, y0+int(H*0.006)), text_top, fill=MAIN_COLOR, font=t_top, anchor="ma")
    draw.text((cx, y0+int(H*0.084)), text_mid, fill=MAIN_COLOR, font=t_mid, anchor="ma")

    return (x0, y0, x1, y1)  # 말풍선 영역 반환

# ----------------------
# 카테고리 배지
# ----------------------
def draw_category_badge(draw, text, x, y):
    f = f_bold(32)
    pad_x = 26
    text_w = draw.textlength(text, font=f)
    w, h = text_w + pad_x*2, 54
    rect = (x, y, x + w, y + h)
    draw.rounded_rectangle(rect, radius=16, fill=CATEGORY_BG)
    draw.text((x + pad_x, y + 8), text, font=f, fill=WHITE)
    return (w, h)

# ----------------------
# 카드, 질문/선택지, 진행바
# ----------------------
def draw_card_and_contents(img, question, choices, category, anchor_top_y, reveal, answer_idx, progress):
    draw = ImageDraw.Draw(img)

    # 1) 카테고리 배지
    badge_x = int(W*0.08)
    badge_y = anchor_top_y + LAYOUT_GAP_BUBBLE_TO_BADGE
    _, badge_h = draw_category_badge(draw, category, badge_x, badge_y)

    # 2) 카드
    card_w, card_h = int(W*0.86), int(H*0.52)
    cx = W//2
    card_top = badge_y + badge_h + LAYOUT_GAP_BADGE_TO_CARD
    card = (cx - card_w//2, card_top, cx + card_w//2, card_top + card_h)

    # 그림자
    shadow = Image.new("RGBA", (W,H), (0,0,0,0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle((card[0]+12, card[1]+16, card[2]+12, card[3]+16),
                            radius=40, fill=(0,0,0,90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    img.alpha_composite(shadow)

    draw.rounded_rectangle(card, radius=40, fill=CARD, outline=(0,0,0,40), width=1)

    # 3) 질문
    q_font = f_bold(58)
    max_w = card[2] - card[0] - LAYOUT_CARD_SIDE_PADDING*2
    q_lines = wrap_text(draw, "Q. " + question, q_font, max_w)

    y = card[1] + 44
    for ln in q_lines:
        draw.text((card[0] + LAYOUT_CARD_SIDE_PADDING, y), ln, font=q_font, fill=(0,0,0))
        y += 68

    # 4) 선택지
    choice_font = f_reg(56)
    start_y = y + LAYOUT_Q_TO_CHOICES
    line_h = 86
    for i, ch in enumerate(choices):
        box_h = 76
        box = (card[0] + LAYOUT_CARD_SIDE_PADDING,
               start_y + i*line_h,
               card[2] - LAYOUT_CARD_SIDE_PADDING,
               start_y + i*line_h + box_h)

        if reveal:
            if i == answer_idx:
                draw.rounded_rectangle(box, radius=18, fill=ACCENT)
                color = (10,10,10)
            else:
                draw.rounded_rectangle(box, radius=18, fill=None)
                color = MUTED
        else:
            draw.rounded_rectangle(box, radius=18, fill=None)
            color = CARD_TEXT

        draw.text((box[0]+14, box[1]+8), ch, font=choice_font, fill=color)

    # 5) 진행바(축구공)
    draw_soccer_progress(img, progress)

def draw_soccer_progress(img, filled):
    base_icon = Image.open(SOCCER_IMG_PATH).convert("RGBA").resize((SOCCER_ICON_SIZE, SOCCER_ICON_SIZE))
    r,g,b,a = base_icon.split()
    a_faded = a.point(lambda v: int(v*0.35))
    faded = Image.merge("RGBA", (r,g,b,a_faded))

    dot_y = int(H*0.92)
    gap = int(W*0.16)
    start_x = W//2 - gap*2

    for i in range(5):
        x = start_x + i*gap - SOCCER_ICON_SIZE//2
        y = dot_y - SOCCER_ICON_SIZE//2
        img.alpha_composite(base_icon if i < filled else faded, (x, y))

# ----------------------
# 비디오 생성
# ----------------------
def render_frame(question, choices, category, progress, reveal, answer_idx):
    img = Image.new("RGBA", (W, H), MAIN_COLOR + (255,))
    _, _, _, bubble_bottom = draw_speech_bubble(img)
    draw_card_and_contents(img, question, choices, category,
                           anchor_top_y=bubble_bottom,
                           reveal=reveal, answer_idx=answer_idx, progress=progress)
    return img.convert("RGB")

def make_video(quiz_json):
    data = json.loads(quiz_json)
    question = data["question"]
    choices = data["choices"]
    answer_idx = data["answerIndex"]
    category = data["category"]

    # 비디오 프레임
    clips = []
    for sec in range(COUNTDOWN_SECONDS):
        frame = render_frame(question, choices, category, progress=sec+1, reveal=False, answer_idx=answer_idx)
        clips.append(ImageClip(np.array(frame)).set_duration(1))

    ans_frame = render_frame(question, choices, category, progress=5, reveal=True, answer_idx=answer_idx)
    clips.append(ImageClip(np.array(ans_frame)).set_duration(ANSWER_HOLD))

    final = concatenate_videoclips(clips, method="compose")

    # ---------- 오디오 믹스 ----------
    # BGM 로드 및 길이 맞추기
    bgm = None
    if os.path.exists(BGM_PATH):
        bgm = AudioFileClip(BGM_PATH).subclip(0.8).volumex(0.35)
        if bgm.duration < final.duration:
            bgm = bgm.fx(vfx.loop, duration=final.duration)
        else:
            bgm = bgm.subclip(0, final.duration)

    # 정답 효과음
    sfx_clip = None
    if os.path.exists(SFX_CORRECT_PATH):
        sfx = AudioFileClip(SFX_CORRECT_PATH).volumex(1.0)
        answer_start = final.duration - ANSWER_HOLD  # 정답 시작 시점
        sfx_clip = sfx.set_start(answer_start)

    # "정답 구간"에서는 BGM을 완전히 끄고 SFX만 들리게
    if bgm and sfx_clip:
        # 정답 0.3초 전에 BGM 페이드아웃
        fade_duration = 0.3
        answer_start = final.duration - ANSWER_HOLD
        bgm_until_answer = bgm.subclip(0, max(0, answer_start)).audio_fadeout(fade_duration)
        final_audio = CompositeAudioClip([bgm_until_answer, sfx_clip])
        final = final.set_audio(final_audio)
    elif bgm:
        final = final.set_audio(bgm)
    elif sfx_clip:
        final = final.set_audio(sfx_clip)

    final.write_videofile(OUTPUT, fps=FPS, codec="libx264", audio_codec="aac")
    print(f"✅ 비디오 생성 완료: {OUTPUT}")
    return OUTPUT

if __name__ == "__main__":
    missing = []
    for p in [SOCCER_IMG_PATH, BGM_PATH, SFX_CORRECT_PATH]:
        if not os.path.exists(p):
            missing.append(p)
    if missing:
        raise FileNotFoundError("필요 파일이 없습니다: " + ", ".join(missing))
    make_video(quiz_json_str)
