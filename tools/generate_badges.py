from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 512
CENTER = SIZE // 2
OUT_DIR = Path(__file__).resolve().parents[1] / "economy" / "badges" / "images" / "resized"

BADGE_SPECS = {
    "first_work": {"icon": "hammer", "code": "FW", "palette": ("#F8D66D", "#D6792A", "#3A1F12")},
    "streak_7": {"icon": "flame", "code": "7", "palette": ("#FFD06B", "#F0642E", "#4A1F18")},
    "shop_veteran": {"icon": "cart", "code": "SV", "palette": ("#9FD8FF", "#3D8ED8", "#152A49")},
    "certified": {"icon": "check", "code": "OK", "palette": ("#8BF4A2", "#28A86B", "#103826")},
    "streak_30": {"icon": "flame", "code": "30", "palette": ("#FFD189", "#E5542A", "#4E2118")},
    "wealth_1m": {"icon": "coins", "code": "1M", "palette": ("#FFE08A", "#D39A22", "#4A2D0C")},
    "master_thief": {"icon": "mask", "code": "MT", "palette": ("#D0B8FF", "#7A58D8", "#221845")},
    "shop_legend": {"icon": "crown_cart", "code": "SL", "palette": ("#FFD67A", "#CC7F1A", "#46280D")},
    "gift_giver": {"icon": "gift", "code": "GG", "palette": ("#FFC4E6", "#D0549A", "#4B1734")},
    "speed_runner": {"icon": "bolt", "code": "SR", "palette": ("#B8F8FF", "#24A9D1", "#103647")},
    "underdog": {"icon": "paw", "code": "UD", "palette": ("#FFE3A4", "#C07F2B", "#4A2D13")},
    "hoarder": {"icon": "chest", "code": "HO", "palette": ("#E0C2A0", "#9A5B2B", "#3A2214")},
    "raid_boss": {"icon": "skull", "code": "RB", "palette": ("#F3B8B8", "#B75252", "#3F1A1A")},
}


def _hex_to_rgba(value: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = value.strip().lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _load_font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "C:/Windows/Fonts/segoeuib.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
        )
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_cheese(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0, alpha: int = 220) -> None:
    w = int(46 * scale)
    h = int(34 * scale)
    fill = (255, 206, 88, alpha)
    outline = (227, 141, 44, alpha)
    draw.polygon(
        [(x, y + h), (x + int(0.18 * w), y + int(0.12 * h)), (x + w, y + int(0.03 * h)), (x + int(0.82 * w), y + h)],
        fill=fill,
        outline=outline,
    )
    hole = (246, 168, 70, alpha)
    draw.ellipse((x + int(0.25 * w), y + int(0.28 * h), x + int(0.40 * w), y + int(0.48 * h)), fill=hole)
    draw.ellipse((x + int(0.55 * w), y + int(0.36 * h), x + int(0.70 * w), y + int(0.54 * h)), fill=hole)


