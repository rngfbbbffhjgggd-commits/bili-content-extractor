#!/usr/bin/env python3
"""make_icon.py — 生成「B站一键提取」的桌面图标

设计：B站粉圆角底 + 白色屏幕（内嵌播放键，代表视频）+ 三条横线（转写出的文本）
      + 右下角下载角标（代表提取）。一眼看出「把视频变成文字」。

用法:
    python make_icon.py            # 需要 Pillow

输出（都在本脚本所在目录）:
    bili_tool.ico           多尺寸图标（16/24/32/48/64/128/256），给快捷方式用
    bili_tool_preview.png   256x256 预览
    bili_tool_sizes.png     小尺寸可读性检查图（16/32/48/64 放大）

换设计时改下面的常量即可（配色、圆角、元素位置）。
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ICO_PATH = os.path.join(HERE, "bili_tool.ico")
PREVIEW_PATH = os.path.join(HERE, "bili_tool_preview.png")
SIZES_PATH = os.path.join(HERE, "bili_tool_sizes.png")

BI_PINK = (251, 114, 153, 255)        # B站粉
BI_PINK_DEEP = (233, 86, 128, 255)    # 渐变末端
WHITE = (255, 255, 255, 255)
WHITE_SOFT = (255, 255, 255, 232)

SS = 4          # 超采样倍率（先画大图再缩小，边缘更干净）
BASE = 256      # 基础边长
S = BASE * SS


def sc(*vals):
    return [v * SS for v in vals]


def render():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # 背景：圆角方块 + 纵向渐变
    bg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bg)
    for y in range(S):
        t = y / (S - 1)
        color = tuple(
            int(BI_PINK[i] + (BI_PINK_DEEP[i] - BI_PINK[i]) * t) for i in range(3)
        ) + (255,)
        bd.line([(0, y), (S, y)], fill=color)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle(sc(10, 10, 246, 246), radius=54 * SS, fill=255)
    img.paste(bg, (0, 0), mask)

    d = ImageDraw.Draw(img)
    # 白色屏幕 + 粉色播放三角（视频）
    d.rounded_rectangle(sc(46, 48, 210, 128), radius=16 * SS, fill=WHITE)
    d.polygon([(118 * SS, 70 * SS), (118 * SS, 106 * SS), (150 * SS, 88 * SS)], fill=BI_PINK)
    # 三条横线（文本），宽度递减
    for y, w in ((148, 148), (176, 108), (204, 68)):
        d.rounded_rectangle(sc(54, y, 54 + w, y + 15), radius=7 * SS, fill=WHITE_SOFT)
    # 右下角：下载角标（提取）
    d.ellipse(sc(176, 176, 232, 232), fill=WHITE)
    d.polygon([(204 * SS, 218 * SS), (188 * SS, 196 * SS), (220 * SS, 196 * SS)], fill=BI_PINK_DEEP)
    d.rectangle(sc(199, 188, 209, 200), fill=BI_PINK_DEEP)

    return img.resize((BASE, BASE), Image.LANCZOS)


def main():
    final = render()
    final.save(PREVIEW_PATH)
    final.save(ICO_PATH, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    # 小尺寸可读性检查图（放大 3 倍便于肉眼判断）
    icon = Image.open(ICO_PATH)
    canvas = Image.new("RGBA", (16 + 32 + 48 + 64 + 40, 80), (245, 245, 245, 255))
    x = 8
    for s in (16, 32, 48, 64):
        frame = icon.resize((s, s), Image.LANCZOS)
        canvas.paste(frame, (x, 40 - s // 2), frame)
        x += s + 10
    canvas.resize((canvas.width * 3, canvas.height * 3), Image.NEAREST).save(SIZES_PATH)

    print(f"[ok] {ICO_PATH} ({os.path.getsize(ICO_PATH)} bytes)")
    print(f"[ok] {PREVIEW_PATH}")
    print(f"[ok] {SIZES_PATH}")


if __name__ == "__main__":
    main()
