"""
Character Animation System — Flat Design Characters for YouTube Shorts
Draws simple but appealing characters frame-by-frame with Pillow.
Each script phrase maps to a visual scene with animated characters.
"""

import math
import random
import os
import logging
from typing import List, Tuple, Dict

from PIL import Image, ImageDraw, ImageFilter

log = logging.getLogger(__name__)

W, H = 1080, 1920

# Brand colors
C_BG      = (12, 10, 25)
C_CYAN    = (0, 212, 255)
C_PURPLE  = (123, 47, 187)
C_YELLOW  = (255, 220, 0)
C_RED     = (255, 70, 70)
C_GREEN   = (80, 220, 120)
C_WHITE   = (255, 255, 255)
C_SKIN    = (255, 200, 160)
C_DARK    = (30, 25, 50)
C_SHIRT   = (0, 160, 220)


# ══════════════════════════════════════════════════════════════════
#  CHARACTER DRAWING (Simple flat-design people)
# ══════════════════════════════════════════════════════════════════

def _draw_person(draw: ImageDraw, cx: int, cy: int, scale: float = 1.0,
                 shirt_color=C_SHIRT, facing='right', arm_pose='down',
                 expression='neutral', leg_pose='standing'):
    """Draw a simple flat-design person at (cx, cy) with given scale."""
    s = scale
    # Body colors
    skin = C_SKIN
    hair = (60, 40, 30)
    pants = (40, 40, 70)
    shoes = (30, 30, 30)

    # Head
    head_r = int(35 * s)
    head_cy = cy - int(120 * s)
    draw.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r],
                 fill=skin)
    # Hair
    hair_offset = int(5 * s) if facing == 'right' else -int(5 * s)
    draw.ellipse([cx - head_r + hair_offset, head_cy - head_r - int(5*s),
                  cx + head_r + hair_offset, head_cy - int(5*s)], fill=hair)
    # Eyes
    eye_y = head_cy - int(3 * s)
    if facing == 'right':
        eye_x = cx + int(8 * s)
    else:
        eye_x = cx - int(8 * s)
    eye_r = int(4 * s)
    draw.ellipse([eye_x - eye_r, eye_y - eye_r, eye_x + eye_r, eye_y + eye_r], fill=(255, 255, 255))
    pupil_r = int(2 * s)
    draw.ellipse([eye_x - pupil_r, eye_y - pupil_r, eye_x + pupil_r, eye_y + pupil_r], fill=(20, 20, 20))
    # Mouth
    mouth_y = head_cy + int(12 * s)
    mouth_w = int(10 * s)
    if expression == 'happy':
        draw.arc([cx - mouth_w, mouth_y - int(5*s), cx + mouth_w, mouth_y + int(10*s)],
                 0, 180, fill=(180, 60, 60), width=max(1, int(2*s)))
    elif expression == 'surprised':
        mouth_r = int(6 * s)
        draw.ellipse([cx - mouth_r, mouth_y - mouth_r, cx + mouth_r, mouth_y + mouth_r],
                     fill=(180, 60, 60))
    elif expression == 'thinking':
        # Flat mouth
        draw.line([cx - mouth_w, mouth_y, cx + mouth_w, mouth_y], fill=(150, 80, 60), width=max(1, int(2*s)))
    else:
        draw.line([cx - mouth_w, mouth_y, cx + mouth_w, mouth_y], fill=(150, 80, 60), width=max(1, int(2*s)))

    # Torso
    torso_top = cy - int(80 * s)
    torso_bot = cy + int(10 * s)
    torso_w = int(40 * s)
    draw.rounded_rectangle([cx - torso_w, torso_top, cx + torso_w, torso_bot],
                           radius=int(8*s), fill=shirt_color)

    # Arms
    arm_top = torso_top + int(10 * s)
    arm_len = int(60 * s)
    arm_w = int(8 * s)
    if arm_pose == 'down':
        draw.rounded_rectangle([cx - torso_w - arm_w, arm_top, cx - torso_w, arm_top + arm_len],
                               radius=int(4*s), fill=skin)
        draw.rounded_rectangle([cx + torso_w, arm_top, cx + torso_w + arm_w, arm_top + arm_len],
                               radius=int(4*s), fill=skin)
    elif arm_pose == 'up':
        draw.rounded_rectangle([cx - torso_w - arm_w, arm_top - arm_len, cx - torso_w, arm_top],
                               radius=int(4*s), fill=skin)
        draw.rounded_rectangle([cx + torso_w, arm_top - arm_len, cx + torso_w + arm_w, arm_top],
                               radius=int(4*s), fill=skin)
    elif arm_pose == 'pointing':
        draw.rounded_rectangle([cx - torso_w - arm_w, arm_top, cx - torso_w, arm_top + arm_len],
                               radius=int(4*s), fill=skin)
        # Pointing arm (right side, angled up)
        draw.rounded_rectangle([cx + torso_w, arm_top - int(20*s), cx + torso_w + arm_w + int(30*s), arm_top + int(10*s)],
                               radius=int(4*s), fill=skin)
    elif arm_pose == 'think':
        draw.rounded_rectangle([cx - torso_w - arm_w, arm_top, cx - torso_w, arm_top + arm_len],
                               radius=int(4*s), fill=skin)
        # Hand on chin
        draw.rounded_rectangle([cx + torso_w, arm_top - int(30*s), cx + torso_w + arm_w + int(15*s), arm_top + int(5*s)],
                               radius=int(4*s), fill=skin)

    # Legs
    leg_top = torso_bot
    leg_len = int(50 * s)
    leg_w = int(12 * s)
    leg_gap = int(15 * s)
    if leg_pose == 'walking':
        draw.rounded_rectangle([cx - leg_gap - leg_w, leg_top, cx - leg_gap, leg_top + leg_len],
                               radius=int(4*s), fill=pants)
        draw.rounded_rectangle([cx + leg_gap, leg_top + int(10*s), cx + leg_gap + leg_w, leg_top + leg_len + int(10*s)],
                               radius=int(4*s), fill=pants)
    else:
        draw.rounded_rectangle([cx - leg_gap - leg_w, leg_top, cx - leg_gap, leg_top + leg_len],
                               radius=int(4*s), fill=pants)
        draw.rounded_rectangle([cx + leg_gap, leg_top, cx + leg_gap + leg_w, leg_top + leg_len],
                               radius=int(4*s), fill=pants)

    # Shoes
    shoe_w = int(16 * s)
    shoe_h = int(8 * s)
    draw.rounded_rectangle([cx - leg_gap - shoe_w, leg_top + leg_len - shoe_h,
                            cx - leg_gap + leg_w, leg_top + leg_len + shoe_h],
                           radius=int(3*s), fill=shoes)
    draw.rounded_rectangle([cx + leg_gap - leg_w, leg_top + leg_len - shoe_h,
                            cx + leg_gap + shoe_w, leg_top + leg_len + shoe_h],
                           radius=int(3*s), fill=shoes)


