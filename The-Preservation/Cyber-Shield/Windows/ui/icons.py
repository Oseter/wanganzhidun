from PIL import Image, ImageDraw

BLUE = (33, 120, 200, 255)
BLUE_HI = (90, 160, 230, 255)
GRAY = (149, 165, 166, 255)
GRAY_HI = (190, 200, 201, 255)
EDGE = (255, 255, 255, 140)
FG = (255, 255, 255, 255)


def shield_image(size: int = 64, active: bool = True):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 100.0
    base = BLUE if active else GRAY
    hi = BLUE_HI if active else GRAY_HI
    pts = [
        (50 * s, 8 * s), (88 * s, 22 * s), (88 * s, 55 * s),
        (50 * s, 92 * s), (12 * s, 55 * s), (12 * s, 22 * s),
    ]
    d.polygon(pts, fill=base)
    d.ellipse([(18 * s, 10 * s), (82 * s, 60 * s)], fill=hi)
    d.polygon(pts, fill=base)
    d.ellipse([(20 * s, 12 * s), (80 * s, 52 * s)], fill=hi)
    d.line(pts + [pts[0]], fill=EDGE, width=max(2, int(3 * s)), joint="curve")
    lw = max(3, int(8 * s))
    d.line([(34 * s, 50 * s), (45 * s, 64 * s), (70 * s, 33 * s)],
           fill=FG, width=lw, joint="curve")
    return img


def tray_icon(size: int = 64, active: bool = True):
    return shield_image(size, active=active)


def window_logo(size: int = 40):
    return shield_image(size, active=True)