def _draw_background(image: Image.Image, key: str, palette: tuple[str, str, str]) -> ImageDraw.ImageDraw:
    draw = ImageDraw.Draw(image)
    p0 = _hex_to_rgba(palette[0])
    p1 = _hex_to_rgba(palette[1])
    p2 = _hex_to_rgba(palette[2])

    # Glow + rim
    for i in range(22):
        radius = 235 - i * 6
        alpha = max(0, 90 - i * 4)
        draw.ellipse((CENTER - radius, CENTER - radius, CENTER + radius, CENTER + radius), fill=(p1[0], p1[1], p1[2], alpha))

    for i in range(185, 0, -1):
        t = 1 - (i / 185.0)
        rgb = _mix((p2[0], p2[1], p2[2]), (p1[0], p1[1], p1[2]), t)
        draw.ellipse((CENTER - i, CENTER - i, CENTER + i, CENTER + i), fill=(rgb[0], rgb[1], rgb[2], 255))

    draw.ellipse((CENTER - 177, CENTER - 177, CENTER + 177, CENTER + 177), outline=(255, 246, 214, 220), width=5)
    draw.ellipse((CENTER - 145, CENTER - 145, CENTER + 145, CENTER + 145), fill=(24, 29, 44, 220))
    draw.ellipse((CENTER - 128, CENTER - 128, CENTER + 128, CENTER + 128), fill=(31, 39, 58, 240))

    # Decorative sparkle + cheese wedges
    rng = random.Random(key)
    for _ in range(18):
        angle = rng.random() * math.tau
        dist = rng.randint(165, 230)
        px = int(CENTER + math.cos(angle) * dist)
        py = int(CENTER + math.sin(angle) * dist)
        r = rng.randint(2, 5)
        draw.ellipse((px - r, py - r, px + r, py + r), fill=(255, 244, 220, 160))

    for angle_deg in (320, 35, 130):
        angle = math.radians(angle_deg)
        x = int(CENTER + math.cos(angle) * 172) - 20
        y = int(CENTER + math.sin(angle) * 172) - 15
        _draw_cheese(draw, x, y, scale=0.65, alpha=180)

    # Teeth around the rim
    teeth_fill = (255, 236, 186, 120)
    for i in range(18):
        a = (math.tau / 18) * i
        x1 = CENTER + int(math.cos(a) * 196)
        y1 = CENTER + int(math.sin(a) * 196)
        x2 = CENTER + int(math.cos(a + 0.06) * 214)
        y2 = CENTER + int(math.sin(a + 0.06) * 214)
        x3 = CENTER + int(math.cos(a - 0.06) * 214)
        y3 = CENTER + int(math.sin(a - 0.06) * 214)
        draw.polygon([(x1, y1), (x2, y2), (x3, y3)], fill=teeth_fill)

    return draw