def _draw_lightbulb(draw: ImageDraw, cx: int, cy: int, scale: float = 1.0, glow=False):
    """Draw a glowing lightbulb icon."""
    s = scale
    r = int(30 * s)
    # Bulb
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=C_YELLOW)
    if glow:
        for i in range(r + int(20*s), r, -2):
            alpha = int(40 * (1 - (i - r) / (20*s)))
            draw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=(255, 220, 0))
    # Base
    bw = int(12 * s)
    bh = int(15 * s)
    draw.rounded_rectangle([cx - bw, cy + r, cx + bw, cy + r + bh],
                           radius=int(3*s), fill=(180, 180, 180))
    # Rays
    ray_len = int(20 * s)
    for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
        rad = math.radians(angle)
        x1 = cx + int((r + 5*s) * math.cos(rad))
        y1 = cy + int((r + 5*s) * math.sin(rad))
        x2 = cx + int((r + ray_len) * math.cos(rad))
        y2 = cy + int((r + ray_len) * math.sin(rad))
        draw.line([x1, y1, x2, y2], fill=C_YELLOW, width=max(1, int(2*s)))


def _draw_question_marks(draw: ImageDraw, cx: int, cy: int, scale: float = 1.0, count=3):
    """Draw floating question marks."""
    s = scale
    font_size = int(40 * s)
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    for i in range(count):
        offset_x = int((i - count//2) * 50 * s)
        offset_y = int(math.sin(i * 1.5) * 20 * s)
        alpha = 200 - i * 40
        draw.text((cx + offset_x, cy + offset_y), "?", font=font, fill=(*C_PURPLE, alpha))


def _draw_brain(draw: ImageDraw, cx: int, cy: int, scale: float = 1.0):
    """Draw a simple brain icon."""
    s = scale
    r = int(35 * s)
    # Brain shape (two lobes)
    draw.ellipse([cx - r, cy - r, cx + int(5*s), cy + r], fill=(220, 150, 180))
    draw.ellipse([cx - int(5*s), cy - r, cx + r, cy + r], fill=(200, 130, 160))
    # Center line
    draw.line([cx, cy - r, cx, cy + r], fill=(180, 100, 130), width=max(1, int(2*s)))
    # Folds
    for i in range(3):
        fold_y = cy - r + int((i + 1) * r * 2 / 4)
        draw.arc([cx - r + int(5*s), fold_y - int(5*s), cx - int(5*s), fold_y + int(5*s)],
                 0, 180, fill=(180, 100, 130), width=max(1, int(1.5*s)))
        draw.arc([cx + int(5*s), fold_y - int(5*s), cx + r - int(5*s), fold_y + int(5*s)],
                 180, 360, fill=(180, 100, 130), width=max(1, int(1.5*s)))


def _draw_arrow_right(draw: ImageDraw, cx: int, cy: int, length: int, color=C_CYAN, width=3):
    """Draw a right-pointing arrow."""
    draw.line([cx, cy, cx + length, cy], fill=color, width=width)
    arrow_size = 15
    draw.polygon([
        (cx + length, cy),
        (cx + length - arrow_size, cy - arrow_size),
        (cx + length - arrow_size, cy + arrow_size)
    ], fill=color)


def _draw_magnifying_glass(draw: ImageDraw, cx: int, cy: int, scale: float = 1.0):
    """Draw a magnifying glass icon."""
    s = scale
    r = int(30 * s)
    # Glass
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=C_CYAN, width=max(2, int(3*s)))
    draw.ellipse([cx - r + int(5*s), cy - r + int(5*s), cx + r - int(5*s), cy + r - int(5*s)],
                 fill=(0, 0, 0, 50))
    # Handle
    handle_x = cx + int(r * 0.7)
    handle_y = cy + int(r * 0.7)
    draw.line([handle_x, handle_y, handle_x + int(25*s), handle_y + int(25*s)],
              fill=C_CYAN, width=max(2, int(4*s)))


def _draw_person_at_desk(draw: ImageDraw, cx: int, cy: int, scale: float = 1.0):
    """Draw a person sitting at a desk with laptop."""
    s = scale
    # Desk
    desk_w = int(120 * s)
    desk_h = int(10 * s)
    desk_y = cy + int(30 * s)
    draw.rounded_rectangle([cx - desk_w, desk_y, cx + desk_w, desk_y + desk_h],
                           radius=int(3*s), fill=(80, 60, 40))
    # Desk legs
    leg_w = int(6 * s)
    draw.rectangle([cx - desk_w + int(10*s), desk_y + desk_h, cx - desk_w + int(10*s) + leg_w, desk_y + int(70*s)],
                   fill=(60, 45, 30))
    draw.rectangle([cx + desk_w - int(10*s) - leg_w, desk_y + desk_h, cx + desk_w - int(10*s), desk_y + int(70*s)],
                   fill=(60, 45, 30))
    # Laptop
    lap_w = int(45 * s)
    lap_h = int(30 * s)
    lap_y = desk_y - lap_h
    draw.rounded_rectangle([cx - lap_w, lap_y, cx + lap_w, desk_y],
                           radius=int(3*s), fill=(50, 50, 60))
    # Screen
    scr_margin = int(3 * s)
    draw.rounded_rectangle([cx - lap_w + scr_margin, lap_y + scr_margin,
                            cx + lap_w - scr_margin, desk_y - int(3*s)],
                           radius=int(2*s), fill=(100, 180, 255))
    # Person (simplified, sitting)
    _draw_person(draw, cx, cy - int(30*s), scale=s * 0.8, arm_pose='down', expression='neutral')


def _draw_two_people_talking(draw: ImageDraw, cx: int, cy: int, scale: float = 1.0):
    """Draw two people facing each other (conversation)."""
    s = scale
    gap = int(80 * s)
    _draw_person(draw, cx - gap, cy, scale=s, facing='right', arm_pose='pointing',
                 expression='happy', shirt_color=C_SHIRT)
    _draw_person(draw, cx + gap, cy, scale=s, facing='left', arm_pose='think',
                 expression='thinking', shirt_color=C_PURPLE)
    # Speech lines
    for i in range(3):
        y_off = int((i - 1) * 15 * s)
        line_len = int(20 * s) + i * int(5*s)
        draw.line([cx - gap + int(40*s), cy - int(80*s) + y_off,
                   cx - gap + int(40*s) + line_len, cy - int(80*s) + y_off],
                  fill=C_CYAN, width=max(1, int(2*s)))


def _draw_explosion(draw: ImageDraw, cx: int, cy: int, scale: float = 1.0, color=C_YELLOW):
    """Draw a comic-style explosion/bang."""
    s = scale
    r = int(50 * s)
    points = []
    for i in range(12):
        angle = math.radians(i * 30)
        outer = r if i % 2 == 0 else int(r * 0.5)
        px = cx + int(outer * math.cos(angle))
        py = cy + int(outer * math.sin(angle))
        points.append((px, py))
    draw.polygon(points, fill=color)
    # Inner circle
    inner_r = int(r * 0.4)
    draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=C_WHITE)


