import json, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import (
    ImageClip, concatenate_videoclips,
    AudioFileClip, CompositeAudioClip, vfx
)

# ======================
# 기본 설정 (9:16 숏폼)
# ======================
# Base directory for generate_quiz_video.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Normalize "../assets" properly
ASSETS = os.path.normpath(os.path.join(BASE_DIR, "..", "assets"))

# Helper to ensure POSIX paths for ffmpeg/moviepy
def px(path):
    return path.replace("\\", "/")

FONT_PATH = os.path.join(ASSETS, "fonts", "Nunito-Bold.ttf")
FONT_BOLD_PATH = os.path.join(ASSETS, "fonts", "Nunito-Bold.ttf")
FONT_MEDIUM_PATH = os.path.join(ASSETS, "fonts", "Nunito-Bold.ttf")

W, H = 1080, 1920
VIDEO_SIZE = (W, H)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
CYAN = (0, 201, 242)
MUTED = (168, 168, 168)
FPS = 30

# Theme-specific colors
THEME_COLORS = {
    "purple": {
        "letter": (87, 72, 242),  # #5748F2
        "primary": (118, 104, 255),  # #7668FF
    },
    "green": {
        "letter": (21, 176, 156),  # #15B09C
        "primary": (21, 176, 156),  # #15B09C
    },
    "blue": {
        "letter": (13, 148, 255),  # #0D94FF
        "primary": (13, 148, 255),  # #0D94FF
    }
}

# 오디오 파일
BGM_PATH = os.path.normpath(os.path.join(ASSETS, "background.mp3"))
SFX_CORRECT_PATH = os.path.normpath(os.path.join(ASSETS, "correct.wav"))

BGM_PATH = px(BGM_PATH)
SFX_CORRECT_PATH = px(SFX_CORRECT_PATH)

# 타이밍
COUNTDOWN_SECONDS = 5
ANSWER_HOLD = 2
OUTPUT = "quiz_video.mp4"

# Available themes
AVAILABLE_THEMES = ["purple", "green", "blue"]


def get_theme_assets(theme):
    """Return asset paths for the given theme (purple, green, or blue)"""
    theme_dir = os.path.normpath(os.path.join(ASSETS, "v1_design", theme))
    
    assets = {
        "logo": px(os.path.normpath(os.path.join(ASSETS, "ZEPQUIZ-logo.png"))),
        "quiz_bg": px(os.path.normpath(os.path.join(theme_dir, f"{theme}_quiz_bg.png"))),
        "paper": px(os.path.normpath(os.path.join(theme_dir, f"{theme}_paper.png"))),
        "all_choices": px(os.path.normpath(os.path.join(theme_dir, f"{theme}_all_choices.png"))),
        "answer": px(os.path.normpath(os.path.join(theme_dir, f"{theme}_answer.png")))
    }
    
    return assets


# ----------------------
# 유틸
# ----------------------
def load_font(size, bold=False, medium=False):
    try:
        return ImageFont.truetype(FONT_BOLD_PATH, size)
    except Exception:
        return ImageFont.load_default()


def wrap_text(draw, text, font, max_w):
    """텍스트를 max_width에 맞게 줄바꿈"""
    lines, words = [], text.split()
    cur = ""
    for w in words:
        t = (cur + " " + w).strip()
        # use draw.textlength for width measurement if available
        try:
            length = draw.textlength(t, font=font)
        except Exception:
            # fallback: approximate using character count
            length = len(t) * (font.size * 0.55)
        if length <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_progress_bar(img, progress, theme_color):
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
            # Completed step: theme color circle
            draw.ellipse([x - circle_radius, bar_y - circle_radius,
                          x + circle_radius, bar_y + circle_radius],
                         fill=theme_color, outline=(200, 200, 200), width=5)
        else:
            # Incomplete step: gray circle
            draw.ellipse([x - circle_radius, bar_y - circle_radius,
                          x + circle_radius, bar_y + circle_radius],
                         fill=WHITE, outline=(200, 200, 200), width=5)


