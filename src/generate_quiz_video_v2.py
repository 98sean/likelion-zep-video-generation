import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip, vfx

# ======================
# Paths & constants
# ======================
ASSETS_ROOT = "../assets"

def resolve_asset(*candidates):
    """
    Try several relative paths under ../assets and ../assets/v2_design.
    Returns the first existing absolute path or None.
    """
    search_roots = [ASSETS_ROOT, os.path.join(ASSETS_ROOT, "v2_design")]
    for rel in candidates:
        for root in search_roots:
            p = os.path.join(root, rel)
            if os.path.exists(p):
                return p
    return None

# Fonts
FONT_PATH = resolve_asset("fonts/Nunito-Bold.ttf") or "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Design assets (resolve flexibly)
ZEP_CIRCLE_PATH   = resolve_asset("ZEP_circle.png")           # prefer v2_design if present
ZEP_QUIZ_LOGO_PATH= resolve_asset("ZEPQUIZ-logo.png")
PURPLE_BG_PATH    = resolve_asset("purple_quiz_bg.png")       # optional

# Audio (optional)
BGM_PATH          = resolve_asset("background.mp3")
SFX_CORRECT_PATH  = resolve_asset("correct.wav")

# Canvas / video
W, H = 1080, 1920
FPS = 30
COUNTDOWN_SECONDS = 5
ANSWER_HOLD = 2
OUTPUT = "quiz_video_v3.mp4"

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PURPLE = (91, 77, 219)
GRAD_TOP = (217, 198, 255)
GRAD_BOT = (237, 223, 255)
ANSWER_BG = (244, 246, 250)
SELECTED_BG = (205, 247, 255)   # highlight on reveal
SELECTED_TXT = (79, 70, 229)
DOT = (205, 210, 220)
ACTIVE = (107, 90, 255)

# ======================
# Font loader
# ======================
def load_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()

TITLE_FONT  = load_font(64)
OPTION_FONT = load_font(44)

# ======================
# Helpers
# ======================
_once_flags = {}

def log_once(key, msg):
    if not _once_flags.get(key):
        print(msg)
        _once_flags[key] = True