def _draw_heart(draw: ImageDraw, cx: int, cy: int, scale: float = 1.0, color=C_RED):
    """Draw a heart shape."""
    s = scale
    r = int(20 * s)
    # Two circles for top of heart
    draw.ellipse([cx - r*2, cy - r, cx, cy + r], fill=color)
    draw.ellipse([cx, cy - r, cx + r*2, cy + r], fill=color)
    # Triangle for bottom
    draw.polygon([(cx - r*2, cy), (cx + r*2, cy), (cx, cy + r*2)], fill=color)


def _draw_checkmark(draw: ImageDraw, cx: int, cy: int, scale: float = 1.0, color=C_GREEN):
    """Draw a checkmark icon."""
    s = scale
    r = int(30 * s)
    # Circle background
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    # Checkmark
    points = [
        (cx - int(15*s), cy),
        (cx - int(3*s), cy + int(15*s)),
        (cx + int(20*s), cy - int(12*s))
    ]
    draw.line(points, fill=C_WHITE, width=max(2, int(4*s)))


def _draw_x_mark(draw: ImageDraw, cx: int, cy: int, scale: float = 1.0, color=C_RED):
    """Draw an X mark icon."""
    s = scale
    r = int(30 * s)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    sz = int(15 * s)
    draw.line([cx - sz, cy - sz, cx + sz, cy + sz], fill=C_WHITE, width=max(2, int(4*s)))
    draw.line([cx + sz, cy - sz, cx - sz, cy + sz], fill=C_WHITE, width=max(2, int(4*s)))


