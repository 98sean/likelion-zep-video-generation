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
ASSETS = "../assets"
FONT_PATH = os.path.join(ASSETS, "fonts", "Fredoka-Regular.ttf")
FONT_BOLD_PATH = os.path.join(ASSETS, "fonts", "Fredoka-Bold.ttf")
FONT_MEDIUM_PATH = os.path.join(ASSETS, "fonts", "Fredoka-Medium.ttf")
SPEECH_BUBBLE_PATH = os.path.join(ASSETS, "speech_bubble.png")

W, H = 1080, 1920
VIDEO_SIZE = (W, H)
BACKGROUND_COLOR = (118, 104, 255)  # Purple/blue color from design
CYAN = (0, 201, 242)  # #00C9F2 - 카테고리 배지 색상
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_PURPLE = (88, 78, 204)  # For sport icons and text
QUIZ_TEXT_COLOR = (103, 88, 255)  # #6758FF - ? and QUIZ text color
ACCENT = (205, 247, 255)  # #CDF7FF - 정답 표시 배경색
MUTED = (168, 168, 168)  # 정답 외 선택지
FPS = 30

# 오디오 파일
BGM_PATH = os.path.join(ASSETS, "background.mp3")
SFX_CORRECT_PATH = os.path.join(ASSETS, "correct.wav")

# 아이콘 파일 (Flaticon에서 다운로드)
SOCCER_BALL = os.path.join(ASSETS, "sports_balls", "soccer_ball.png")
BASKETBALL_BALL = os.path.join(ASSETS, "sports_balls", "basketball.png")
BASEBALL_BALL = os.path.join(ASSETS, "sports_balls", "baseball.png")
VOLLEYBALL_BALL = os.path.join(ASSETS, "sports_balls", "volleyball.png")
FOOTBALL_BALL = os.path.join(ASSETS, "sports_balls", "football.png")

BALL_ICONS = [SOCCER_BALL, BASKETBALL_BALL, BASEBALL_BALL, VOLLEYBALL_BALL, FOOTBALL_BALL]
BALL_SIZE = 90

# 타이밍
COUNTDOWN_SECONDS = 5
ANSWER_HOLD = 2
OUTPUT = "quiz_video.mp4"

# 레이아웃 간격(픽셀)
LAYOUT_GAP_BUBBLE_TO_BADGE = 60
LAYOUT_GAP_BADGE_TO_CARD = 36


# ----------------------
# 유틸
# ----------------------
def load_font(size, bold=False, medium=False):
    try:
        if bold:
            return ImageFont.truetype(FONT_BOLD_PATH, size)
        elif medium:
            return ImageFont.truetype(FONT_MEDIUM_PATH, size)
        return ImageFont.truetype(FONT_PATH, size)
    except:
        return ImageFont.load_default()


def wrap_text(draw, text, font, max_w):
    """텍스트를 max_width에 맞게 줄바꿈"""
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


def draw_speech_bubble(img, x, y, width, height):
    """말풍선 이미지 사용 (speech_bubble.png)"""
    if os.path.exists(SPEECH_BUBBLE_PATH):
        bubble = Image.open(SPEECH_BUBBLE_PATH).convert("RGBA")
        # 지정된 크기로 리사이즈
        bubble = bubble.resize((width, height))
        img.paste(bubble, (x, y), bubble)
        return (x, y, x + width, y + height)
    else:
        # 이미지 없을 경우 폴백
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((x, y, x + width, y + height), radius=50, fill=WHITE, outline=BLACK, width=6)
        
        tail_points = [
            (x + 80, y + height),
            (x + 30, y + height + 80),
            (x + 120, y + height)
        ]
        draw.polygon(tail_points, fill=WHITE, outline=BLACK)
        
        return (x, y, x + width, y + height)


from PIL import Image, ImageDraw
import os