def draw_gradient(draw, w, h, top_rgb, bot_rgb):
    for y in range(h):
        t = y / h
        r = int(top_rgb[0]*(1-t) + bot_rgb[0]*t)
        g = int(top_rgb[1]*(1-t) + bot_rgb[1]*t)
        b = int(top_rgb[2]*(1-t) + bot_rgb[2]*t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

def text_bbox(font, text):
    bbox = font.getbbox(text)
    return (bbox[2]-bbox[0], bbox[3]-bbox[1])

def wrap_text(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def draw_timer_dots(draw, current_step, total_steps=5):
    dot_y = H - 400
    spacing = 100
    total_width = (total_steps - 1) * spacing
    start_x = (W - total_width) // 2
    for i in range(total_steps):
        x = start_x + i * spacing
        if i == current_step - 1:
            draw.ellipse([x-16, dot_y-16, x+16, dot_y+16], outline=ACTIVE, width=6, fill=WHITE)
        else:
            draw.ellipse([x-10, dot_y-10, x+10, dot_y+10], fill=DOT)

def draw_option(draw, rect, text, selected=False):
    (x1, y1, x2, y2) = rect
    bg = SELECTED_BG if selected else ANSWER_BG
    fg = SELECTED_TXT if selected else (75, 85, 99)
    draw.rounded_rectangle(rect, radius=20, fill=bg)
    w, h = text_bbox(OPTION_FONT, text)
    draw.text((x1+(x2-x1-w)//2, y1+(y2-y1-h)//2), text, font=OPTION_FONT, fill=fg)

# ======================
# Frame render
# ======================
def render_frame(question, choices, progress, reveal, answer_idx):
    # Background
    if PURPLE_BG_PATH:
        img = Image.open(PURPLE_BG_PATH).convert("RGB").resize((W, H))
        draw = ImageDraw.Draw(img)
    else:
        img = Image.new("RGB", (W, H), GRAD_TOP)
        draw = ImageDraw.Draw(img)
        draw_gradient(draw, W, H, GRAD_TOP, GRAD_BOT)

    # Card with soft shadow
    card = (90, 240, W-90, H-360)
    shadow = Image.new("RGBA", (W, H), (0,0,0,0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([card[0], card[1]+18, card[2], card[3]+18], radius=42, fill=(0,0,0,80))
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    img = Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(card, radius=42, fill=WHITE)

    # Top badge: ZEP_circle.png
    if ZEP_CIRCLE_PATH:
        try:
            badge = Image.open(ZEP_CIRCLE_PATH).convert("RGBA")
            bw = 150
            bh = int(bw * badge.height / badge.width)
            badge = badge.resize((bw, bh), Image.LANCZOS)
            bx = (W - bw) // 2
            by = card[1] - bw // 2  # half overlap
            img.paste(badge, (bx, by), badge)
            log_once("badge", f"Using ZEP circle: {ZEP_CIRCLE_PATH}")
        except Exception as e:
            log_once("badge_err", f"⚠️  Failed to load ZEP_circle.png ({ZEP_CIRCLE_PATH}): {e}")
    else:
        log_once("badge_missing", "⚠️  ZEP_circle.png not found under assets/ or assets/v2_design/")

    # Question
    y = card[1] + 180
    q_lines = wrap_text(draw, question, TITLE_FONT, (card[2]-card[0]) - 160)
    for line in q_lines:
        w, h = text_bbox(TITLE_FONT, line)
        draw.text((W//2 - w//2, y), line, font=TITLE_FONT, fill=BLACK)
        y += h + 16

    # Options
    left, right = card[0] + 60, card[2] - 60
    base_y = y + 60
    pill_h, gap = 120, 140
    for i, opt in enumerate(choices):
        clean = opt.split(". ", 1)[-1] if ". " in opt else opt
        top = base_y + i * gap
        rect = (left, top, right, top + pill_h)
        draw_option(draw, rect, clean, selected=(reveal and i == answer_idx))

    # Timer dots
    draw_timer_dots(draw, progress, total_steps=5)

    # Footer logo
    if ZEP_QUIZ_LOGO_PATH:
        try:
            logo = Image.open(ZEP_QUIZ_LOGO_PATH).convert("RGBA")
            lw = 360
            lh = int(lw * logo.height / logo.width)
            logo = logo.resize((lw, lh), Image.LANCZOS)
            lx = (W - lw) // 2
            ly = card[3] + 56
            img.paste(logo, (lx, ly), logo)
            log_once("logo", f"Using logo: {ZEP_QUIZ_LOGO_PATH}")
        except Exception as e:
            log_once("logo_err", f"⚠️  Failed to load logo ({ZEP_QUIZ_LOGO_PATH}): {e}")
    else:
        log_once("logo_missing", "⚠️  ZEPQUIZ-logo.png not found under assets/ or assets/v2_design/")

    return img

# ======================
# Video generation
# ======================
def make_video(quiz_data):
    data = json.loads(quiz_data) if isinstance(quiz_data, str) else quiz_data
    question = data["question"]
    choices  = data["options"]
    answer   = data["answer"]
    answer_idx = choices.index(answer) if answer in choices else 0

    clips = []
    for sec in range(COUNTDOWN_SECONDS):
        frame = render_frame(question, choices, progress=sec+1, reveal=False, answer_idx=answer_idx)
        clips.append(ImageClip(np.array(frame)).set_duration(1))

    ans_frame = render_frame(question, choices, progress=5, reveal=True, answer_idx=answer_idx)
    clips.append(ImageClip(np.array(ans_frame)).set_duration(ANSWER_HOLD))

    final = concatenate_videoclips(clips, method="compose")

    # Audio (optional)
    bgm = None
    if BGM_PATH:
        try:
            bgm = AudioFileClip(BGM_PATH).volumex(0.35)
            if bgm.duration < final.duration:
                bgm = bgm.fx(vfx.loop, duration=final.duration)
            else:
                bgm = bgm.subclip(0, final.duration)
            log_once("bgm", f"Using BGM: {BGM_PATH}")
        except Exception as e:
            log_once("bgm_err", f"⚠️  Failed to load BGM ({BGM_PATH}): {e}")

    sfx_clip = None
    if SFX_CORRECT_PATH:
        try:
            sfx = AudioFileClip(SFX_CORRECT_PATH).volumex(1.0)
            answer_start = final.duration - ANSWER_HOLD
            sfx_clip = sfx.set_start(answer_start)
            log_once("sfx", f"Using SFX: {SFX_CORRECT_PATH}")
        except Exception as e:
            log_once("sfx_err", f"⚠️  Failed to load SFX ({SFX_CORRECT_PATH}): {e}")

    if bgm and sfx_clip:
        final_audio = CompositeAudioClip([bgm, sfx_clip])
        final = final.set_audio(final_audio)
    elif bgm:
        final = final.set_audio(bgm)
    elif sfx_clip:
        final = final.set_audio(sfx_clip)

    final.write_videofile(OUTPUT, fps=30, codec="libx264", audio_codec="aac")
    print(f"✅ Video generated: {OUTPUT}")

# ======================
# Main
# ======================
def main():
    quiz_json_str = """
    {
      "category": "sports",
      "question": "Which country won the FIFA World Cup in 2022?",
      "options": ["France", "Argentina", "Brazil", "Croatia"],
      "answer": "Argentina"
    }
    """
    make_video(quiz_json_str)

if __name__ == "__main__":
    main()