# ══════════════════════════════════════════════════════════════════
#  SCENE GENERATOR — Maps script phrases to visual scenes
# ══════════════════════════════════════════════════════════════════

# Keywords → visual scene type
SCENE_KEYWORDS = {
    'think':    'brain', 'mind': 'brain', 'psychology': 'brain', 'brain': 'brain',
    'know':     'magnifier', 'secret': 'magnifier', 'discover': 'magnifier', 'learn': 'magnifier',
    'talk':     'conversation', 'tell': 'conversation', 'say': 'conversation', 'speak': 'conversation',
    'love':     'heart', 'feel': 'heart', 'emotion': 'heart', 'attract': 'heart',
    'work':     'desk', 'office': 'desk', 'computer': 'desk', 'job': 'desk',
    'danger':   'explosion', 'risk': 'explosion', 'threat': 'explosion', 'crash': 'explosion',
    'yes':      'check', 'correct': 'check', 'right': 'check', 'true': 'check', 'good': 'check',
    'no':       'x_mark', 'wrong': 'x_mark', 'false': 'x_mark', 'bad': 'x_mark', 'never': 'x_mark',
    'idea':     'lightbulb', 'eureka': 'lightbulb', 'discover': 'lightbulb', 'realize': 'lightbulb',
}


def _classify_phrase(phrase: str) -> str:
    """Classify a phrase into a scene type based on keywords."""
    words = phrase.lower().split()
    for word in words:
        for keyword, scene_type in SCENE_KEYWORDS.items():
            if keyword in word:
                return scene_type
    # Default: alternate between person poses
    return random.choice(['person_think', 'person_happy', 'person_surprised'])