def get_font_for_text(draw, text, base_size, max_w, min_size=20, step=2, bold=True):
    """
    Return an ImageFont instance whose rendered text width is <= max_w.
    Start from base_size and decrement by 'step' until it fits or min_size reached.
    """
    size = base_size
    font = load_font(size, bold=bold)
    # handle cases where draw.textlength might not exist
    while size >= min_size:
        try:
            length = draw.textlength(text, font=font)
        except Exception:
            # approximate by char count
            length = len(text) * (size * 0.55)
        if length <= max_w:
            return font
        size -= step
        font = load_font(size, bold=bold)
    return font  # returns smallest tried if nothing fits


def get_smallest_font_size_for_choices(draw, choices, base_size, max_w, min_size=20, step=2):
    """
    Calculate the smallest font size needed to fit all answer choices.
    Returns the font size (int) that works for the longest choice.
    """
    smallest_size = base_size
    
    for ans in choices:
        # Remove number prefix if exists
        clean_ans = ans.split(". ", 1)[-1] if ". " in ans else ans
        
        size = base_size
        while size >= min_size:
            font = load_font(size, bold=False)
            try:
                length = draw.textlength(clean_ans, font=font)
            except Exception:
                length = len(clean_ans) * (size * 0.55)
            
            if length <= max_w:
                # This size works for this choice
                break
            size -= step
        
        # Track the smallest size needed across all choices
        smallest_size = min(smallest_size, size)
    
    return max(smallest_size, min_size)  # Ensure we don't go below min_size


def validate_word_limits(question, choices, q_limit=10, a_limit=5):
    """
    Soft validation: warn if question has more than q_limit words or choices exceed a_limit.
    This does not truncate; it only prints warnings so user can inspect input.
    """
    q_words = len(question.split())
    if q_words > q_limit:
        print(f"⚠️  Question word count ({q_words}) exceeds {q_limit} words: \"{question}\"")
    for i, ans in enumerate(choices):
        a_words = len(ans.split())
        if a_words > a_limit:
            print(f"⚠️  Choice {i} word count ({a_words}) exceeds {a_limit} words: \"{ans}\"")


def get_question_font_and_lines(draw, question_text, base_size=62, max_w=800, min_size=28):
    """
    Choose a font size so that the question wraps into at most 2 lines.
    If wrapping produces >2 lines, merge remaining words into the 2nd line.
    Returns (font, lines) where lines is a list of 1 or 2 strings.
    """
    # Try decreasing font sizes until the question can be represented in <=2 lines and both fit width.
    for size in range(base_size, min_size - 1, -2):
        font = load_font(size, bold=True)
        lines = wrap_text(draw, question_text, font, max_w)
        if len(lines) <= 2:
            # check widths
            fits = True
            for ln in lines:
                try:
                    wlen = draw.textlength(ln, font=font)
                except Exception:
                    wlen = len(ln) * (font.size * 0.55)
                if wlen > max_w:
                    fits = False
                    break
            if fits:
                return font, lines
        else:
            # Merge so that we have exactly 2 lines: keep first line, merge the rest into second
            first = lines[0]
            second = " ".join(lines[1:])
            # check widths for this size
            try:
                w1 = draw.textlength(first, font=font)
                w2 = draw.textlength(second, font=font)
            except Exception:
                w1 = len(first) * (font.size * 0.55)
                w2 = len(second) * (font.size * 0.55)
            if w1 <= max_w and w2 <= max_w:
                return font, [first, second]
            # else continue to smaller font
    # fallback: smallest font and force two-line split if possible
    font = load_font(min_size, bold=True)
    lines = wrap_text(draw, question_text, font, max_w)
    if len(lines) > 2:
        lines = [lines[0], " ".join(lines[1:])]
    return font, lines