def _draw_icon(draw: ImageDraw.ImageDraw, icon: str) -> None:
    ic = (255, 224, 138, 255)
    shadow = (18, 22, 34, 235)
    accent = (255, 167, 71, 255)

    if icon == "hammer":
        draw.rounded_rectangle((198, 215, 314, 258), radius=12, fill=ic, outline=shadow, width=4)
        draw.rounded_rectangle((248, 248, 276, 350), radius=10, fill=(229, 150, 84, 255), outline=shadow, width=4)
        draw.polygon([(208, 220), (186, 248), (198, 258), (218, 232)], fill=(255, 241, 204, 255))
    elif icon == "flame":
        draw.polygon([(256, 150), (324, 248), (292, 340), (256, 362), (220, 340), (188, 248)], fill=accent, outline=shadow)
        draw.polygon([(256, 186), (298, 252), (274, 312), (256, 326), (238, 312), (214, 252)], fill=(255, 229, 150, 255))
    elif icon == "cart":
        draw.rounded_rectangle((182, 224, 328, 280), radius=12, fill=ic, outline=shadow, width=4)
        draw.line((164, 206, 186, 238), fill=ic, width=10)
        draw.ellipse((198, 286, 234, 322), fill=(255, 188, 92, 255), outline=shadow, width=4)
        draw.ellipse((276, 286, 312, 322), fill=(255, 188, 92, 255), outline=shadow, width=4)
    elif icon == "check":
        draw.ellipse((182, 182, 330, 330), fill=(129, 242, 160, 255), outline=shadow, width=5)
        draw.line((216, 258, 246, 290), fill=(18, 74, 45, 255), width=16)
        draw.line((246, 290, 304, 226), fill=(18, 74, 45, 255), width=16)
    elif icon == "coins":
        for y in (292, 260, 228):
            draw.ellipse((190, y, 322, y + 44), fill=(255, 210, 104, 255), outline=shadow, width=4)
    elif icon == "mask":
        draw.ellipse((176, 198, 336, 314), fill=(211, 193, 255, 255), outline=shadow, width=4)
        draw.ellipse((210, 235, 250, 268), fill=shadow)
        draw.ellipse((262, 235, 302, 268), fill=shadow)
        draw.arc((202, 240, 312, 300), 20, 160, fill=shadow, width=5)
    elif icon == "crown_cart":
        _draw_icon(draw, "cart")
        draw.polygon([(192, 186), (222, 230), (256, 188), (290, 230), (320, 186), (320, 246), (192, 246)], fill=(255, 216, 106, 255), outline=shadow)
    elif icon == "gift":
        draw.rounded_rectangle((188, 220, 324, 328), radius=14, fill=(255, 170, 215, 255), outline=shadow, width=4)
        draw.rectangle((248, 220, 266, 328), fill=(255, 235, 245, 255))
        draw.rectangle((188, 262, 324, 280), fill=(255, 235, 245, 255))
        draw.ellipse((216, 180, 258, 226), outline=(255, 235, 245, 255), width=8)
        draw.ellipse((254, 180, 296, 226), outline=(255, 235, 245, 255), width=8)
    elif icon == "bolt":
        draw.polygon([(270, 154), (224, 256), (272, 256), (234, 360), (308, 240), (260, 240)], fill=(170, 244, 255, 255), outline=shadow)
        draw.line((184, 236, 220, 236), fill=(170, 244, 255, 200), width=8)
        draw.line((184, 268, 220, 268), fill=(170, 244, 255, 160), width=8)
    elif icon == "paw":
        draw.ellipse((222, 242, 292, 322), fill=(255, 217, 150, 255), outline=shadow, width=4)
        draw.ellipse((206, 198, 236, 236), fill=(255, 217, 150, 255), outline=shadow, width=4)
        draw.ellipse((240, 182, 272, 228), fill=(255, 217, 150, 255), outline=shadow, width=4)
        draw.ellipse((274, 198, 304, 236), fill=(255, 217, 150, 255), outline=shadow, width=4)
    elif icon == "chest":
        draw.rounded_rectangle((182, 234, 328, 334), radius=12, fill=(219, 157, 96, 255), outline=shadow, width=4)
        draw.rounded_rectangle((182, 198, 328, 254), radius=12, fill=(165, 96, 48, 255), outline=shadow, width=4)
        draw.rounded_rectangle((244, 252, 266, 294), radius=6, fill=(255, 216, 112, 255), outline=shadow, width=3)
    elif icon == "skull":
        draw.ellipse((188, 176, 324, 286), fill=(255, 221, 221, 255), outline=shadow, width=5)
        draw.rounded_rectangle((214, 270, 298, 338), radius=10, fill=(255, 221, 221, 255), outline=shadow, width=5)
        draw.ellipse((220, 218, 250, 248), fill=shadow)
        draw.ellipse((262, 218, 292, 248), fill=shadow)
        for x in (228, 246, 264, 282):
            draw.line((x, 286, x, 328), fill=shadow, width=4)


def _draw_badge(key: str, spec: dict) -> Image.Image:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = _draw_background(image, key, spec["palette"])

    _draw_icon(draw, spec["icon"])

    banner_color = _hex_to_rgba(spec["palette"][1], 240)
    draw.rounded_rectangle((120, 372, 392, 448), radius=18, fill=banner_color, outline=(255, 238, 194, 255), width=3)
    code_font = _load_font(56, bold=True)
    code = spec["code"]
    bbox = draw.textbbox((0, 0), code, font=code_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    tx = CENTER - text_w // 2
    ty = 410 - text_h // 2
    draw.text((tx + 2, ty + 2), code, font=code_font, fill=(25, 20, 20, 160))
    draw.text((tx, ty), code, font=code_font, fill=(255, 248, 230, 255))

    return image


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, spec in BADGE_SPECS.items():
        image = _draw_badge(key, spec)
        image.save(OUT_DIR / f"{key}.png", optimize=True)
        print(f"generated: {key}.png")


if __name__ == "__main__":
    main()