def split_into_scenes(script: str, n_scenes: int = None) -> List[Dict]:
    """Split script into scenes with visual types."""
    words = script.split()
    # Split into phrases (2-5 words each)
    phrases = []
    current = []
    for w in words:
        current.append(w)
        if len(current) >= random.randint(3, 5) or w.endswith(('.', '!', '?')):
            phrases.append(' '.join(current))
            current = []
    if current:
        phrases.append(' '.join(current))

    if n_scenes:
        # Merge/split to match n_scenes
        while len(phrases) > n_scenes:
            merged = []
            for i in range(0, len(phrases), 2):
                if i + 1 < len(phrases):
                    merged.append(phrases[i] + ' ' + phrases[i+1])
                else:
                    merged.append(phrases[i])
            phrases = merged

    scenes = []
    for phrase in phrases:
        scene_type = _classify_phrase(phrase)
        scenes.append({
            'text': phrase,
            'type': scene_type,
        })

    return scenes


# ══════════════════════════════════════════════════════════════════
#  SCENE RENDERER — Draw a scene at time t
# ══════════════════════════════════════════════════════════════════

def _draw_scene(img: Image.Image, scene_type: str, t: float, scene_duration: float):
    """Draw the visual content for a scene type at time t."""
    draw = ImageDraw.Draw(img)
    progress = t / scene_duration if scene_duration > 0 else 0

    # Animation: entrance effect (slide in from bottom)
    entrance = min(1.0, progress * 4)  # First 25% is entrance
    ease = 1 - (1 - entrance) ** 3  # Ease out cubic
    cy_offset = int((1 - ease) * 200)  # Slide up 200px

    cx = W // 2
    cy = H // 2 + cy_offset

    if scene_type == 'brain':
        _draw_brain(draw, cx, cy, scale=2.0)
        _draw_lightbulb(draw, cx + 100, cy - 100, scale=1.2, glow=True)
        _draw_person(draw, cx - 150, cy + 150, scale=1.2, expression='thinking', arm_pose='think')

    elif scene_type == 'lightbulb':
        _draw_lightbulb(draw, cx, cy - 80, scale=2.5, glow=True)
        _draw_person(draw, cx, cy + 150, scale=1.2, expression='surprised', arm_pose='up')

    elif scene_type == 'magnifier':
        _draw_magnifying_glass(draw, cx, cy - 60, scale=2.0)
        _draw_person(draw, cx, cy + 150, scale=1.0, expression='neutral')

    elif scene_type == 'conversation':
        _draw_two_people_talking(draw, cx, cy, scale=1.1)

    elif scene_type == 'heart':
        _draw_heart(draw, cx, cy - 60, scale=2.5)
        _draw_person(draw, cx, cy + 150, scale=1.0, expression='happy')

    elif scene_type == 'desk':
        _draw_person_at_desk(draw, cx, cy, scale=1.0)

    elif scene_type == 'explosion':
        _draw_explosion(draw, cx, cy - 60, scale=2.0)
        _draw_person(draw, cx, cy + 150, scale=0.9, expression='surprised')

    elif scene_type == 'check':
        _draw_checkmark(draw, cx, cy - 60, scale=2.5)
        _draw_person(draw, cx, cy + 150, scale=1.0, expression='happy', arm_pose='up')

    elif scene_type == 'x_mark':
        _draw_x_mark(draw, cx, cy - 60, scale=2.5)
        _draw_person(draw, cx, cy + 150, scale=1.0, expression='surprised')

    else:
        # Default: person with random pose
        poses = ['down', 'up', 'pointing', 'think']
        expressions = ['neutral', 'happy', 'surprised', 'thinking']
        _draw_person(draw, cx, cy, scale=1.5,
                     arm_pose=random.choice(poses),
                     expression=random.choice(expressions))