def draw_ball_progress(img, progress):
    """Draw 5 balls with progressive white backgrounds behind them"""
    # Ensure the base image supports transparency
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    dot_y = 1730  # Y position of balls
    gap = int(W * 0.16)
    start_x = W // 2 - gap * 2
    ball_radius = BALL_SIZE // 2
    bg_radius = ball_radius + 5  # slightly bigger background circle

    # Layer for background circles
    bg_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_bg = ImageDraw.Draw(bg_layer)

    # Draw white background circles behind balls based on progress
    for i in range(5):
        x_center = start_x + i * gap

        if i < progress:
            draw_bg.ellipse(
                [x_center - bg_radius, dot_y - bg_radius, x_center + bg_radius, dot_y + bg_radius],
                fill=(255, 255, 255, 255)  # fully opaque white
            )

    # Merge background layer first
    img.alpha_composite(bg_layer)

    # Draw all ball PNGs on top
    for i in range(5):
        x_center = start_x + i * gap
        if i < len(BALL_ICONS) and os.path.exists(BALL_ICONS[i]):
            this_ball_size = 70 if i == len(BALL_ICONS) - 1 else BALL_SIZE
            ball = Image.open(BALL_ICONS[i]).convert("RGBA").resize((this_ball_size, this_ball_size))
            x = x_center - this_ball_size // 2
            y = dot_y - this_ball_size // 2
            img.alpha_composite(ball, (x, y))

    return img



def render_frame(question, choices, category, progress, reveal, answer_idx):
    """디자인에 맞춘 프레임 렌더링"""
    img = Image.new("RGBA", (W, H), BACKGROUND_COLOR + (255,))
    draw = ImageDraw.Draw(img)

    # 투명도 효과를 위한 오버레이 레이어 생성 (하이라이트 박스를 그릴 곳)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0)) 
    overlay_draw = ImageDraw.Draw(overlay)

    # --- 말풍선 (? / QUIZ) ---
    # 말풍선: 669x486, 위치: x=205, y=150
    bubble_bounds = draw_speech_bubble(img, 205, 150, 669, 486)
    
    # 말풍선 중앙 계산
    bubble_center_x = 205 + 669 // 2
    
    # 물음표: size=180, bold, color=#6758FF, 중앙 정렬
    qmark_font = load_font(180, bold=True)
    qmark_bbox = draw.textbbox((0, 0), "?", font=qmark_font)
    qmark_width = qmark_bbox[2] - qmark_bbox[0]
    qmark_x = bubble_center_x - qmark_width // 2 - 15
    draw.text((qmark_x, 194), "?", font=qmark_font, fill=QUIZ_TEXT_COLOR)
    
    # QUIZ 텍스트: size=110, bold, 중앙 정렬
    quiz_font = load_font(110, bold=True)
    quiz_bbox = draw.textbbox((0, 0), "QUIZ", font=quiz_font)
    quiz_width = quiz_bbox[2] - quiz_bbox[0]
    quiz_x = bubble_center_x - quiz_width // 2 - 10
    quiz_y = 194 + 180 + 20
    draw.text((quiz_x, quiz_y), "QUIZ", font=quiz_font, fill=QUIZ_TEXT_COLOR)

    # --- 카테고리 배지 (SPORTS) ---
    # 파란 박스: width=209, height=78, color=#00C9F2, position: x=154, y=693
    tag_w = 209
    tag_h = 78
    tag_x = 154
    tag_y = 693
    draw.rounded_rectangle([tag_x, tag_y, tag_x + tag_w, tag_y + tag_h], 
                          radius=20, fill=CYAN)
    
    # 텍스트: fontsize=40, Fredoka Medium, 중앙 정렬
    tag_font = load_font(40, medium=True)
    tag_text = category
    tag_bbox = draw.textbbox((0, 0), tag_text, font=tag_font)
    tag_text_width = tag_bbox[2] - tag_bbox[0]
    tag_text_height = tag_bbox[3] - tag_bbox[1]
    tag_text_x = tag_x + (tag_w - tag_text_width) // 2
    tag_text_y = tag_y + (tag_h - tag_text_height) // 2 - tag_bbox[1]
    draw.text((tag_text_x, tag_text_y), tag_text, font=tag_font, fill=WHITE)

    # --- 질문 카드 (772x789, 위치: x=154, y=812) ---
    box_w = 772
    box_h = 789
    box_x = 154
    box_y = 812
    
    draw.rounded_rectangle([box_x, box_y, box_x + box_w, box_y + box_h], 
                          radius=40, fill=WHITE, outline=BLACK, width=5)
    
    # 1. 질문 텍스트: 카드의 가로 중앙에 정렬
    q_font = load_font(52, bold=True)
    q_text = "Q. " + question
    q_lines = wrap_text(draw, q_text, q_font, 700) # 최대 너비 700으로 줄바꿈
    
    y = 906
    card_inner_width = box_w 
    card_start_x = box_x
    for line in q_lines:
        text_width = draw.textlength(line, font=q_font)
        # 텍스트를 카드 내부(772px)의 중앙에 배치
        line_x = card_start_x + (card_inner_width - text_width) // 2
        
        draw.text((line_x, y), line, font=q_font, fill=BLACK)
        y += 60
    
    # 선택지 컨테이너: position: x=234, y=1081, width: 710, height: 456
    ans_font = load_font(48, bold=False) # Regular font for incorrect/unrevealed
    ans_font_medium = load_font(48, medium=True) # Medium font for correct answer
    
    ans_container_x = 234
    ans_container_y = 1096
    ans_container_h = 456
    num_choices = len(choices)
    
    # 각 선택지의 세로 간격 계산 (균등 배치)
    ans_spacing = ans_container_h / num_choices
        
    # --- 진행바 (축구공 등) ---
    draw_ball_progress(img, progress)
    
    # 정답 하이라이트 박스를 먼저 오버레이에 그립니다. (텍스트 아래에 오도록)
    if reveal and 0 <= answer_idx < len(choices):
        box_w_new = 758
        box_h_new = 128
        accent_80_opacity = ACCENT + (204,)
        box_x_start = 161

        # --- compute vertical alignment properly ---
        ascent, descent = ans_font.getmetrics()
        text_height = ascent + descent
        text_center_offset = text_height / 2 - descent

        text_baseline_y = ans_container_y + answer_idx * ans_spacing
        visual_center_y = text_baseline_y + text_center_offset + 14

        box_y_start = visual_center_y - box_h_new / 2

        highlight_box = [
            box_x_start,
            box_y_start,
            box_x_start + box_w_new,
            box_y_start + box_h_new,
        ]
        overlay_draw.rectangle(highlight_box, fill=accent_80_opacity)

    img.alpha_composite(overlay)



    # 이제 텍스트를 그립니다. (합성된 오버레이 위에 텍스트가 오도록)
    for i, ans in enumerate(choices):
        ans_x = ans_container_x
        ans_y = ans_container_y + int(i * ans_spacing) # 텍스트 베이스라인 Y
        
        if reveal and i == answer_idx:
            # 정답은 요청대로 Black 색상, Fredoka Medium 폰트
            current_font = ans_font_medium
            color = BLACK 
            
            # 텍스트의 실제 Y 위치는 ans_y 베이스라인에서 시작
            draw.text((ans_x, ans_y), ans, font=current_font, fill=color)

        elif reveal:
            # 오답은 회색으로
            current_font = ans_font 
            color = MUTED 
            draw.text((ans_x, ans_y), ans, font=current_font, fill=color)
        else:
            # 정답 공개 전에는 모두 검정으로
            current_font = ans_font
            color = BLACK
            draw.text((ans_x, ans_y), ans, font=current_font, fill=color)
    
    return img.convert("RGB")



