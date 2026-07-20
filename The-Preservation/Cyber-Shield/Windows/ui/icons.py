"""图标绘制（UI 改进版）：盾牌 logo（PIL Image），用于系统托盘与窗口标题栏。

相对旧版改进：
    - 增加顶部高光 + 内描边，视觉更立体；
    - 提供 active / inactive 两态：暂停监听时托盘图标变灰，状态一眼可见；
    - 纯代码绘制，不依赖任何外部图片资源（打包后也不会丢失图标）。

配色取自「存护命途」防御蓝：盾面 #2178C8，对勾白。
"""
from PIL import Image, ImageDraw

# 盾面蓝（运行中）/ 灰（暂停）
BLUE = (33, 120, 200, 255)
BLUE_HI = (90, 160, 230, 255)   # 高光
GRAY = (149, 165, 166, 255)
GRAY_HI = (190, 200, 201, 255)
EDGE = (255, 255, 255, 140)
FG = (255, 255, 255, 255)


def shield_image(size: int = 64, active: bool = True):
    """返回一个 RGBA 盾牌图标（含对勾）。size: 输出边长（像素）。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 100.0

    base = BLUE if active else GRAY
    hi = BLUE_HI if active else GRAY_HI

    # 盾形多边形（上宽下尖）
    pts = [
        (50 * s, 8 * s),
        (88 * s, 22 * s),
        (88 * s, 55 * s),
        (50 * s, 92 * s),
        (12 * s, 55 * s),
        (12 * s, 22 * s),
    ]
    d.polygon(pts, fill=base)
    # 顶部高光（上半部椭圆，半透明叠加，模拟立体）
    d.ellipse([(18 * s, 10 * s), (82 * s, 60 * s)], fill=hi)
    # 重新压一层盾形，让高光只落在盾内上半（先画高光再盖边）
    d.polygon(pts, fill=base)
    d.ellipse([(20 * s, 12 * s), (80 * s, 52 * s)], fill=hi)
    # 内描边
    d.line(pts + [pts[0]], fill=EDGE, width=max(2, int(3 * s)), joint="curve")

    # 对勾（确认 / 防御成功意象）
    lw = max(3, int(8 * s))
    d.line(
        [(34 * s, 50 * s), (45 * s, 64 * s), (70 * s, 33 * s)],
        fill=FG, width=lw, joint="curve",
    )
    return img


def tray_icon(size: int = 64, active: bool = True):
    """系统托盘用的盾牌图标。active=False 时返回灰色（暂停态）。"""
    return shield_image(size, active=active)


def window_logo(size: int = 40):
    """窗口标题栏用的小盾牌。"""
    return shield_image(size, active=True)