def render_scene_frame(scene: Dict, t: float, scene_duration: float) -> Image.Image:
    """Render a single frame for a scene."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _draw_scene(img, scene['type'], t, scene_duration)
    return img


# ══════════════════════════════════════════════════════════════════
#  FULL ANIMATION RENDERER — Compose all scenes into frames
# ══════════════════════════════════════════════════════════════════

def render_character_animation(script: str, audio_duration: float, fps: int = 15) -> List[Image.Image]:
    """
    Render all frames of the character animation.
    Returns a list of RGBA Image frames.
    """
    scenes = split_into_scenes(script)
    n_scenes = len(scenes)
    scene_duration = audio_duration / n_scenes

    total_frames = int(audio_duration * fps)
    frames = []

    log.info(f"Rendering {n_scenes} scenes ({total_frames} frames, {fps}fps)")

    for frame_idx in range(total_frames):
        t = frame_idx / fps
        # Determine which scene we're in
        scene_idx = min(int(t / scene_duration), n_scenes - 1)
        scene = scenes[scene_idx]
        local_t = t - scene_idx * scene_duration

        # Render scene frame
        frame = render_scene_frame(scene, local_t, scene_duration)
        frames.append(frame)

        if frame_idx % (fps * 3) == 0:
            log.info(f"  Characters: frame {frame_idx}/{total_frames} (scene {scene_idx+1}/{n_scenes})")

    return frames


# ══════════════════════════════════════════════════════════════════
#  TEST FUNCTION
# ══════════════════════════════════════════════════════════════════

def test_characters():
    """Test character rendering."""
    script = "99 percent of people have no idea how the dark psychology trick works. This simple technique can make anyone do what you want. The key is understanding one basic principle about human behavior."
    scenes = split_into_scenes(script)
    print(f"Script split into {len(scenes)} scenes:")
    for i, s in enumerate(scenes):
        print(f"  Scene {i+1}: [{s['type']}] {s['text'][:50]}...")

    # Render one frame from each scene
    os.makedirs("output/test_chars", exist_ok=True)
    for i, scene in enumerate(scenes):
        frame = render_scene_frame(scene, 1.0, 3.0)  # t=1s into a 3s scene
        frame.save(f"output/test_chars/scene_{i+1}_{scene['type']}.png")
        print(f"  Saved scene_{i+1}_{scene['type']}.png")

    print("Character test done!")


if __name__ == "__main__":
    test_characters()
