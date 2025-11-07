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
FONT_PATH = os.path.join(ASSETS, "fonts", "Nunito-Bold.ttf")
FONT_BOLD_PATH = os.path.join(ASSETS, "fonts", "Nunito-Bold.ttf")
FONT_MEDIUM_PATH = os.path.join(ASSETS, "fonts", "Nunito-Bold.ttf")

# New design assets
ZEP_QUIZ_LOGO = os.path.join(ASSETS, "ZEPQUIZ-logo.png")
PURPLE_QUIZ_BG = os.path.join(ASSETS, "purple_quiz_bg.png")
PURPLE_PAPER = os.path.join(ASSETS, "v1_design", "purple", "purple_paper.png")
PURPLE_ALL_CHOICES = os.path.join(ASSETS, "v1_design", "purple", "purple_all_choices.png")
PURPLE_ANSWER = os.path.join(ASSETS, "v1_design", "purple", "purple_answer.png")

W, H = 1080, 1920
VIDEO_SIZE = (W, H)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PURPLE = (118, 104, 255)
DARK_PURPLE = (88, 78, 204)
CYAN = (0, 201, 242)
MUTED = (168, 168, 168)
LETTER_PURPLE = (87, 72, 242)  # #5748F2 - for ABCD letters
FPS = 30

# 오디오 파일
BGM_PATH = os.path.join(ASSETS, "background.mp3")
SFX_CORRECT_PATH = os.path.join(ASSETS, "correct.wav")

# 타이밍
COUNTDOWN_SECONDS = 5
ANSWER_HOLD = 2
OUTPUT = "quiz_video.mp4"


# ----------------------
# 유틸
# ----------------------
def load_font(size, bold=False, medium=False):
    try:
        return ImageFont.truetype(FONT_BOLD_PATH, size)
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


def draw_progress_bar(img, progress):
    """디자인의 진행 표시줄 그리기 (체크마크와 원)"""
    # Progress bar positioning - moved down
    bar_y = 240
    circle_radius = 30
    line_y = bar_y
    
    # Calculate positions for 5 steps - wider spacing
    total_width = 620
    start_x = (W - total_width) // 2
    step_width = total_width // 4
    
    draw = ImageDraw.Draw(img)
    
    positions = [start_x + i * step_width for i in range(5)]
    
    # Draw connecting lines
    for i in range(4):
        x1, x2 = positions[i], positions[i + 1]

            # Incomplete line (gray)
        draw.line([(x1 + circle_radius, line_y), (x2 - circle_radius, line_y)], 
                    fill=(200, 200, 200), width=10)
    
    # Draw circles and checkmarks/dots
    for i, x in enumerate(positions):
        if i <= progress - 1:
            # Completed step: purple circle with white checkmark
            draw.ellipse([x - circle_radius, bar_y - circle_radius, 
                         x + circle_radius, bar_y + circle_radius], 
                        fill=PURPLE, outline=(200, 200, 200), width=5)
        else:
            # Incomplete step: gray circle
            draw.ellipse([x - circle_radius, bar_y - circle_radius, 
                         x + circle_radius, bar_y + circle_radius], 
                        fill=WHITE, outline=(200, 200, 200), width=5)


