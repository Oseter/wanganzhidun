"""图标绘制：盾牌 logo（PIL Image），用于系统托盘与窗口标题栏。

纯代码绘制，不依赖任何外部图片资源（打包后也不会丢失图标）。
配色取自「存护命途」防御蓝：盾面 #2178C8，对勾白。
"""
from PIL import Image, ImageDraw


def shield_image(size: int = 64, bg=(33, 120, 200, 255),
                 edge=(255, 255, 255, 130), fg=(255, 255, 255, 255)):
    """返回一个 RGBA 盾牌图标（含对勾）。

    size: 输出边长（像素）。
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = size
    s = w / 100.0  # 缩放基准

    # 盾形多边形（上宽下尖）
    pts = [
        (50 * s, 8 * s),
        (88 * s, 22 * s),
        (88 * s, 55 * s),
        (50 * s, 92 * s),
        (12 * s, 55 * s),
        (12 * s, 22 * s),
    ]
    d.polygon(pts, fill=bg)
    # 内描边
    d.line(pts + [pts[0]], fill=edge, width=max(2, int(3 * s)), joint="curve")

    # 对勾（确认/防御成功意象）
    lw = max(3, int(8 * s))
    d.line(
        [(34 * s, 50 * s), (45 * s, 64 * s), (70 * s, 33 * s)],
        fill=fg, width=lw, joint="curve",
    )
    return img


def tray_icon(size: int = 64):
    """系统托盘用的盾牌图标。"""
    return shield_image(size)


def window_logo(size: int = 40):
    """窗口标题栏用的小盾牌。"""
    return shield_image(size)