def render_frame(question, choices, category, progress, reveal, answer_idx, theme_assets, theme):
    """디자인에 맞춘 프레임 렌더링"""
    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    
    # Get theme colors
    letter_color = THEME_COLORS[theme]["letter"]
    primary_color = THEME_COLORS[theme]["primary"]

    # Load background with 40% opacity and overlay it
    if os.path.exists(theme_assets["quiz_bg"]):
        try:
            bg = Image.open(theme_assets["quiz_bg"]).convert("RGBA").resize((W, H))
            # Reduce opacity to ~80% of original alpha (keeps it visible but muted)
            if bg.mode == "RGBA" and len(bg.split()) >= 4:
                bg.putalpha(Image.eval(bg.split()[3], lambda a: int(a * 0.8)))
            # Composite the background over the solid white
            img = Image.alpha_composite(img, bg)
        except Exception:
            pass

    draw = ImageDraw.Draw(img)

    # Draw progress bar at top
    draw_progress_bar(img, progress, primary_color)

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
                           radius=40, fill=primary_color)

    text_x = badge_x + (badge_w - (bbox[2] - bbox[0])) // 2
    text_y = badge_y + (badge_h - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((text_x, text_y), badge_text, font=badge_font, fill=WHITE)

    # --- Purple paper background for question ---
    # Wider and moved down
    paper_y = 486
    paper_width = 925
    paper_height = 385

    if os.path.exists(theme_assets["paper"]):
        try:
            paper = Image.open(theme_assets["paper"]).convert("RGBA")
            paper = paper.resize((paper_width, paper_height))
            paper_x = 90
            img.paste(paper, (paper_x, paper_y), paper)
        except Exception:
            paper_x = (W - paper_width) // 2
            draw.rounded_rectangle([paper_x, paper_y, paper_x + paper_width, paper_y + paper_height],
                                   radius=35, fill=(200, 190, 255))
    else:
        # Fallback: draw rounded rectangle
        paper_x = (W - paper_width) // 2
        draw.rounded_rectangle([paper_x, paper_y, paper_x + paper_width, paper_y + paper_height],
                               radius=35, fill=(200, 190, 255))

    # --- Question text ---
    # Dynamically select font size and ensure at most 2 lines
    q_text = f"Q. {question}"
    q_draw = ImageDraw.Draw(img)
    q_font, q_lines = get_question_font_and_lines(q_draw, q_text, base_size=62, max_w=800, min_size=28)

    # Calculate total height of all lines using measured font height
    # Use ascent/descent if available; fallback to font.size + padding
    try:
        ascent, descent = q_font.getmetrics()
        measured_line_height = ascent + descent + 6
    except Exception:
        measured_line_height = q_font.size + 8

    total_text_height = len(q_lines) * measured_line_height

    # Center text block vertically within paper
    q_y = paper_y + (paper_height - total_text_height) // 2

    for line in q_lines:
        bbox = q_draw.textbbox((0, 0), line, font=q_font)
        line_w = bbox[2] - bbox[0]
        line_x = (W - line_w) // 2
        q_draw.text((line_x, q_y), line, font=q_font, fill=BLACK)
        q_y += measured_line_height

    # --- Answer choices ---
    # Moved down significantly and made wider
    choices_y = 914
    choices_width = 726
    choices_height = 536

    if os.path.exists(theme_assets["all_choices"]):
        # Use the pre-made choices image with ABCD
        try:
            choices_img = Image.open(theme_assets["all_choices"]).convert("RGBA")
            choices_img = choices_img.resize((choices_width, choices_height))
            choices_x = (W - choices_width) // 2

            # Paste the base choices image first
            img.paste(choices_img, (choices_x, choices_y), choices_img)
        except Exception:
            # fallback placement
            choices_x = (W - choices_width) // 2
            draw.rounded_rectangle([choices_x, choices_y, choices_x + choices_width, choices_y + choices_height],
                                   radius=20, fill=(245, 245, 245))

        # If revealing answer, overlay purple_answer.png on the correct answer
        if reveal and os.path.exists(theme_assets["answer"]):
            try:
                purple_ans_img = Image.open(theme_assets["answer"]).convert("RGBA")
                # Size of a single answer bubble
                single_answer_height = choices_height // 4
                purple_ans_img = purple_ans_img.resize((choices_width, single_answer_height))
                # Position it over the correct answer
                answer_y_offset = int(answer_idx * single_answer_height)
                img.paste(purple_ans_img, (choices_x, choices_y + answer_y_offset), purple_ans_img)
            except Exception:
                pass

        # Now recreate draw object since we modified img
        draw = ImageDraw.Draw(img)

        # Add ABCD letters in the circles
        labels = ["A", "B", "C", "D"]
        letter_font = load_font(49, bold=True)
        # circle_center_x is leftmost area for ABCD circle center
        circle_center_x = choices_x + 60
        circle_radius = 28  # approximate radius used in background art
        # We'll place the text area to the right of the ABCD bubble with balanced padding
        left_text_x = choices_x + (circle_center_x - choices_x) + circle_radius + 25  # balanced left padding after bubble
        right_text_x_limit = choices_x + choices_width - 35  # balanced right padding inside bubble area
        choice_spacing = choices_height / 4 + 2.5

        # Draw the ABCD letters
        for i in range(4):
            letter = labels[i]
            letter_bbox = draw.textbbox((0, 0), letter, font=letter_font)
            letter_width = letter_bbox[2] - letter_bbox[0]
            letter_height = letter_bbox[3] - letter_bbox[1]

            # Center letter in the circle
            letter_x = circle_center_x - letter_width // 2 + 1
            letter_y_center = choices_y + int(i * choice_spacing + choice_spacing / 2)
            letter_y = letter_y_center - letter_height // 2 - letter_bbox[1] - 5

            # Use theme-specific letter color
            draw.text((letter_x, letter_y), letter, font=letter_font, fill=letter_color)

        # Calculate uniform font size for all answer choices
        single_answer_width = int(right_text_x_limit - left_text_x)
        ans_draw = ImageDraw.Draw(img)
        uniform_font_size = get_smallest_font_size_for_choices(
            ans_draw, choices, base_size=56, max_w=single_answer_width, min_size=20, step=2
        )
        uniform_font = load_font(uniform_font_size, bold=False)

        # Add answer text on top of the choices bubbles with uniform font size
        for i, ans in enumerate(choices):
            # Remove number prefix if exists
            clean_ans = ans.split(". ", 1)[-1] if ". " in ans else ans

            # Calculate text dimensions using uniform font
            text_bbox = ans_draw.textbbox((0, 0), clean_ans, font=uniform_font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            # Always center in remaining space after ABCD (consistent behavior)
            # This ensures all text is positioned uniformly regardless of length
            text_x = left_text_x + (single_answer_width - text_width) // 2
            
            # Safety check: ensure text doesn't overlap with ABCD
            min_x_after_abcd = circle_center_x + circle_radius + 10
            if text_x < min_x_after_abcd:
                text_x = min_x_after_abcd
            
            # Center text vertically in its bubble
            text_y_center = choices_y + int(i * choice_spacing + choice_spacing / 2)
            text_y = text_y_center - text_height // 2 - text_bbox[1] - 5

            # Draw the answer text
            draw.text((text_x, text_y), clean_ans, font=uniform_font, fill=BLACK)
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
                color = primary_color
            else:
                color = BLACK

            draw.text((text_x, text_y), text, font=ans_font, fill=color)

    # --- ZEP QUIZ logo at bottom ---
    logo_y = 1560
    if os.path.exists(theme_assets["logo"]):
        try:
            logo = Image.open(theme_assets["logo"]).convert("RGBA")
            logo_width = 342
            aspect = logo.height / logo.width
            logo = logo.resize((logo_width, int(logo_width * aspect)))
            logo_x = (W - logo_width) // 2
            img.paste(logo, (logo_x, logo_y), logo)
        except Exception:
            logo_font = load_font(70, bold=True)
            logo_text = "ZEP QUIZ"
            bbox = draw.textbbox((0, 0), logo_text, font=logo_font)
            logo_x = (W - (bbox[2] - bbox[0])) // 2
            draw.text((logo_x, logo_y), logo_text, font=logo_font, fill=primary_color)
    else:
        logo_font = load_font(70, bold=True)
        logo_text = "ZEP QUIZ"
        bbox = draw.textbbox((0, 0), logo_text, font=logo_font)
        logo_x = (W - (bbox[2] - bbox[0])) // 2
        draw.text((logo_x, logo_y), logo_text, font=logo_font, fill=primary_color)

    return img.convert("RGB")


# ----------------------
# 비디오 생성
# ----------------------
def make_video(quiz_data, theme=None, output_path=None):
    """카운트다운 애니메이션과 오디오가 포함된 퀴즈 비디오 생성"""
    global OUTPUT

    if output_path is None:
        output_path = OUTPUT
    else:
        OUTPUT = output_path  # 기존 main()에서 쓰더라도 깨지지 않게 유지

    data = json.loads(quiz_data) if isinstance(quiz_data, str) else quiz_data
    question = data["question"]
    choices = data["options"]
    answer = data["answer"]
    category = data.get("category", "General").capitalize()

    # Randomly select theme if not provided
    if theme is None:
        theme = random.choice(AVAILABLE_THEMES)
    
    print(f"🎨 Using theme: {theme}")
    
    # Get theme-specific assets
    theme_assets = get_theme_assets(theme)

    # Validate soft word-limits and warn if exceeded
    validate_word_limits(question, choices, q_limit=10, a_limit=5)

    # Find answer index from the answer text
    answer_idx = choices.index(answer) if answer in choices else 0

    # 비디오 프레임 - 카운트다운 단계
    clips = []
    for sec in range(COUNTDOWN_SECONDS):
        frame = render_frame(question, choices, category,
                             progress=sec + 1, reveal=False, answer_idx=answer_idx,
                             theme_assets=theme_assets, theme=theme)
        clips.append(ImageClip(np.array(frame)).set_duration(1))

    # 정답 공개 프레임
    ans_frame = render_frame(question, choices, category,
                             progress=5, reveal=True, answer_idx=answer_idx,
                             theme_assets=theme_assets, theme=theme)
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

    final.write_videofile(output_path, fps=FPS, codec="libx264", audio_codec="aac")
    print(f"✅ 비디오 생성 완료: {output_path}")
    return output_path


# --- MAIN ---
def load_quizzes_from_file(path):
    """Load and sanity-check quizzes from a JSON file (expects list of quiz objects)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Quizzes JSON must be a list of quiz objects.")
    # Basic schema validation (soft)
    for i, q in enumerate(data):
        if not all(k in q for k in ("category", "question", "options", "answer")):
            raise ValueError(f"Quiz index {i} is missing required keys.")
        if not isinstance(q["options"], list) or len(q["options"]) < 2:
            raise ValueError(f"Quiz index {i} must have an 'options' list with at least 2 items.")
    return data


def main():
    # dummy_quizzes.json 대신에 generate된 json 파일 path 
    INPUT_JSON = os.path.join(BASE_DIR, "dummy_quizzes.json")
    INPUT_JSON = os.path.normpath(INPUT_JSON)
    NUM_QUIZZES_TO_GENERATE = 2     # set how many to output
    global OUTPUT

    if not os.path.exists(INPUT_JSON):
        print(f"❌ ERROR: {INPUT_JSON} not found. Please add the quizzes.json file.")
        return

    quizzes = load_quizzes_from_file(INPUT_JSON)

    # limit to number requested
    quizzes = quizzes[:NUM_QUIZZES_TO_GENERATE]

    for i, quiz in enumerate(quizzes):
        OUTPUT = f"quiz_video_{i+1}.mp4"
        print(f"\n🎬 Generating video {i+1}/{len(quizzes)} → {OUTPUT}")
        try:
            make_video(quiz)  # Random theme will be selected inside
        except Exception as e:
            print(f"❌ Failed to create video for quiz index {i}: {e}")

    print("\n✨ All processing complete.")


if __name__ == "__main__":
    main()