def render_frame(question, choices, category, progress, reveal, answer_idx):
    """디자인에 맞춘 프레임 렌더링"""
    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    
    # Load background with 40% opacity and overlay it
    if os.path.exists(PURPLE_QUIZ_BG):
        bg = Image.open(PURPLE_QUIZ_BG).convert("RGBA").resize((W, H))
        # Reduce opacity to 40%
        bg.putalpha(Image.eval(bg.split()[3], lambda a: int(a * 0.8)))
        # Composite the background over the solid purple
        img = Image.alpha_composite(img, bg)
    
    draw = ImageDraw.Draw(img)
    
    # Draw progress bar at top
    draw_progress_bar(img, progress)
    
    # --- Sports Quiz badge ---
    # Position: moved down and made bigger
    badge_y = 387
    badge_text = f"{category} Quiz"
    badge_font = load_font(40, bold=True)
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_w = bbox[2] - bbox[0] + 100
    badge_h = 80
    badge_x = (W - badge_w) // 2
    
    draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
                          radius=40, fill=PURPLE)
    
    text_x = badge_x + (badge_w - (bbox[2] - bbox[0])) // 2
    text_y = badge_y + (badge_h - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((text_x, text_y), badge_text, font=badge_font, fill=WHITE)
    
    # --- Purple paper background for question ---
    # Wider and moved down
    paper_y = 486
    paper_width = 925
    paper_height = 385
    
    if os.path.exists(PURPLE_PAPER):
        paper = Image.open(PURPLE_PAPER).convert("RGBA")
        paper = paper.resize((paper_width, paper_height))
        paper_x = 90
        img.paste(paper, (paper_x, paper_y), paper)
    else:
        # Fallback: draw rounded rectangle
        paper_x = (W - paper_width) // 2
        draw.rounded_rectangle([paper_x, paper_y, paper_x + paper_width, paper_y + paper_height],
                              radius=35, fill=(200, 190, 255))
    
    # --- Question text ---
    q_font = load_font(62, bold=True)
    q_text = f"Q. {question}"
    q_lines = wrap_text(draw, q_text, q_font, 800)
    
    # Calculate total height of all lines
    line_height = 65
    total_text_height = len(q_lines) * line_height
    
    # Center text block vertically within paper
    q_y = paper_y + (paper_height - total_text_height) // 2
    
    for line in q_lines:
        bbox = draw.textbbox((0, 0), line, font=q_font)
        line_w = bbox[2] - bbox[0]
        line_x = (W - line_w) // 2
        draw.text((line_x, q_y), line, font=q_font, fill=BLACK)
        q_y += line_height
    
    # --- Answer choices ---
    # Moved down significantly and made wider
    choices_y = 914
    choices_width = 726
    choices_height = 536
    
    if os.path.exists(PURPLE_ALL_CHOICES):
        # Use the pre-made choices image with ABCD
        choices_img = Image.open(PURPLE_ALL_CHOICES).convert("RGBA")
        choices_img = choices_img.resize((choices_width, choices_height))
        choices_x = (W - choices_width) // 2
        
        # Paste the base choices image first
        img.paste(choices_img, (choices_x, choices_y), choices_img)
        
        # If revealing answer, overlay purple_answer.png on the correct answer
        if reveal and os.path.exists(PURPLE_ANSWER):
            purple_ans_img = Image.open(PURPLE_ANSWER).convert("RGBA")
            # Size of a single answer bubble
            single_answer_height = choices_height // 4
            purple_ans_img = purple_ans_img.resize((choices_width, single_answer_height))
            # Position it over the correct answer
            answer_y_offset = int(answer_idx * single_answer_height)
            img.paste(purple_ans_img, (choices_x, choices_y + answer_y_offset), purple_ans_img)
        
        # Now recreate draw object since we modified img
        draw = ImageDraw.Draw(img)
        
        # Add ABCD letters in the circles
        labels = ["A", "B", "C", "D"]
        letter_font = load_font(49, bold=True)
        circle_center_x = choices_x + 60
        choice_spacing = choices_height / 4 + 2.5
        
        for i in range(4):
            letter = labels[i]
            letter_bbox = draw.textbbox((0, 0), letter, font=letter_font)
            letter_width = letter_bbox[2] - letter_bbox[0]
            letter_height = letter_bbox[3] - letter_bbox[1]
            
            # Center letter in the circle
            letter_x = circle_center_x - letter_width // 2 + 1
            letter_y_center = choices_y + int(i * choice_spacing + choice_spacing / 2)
            letter_y = letter_y_center - letter_height // 2 - letter_bbox[1] - 5
            
            # Always use purple color for letters
            draw.text((letter_x, letter_y), letter, font=letter_font, fill=LETTER_PURPLE)
        
        # Add answer text on top of the choices bubbles
        ans_font = load_font(56, medium=False)
        
        for i, ans in enumerate(choices):
            # Remove number prefix if exists
            clean_ans = ans.split(". ", 1)[-1] if ". " in ans else ans
            
            # Calculate text dimensions
            text_bbox = draw.textbbox((0, 0), clean_ans, font=ans_font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # Center text horizontally
            text_x = choices_x + (choices_width - text_width) // 2
            
            # Center text vertically - align with ABCD
            text_y_center = choices_y + int(i * choice_spacing + choice_spacing / 2)
            text_y = text_y_center - text_height // 2 - text_bbox[1] - 5
            
            # All text stays black
            draw.text((text_x, text_y), clean_ans, font=ans_font, fill=BLACK)
    else:
        # Fallback: draw simple choice list
        ans_font = load_font(56)
        choice_spacing = 120
        text_x = 280
        
        for i, ans in enumerate(choices):
            labels = ["A", "B", "C", "D"]
            text = f"{labels[i]}. {ans.split('. ', 1)[-1] if '. ' in ans else ans}"
            text_y = choices_y + i * choice_spacing
            
            if reveal and i == answer_idx:
                color = PURPLE
            else:
                color = BLACK
            
            draw.text((text_x, text_y), text, font=ans_font, fill=color)
    
    # --- ZEP QUIZ logo at bottom ---
    logo_y = 1560
    if os.path.exists(ZEP_QUIZ_LOGO):
        logo = Image.open(ZEP_QUIZ_LOGO).convert("RGBA")
        logo_width = 342
        aspect = logo.height / logo.width
        logo = logo.resize((logo_width, int(logo_width * aspect)))
        logo_x = (W - logo_width) // 2
        img.paste(logo, (logo_x, logo_y), logo)
    else:
        logo_font = load_font(70, bold=True)
        logo_text = "ZEP QUIZ"
        bbox = draw.textbbox((0, 0), logo_text, font=logo_font)
        logo_x = (W - (bbox[2] - bbox[0])) // 2
        draw.text((logo_x, logo_y), logo_text, font=logo_font, fill=PURPLE)
    
    return img.convert("RGB")


# ----------------------
# 비디오 생성
# ----------------------
def make_video(quiz_data):
    """카운트다운 애니메이션과 오디오가 포함된 퀴즈 비디오 생성"""
    data = json.loads(quiz_data) if isinstance(quiz_data, str) else quiz_data
    question = data["question"]
    choices = data["options"]
    answer = data["answer"]
    category = data["category"].capitalize()
    
    # Find answer index from the answer text
    answer_idx = choices.index(answer) if answer in choices else 0

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
    bgm = None
    if os.path.exists(BGM_PATH):
        bgm = AudioFileClip(BGM_PATH).subclip(0.8).volumex(0.35)
        if bgm.duration < final.duration:
            bgm = bgm.fx(vfx.loop, duration=final.duration)
        else:
            bgm = bgm.subclip(0, final.duration)

    sfx_clip = None
    if os.path.exists(SFX_CORRECT_PATH):
        sfx = AudioFileClip(SFX_CORRECT_PATH).volumex(1.0)
        answer_start = final.duration - ANSWER_HOLD
        sfx_clip = sfx.set_start(answer_start)

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
      "category": "sports",
      "question": "Which country won the FIFA World Cup in 2022?",
      "options": [
        "France",
        "Argentina",
        "Brazil",
        "Croatia"
      ],
      "answer": "Argentina"
    }
    """
    
    # 필요한 파일 확인
    required_files = [
        ZEP_QUIZ_LOGO,
        PURPLE_QUIZ_BG,
        PURPLE_PAPER,
        PURPLE_ALL_CHOICES,
        PURPLE_ANSWER,
        BGM_PATH,
        SFX_CORRECT_PATH
    ]
    
    missing = [p for p in required_files if not os.path.exists(p)]
    
    if missing:
        print(f"⚠️  누락된 파일 (비디오는 제한적으로 작동합니다):")
        for m in missing:
            print(f"   - {m}")
    
    make_video(quiz_json_str)


if __name__ == "__main__":
    main()