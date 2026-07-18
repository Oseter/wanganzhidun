"""生成安装包所需的图像资源（纯代码绘制，不依赖外部图片）。

产出：
    resources/icon.ico            —— 程序/安装包图标（盾牌，多尺寸）
    installer/wizard.bmp          —— 安装向导大图（164x314）
    installer/wizard-small.bmp    —— 安装向导右上小图（55x58）

配色取自「存护命途」防御蓝，与 ui/icons.py 的盾牌一致。
用法：python tools/gen_installer_art.py
"""
import os
from PIL import Image, ImageDraw

WIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def shield(size: int, bg=(33, 120, 200, 255),
           edge=(255, 255, 255, 130), fg=(255, 255, 255, 255)) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 100.0
    pts = [
        (50 * s, 8 * s), (88 * s, 22 * s), (88 * s, 55 * s),
        (50 * s, 92 * s), (12 * s, 55 * s), (12 * s, 22 * s),
    ]
    d.polygon(pts, fill=bg)
    d.line(pts + [pts[0]], fill=edge, width=max(2, int(3 * s)), joint="curve")
    lw = max(3, int(8 * s))
    d.line([(34 * s, 50 * s), (45 * s, 64 * s), (70 * s, 33 * s)],
           fill=fg, width=lw, joint="curve")
    return img


def make_ico():
    out_dir = os.path.join(WIN, "resources")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "icon.ico")
    shield(256).save(
        out,
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print("wrote", out)


def make_wizard():
    out_dir = os.path.join(WIN, "installer")
    os.makedirs(out_dir, exist_ok=True)

    # 大图：深蓝底 + 盾牌
    w, h = 164, 314
    base = Image.new("RGBA", (w, h), (15, 31, 49, 255))
    sh = shield(120).resize((120, 120))
    base.alpha_composite(sh, (int((w - 120) / 2), 40))
    base.convert("RGB").save(os.path.join(out_dir, "wizard.bmp"))

    # 小图：右上角盾牌
    w2, h2 = 55, 58
    base2 = Image.new("RGBA", (w2, h2), (15, 31, 49, 255))
    sh2 = shield(46).resize((46, 46))
    base2.alpha_composite(sh2, (int((w2 - 46) / 2), 6))
    base2.convert("RGB").save(os.path.join(out_dir, "wizard-small.bmp"))
    print("wrote wizard bmps")


if __name__ == "__main__":
    make_ico()
    make_wizard()