# ----------------------
# 비디오 생성
# ----------------------
def make_video(quiz_data):
    """카운트다운 애니메이션과 오디오가 포함된 퀴즈 비디오 생성"""
    data = json.loads(quiz_data) if isinstance(quiz_data, str) else quiz_data
    question = data["question"]
    choices = data["choices"]
    answer_idx = data["answerIndex"]
    category = data["category"]

    # 비디오 프레임 - 카운트다운 단계
    clips = []
    for sec in range(COUNTDOWN_SECONDS):
        frame = render_frame(question, choices, category, 
                           progress=sec + 1, reveal=False, answer_idx=answer_idx)
        clips.append(ImageClip(np.array(frame)).set_duration(1))

    # 정답 공개 프레임
    ans_frame = render_frame(question, choices, category, 
                            progress=5, reveal=True, answer_idx=answer_idx)
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
        answer_start = final.duration - ANSWER_HOLD
        sfx_clip = sfx.set_start(answer_start)

    # 정답 구간에서는 BGM 페이드아웃 후 SFX만 재생
    if bgm and sfx_clip:
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


# --- MAIN ---
def main():
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
    
    # 필요한 파일 확인
    missing = []
    for p in [SPEECH_BUBBLE_PATH, BGM_PATH, SFX_CORRECT_PATH] + BALL_ICONS:
        if not os.path.exists(p):
            missing.append(p)
    
    if missing:
        print(f"⚠️  누락된 파일 (비디오는 제한적으로 작동합니다):")
        for m in missing:
            print(f"   - {m}")
    
    make_video(quiz_json_str)


if __name__ == "__main__":
    main()