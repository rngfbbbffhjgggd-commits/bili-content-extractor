#!/usr/bin/env python3
"""summarize.py — 用 DeepSeek API 总结 B站字幕（支持时间节点分段详述）

用法:
  python summarize.py 字幕.txt             (纯文本，无时间线)
  python summarize.py 字幕.srt             (带时间轴，输出时间线分段)
  python summarize.py 字幕.txt --min-sec 90 (每段至少90秒，控制分段粒度)

输出: 同名 _摘要.md
环境变量或同目录 deepseek_key.txt: DEEPSEEK_API_KEY
"""
import argparse
import json
import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

PROMPT = """你是一个专业的视频内容提炼助手。下面是某个B站视频的字幕，每行格式为 [时间] 字幕内容（时间格式 分:秒 或 时:分:秒）。

请输出一份**详细**的中文总结 Markdown，包含以下四个部分：

## 一句话总结
用 1-2 句话概括整个视频的核心内容。

## 内容时间线
按**内容逻辑分段**（场景切换、话题切换即为新段落，不要按固定时长机械切分），用表格列出每一段：
| 时间段 | 段落主题 | 内容要点 |
要求：段落要细，宁可多分几段；"内容要点"写 2-4 句有信息量的话，包含具体细节、数字、人名、结论；时间段必须与字幕时间对应。

## 核心要点
分点列出全片最重要的信息、分析、结论（合并同类，提炼干货）。

## 金句 / 结论
列出原文中最值得记录的原句（或高度概括的结论句）。

要求：忠实于原文，不得编造字幕中没有的内容；时间节点必须准确对应字幕。"""


def get_key():
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key and os.path.exists(os.path.join(HERE, "deepseek_key.txt")):
        key = open(os.path.join(HERE, "deepseek_key.txt"), encoding="utf-8").read().strip()
    return key


def fmt_time(sec):
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def parse_srt(path):
    """Parse srt -> list of (start_sec, text)"""
    lines = []
    cur = None
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            m = re.match(r"(\d{1,2}):(\d{2}):(\d{2}),\d{3}\s*-->", ln)
            if m:
                cur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
                continue
            if ln and cur is not None and not ln.isdigit():
                lines.append((cur, ln))
                cur = None
    return lines


def build_input(path, min_sec=0):
    if path.lower().endswith(".srt"):
        segs = parse_srt(path)
        if not segs:
            raise SystemExit("srt 解析为空")
        if min_sec > 0:
            merged = []
            for t, txt in segs:
                if merged and t - merged[-1][0] < min_sec:
                    merged[-1][1] += txt
                else:
                    merged.append([t, txt])
            segs = [(t, txt) for t, txt in merged]
        return "\n".join(f"[{fmt_time(t)}] {txt}" for t, txt in segs)
    return "\n".join(f"[{fmt_time(i*3)}] {ln}" for i, ln in enumerate(
        [l for l in open(path, encoding="utf-8").read().splitlines() if l.strip()]
    ))


def call_deepseek(text, key):
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,
    }).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        resp = json.load(r)
    return resp["choices"][0]["message"]["content"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="字幕 .txt 或 .srt 文件")
    ap.add_argument("--min-sec", type=int, default=0, help="srt 分段合并的最小秒数（控制粒度）")
    ap.add_argument("--output", default="", help="输出 md 路径")
    args = ap.parse_args()

    key = get_key()
    if not key:
        raise SystemExit("未找到 DeepSeek API key: 设置 DEEPSEEK_API_KEY 或写入 deepseek_key.txt")

    text = build_input(args.input, args.min_sec)
    print(f"输入 {len(text)} 字符 ({args.input})")

    parts = []
    if len(text) > 20000:
        chunk = 16000
        pieces = [text[i:i + chunk] for i in range(0, len(text), chunk)]
        for i, pc in enumerate(pieces, 1):
            print(f"分段 {i}/{len(pieces)} ...")
            parts.append(call_deepseek(pc, key))
    else:
        parts.append(call_deepseek(text, key))

    result = "\n\n---\n\n".join(parts)
    out = args.output or args.input.rsplit(".", 1)[0] + "_摘要.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write(result)
    print(result)
    print(f"\n已保存 -> {out}")


if __name__ == "__main__":
    main()
