#!/usr/bin/env python3
"""bili_text.py — B站视频内容提取工具（AI字幕优先）

用法:
  python bili_text.py <BV号或视频URL> [--all] [-o 输出目录] [--cookie 文件路径]

流程:
  1. 读取 cookie（默认 ./cookie.txt；缺失则提示）
  2. view API -> 视频信息 + 分P列表
  3. player/wbi/v2 API -> AI字幕列表（需登录 cookie）
  4. 下载字幕 JSON -> 输出 .srt + .txt
  5. 无字幕 -> 提示音频转写兜底方案

仅用 Python 标准库。cookie 仅存本地，只用于调用 B站接口。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

MIXIN = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]

_KEYS = None


def get(url, params=None, cookie=None, referer="https://www.bilibili.com/"):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    headers = {"User-Agent": UA, "Referer": referer}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def wbi_keys(cookie):
    global _KEYS
    if _KEYS is None:
        nav = get("https://api.bilibili.com/x/web-interface/nav", cookie=cookie)
        img = nav["data"]["wbi_img"]["img_url"].rsplit("/", 1)[1].split(".")[0]
        sub = nav["data"]["wbi_img"]["sub_url"].rsplit("/", 1)[1].split(".")[0]
        _KEYS = (img, sub)
    return _KEYS


def sign(params, cookie):
    img_key, sub_key = wbi_keys(cookie)
    mixin = "".join((img_key + sub_key)[i] for i in MIXIN)[:32]
    params["wts"] = int(time.time())
    params = dict(sorted(params.items()))
    params["w_rid"] = hashlib.md5(
        urllib.parse.urlencode(params).encode() + mixin.encode()
    ).hexdigest()
    return params


def parse_bv(text):
    m = re.search(r"(BV[0-9A-Za-z]{10})", text)
    if m:
        return m.group(1)
    raise SystemExit("无法从输入中解析 BV 号")


def get_subtitles(bv, cid, cookie):
    p = get("https://api.bilibili.com/x/player/wbi/v2", sign({"bvid": bv, "cid": cid}, cookie), cookie)
    return (p.get("data") or {}).get("subtitle", {}).get("subtitles", [])


def pick_subtitle(subs):
    for pref in ("ai-zh", "zh-CN", "zh-Hans", "zh"):
        for s in subs:
            if s["lan"] == pref:
                return s
    return subs[0] if subs else None


def fmt_srt(lines):
    out = []
    for i, l in enumerate(lines, 1):
        def ts(x):
            h, rem = divmod(int(x), 3600)
            m, s = divmod(rem, 60)
            return f"{h:02d}:{m:02d}:{s:02d},000"
        out.append(f"{i}\n{ts(l['from'])} --> {ts(l['to'])}\n{l['content']}\n")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="B站视频内容提取（AI字幕优先）")
    ap.add_argument("input", help="BV号或视频URL")
    ap.add_argument("--all", action="store_true", help="下载全部分P（默认第一个有字幕的分P）")
    ap.add_argument("-o", "--output", default=".", help="输出目录（默认当前目录）")
    ap.add_argument("--cookie", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookie.txt"),
                    help="cookie 文件路径")
    args = ap.parse_args()

    if not os.path.exists(args.cookie):
        raise SystemExit(f"未找到 cookie 文件: {args.cookie}\n请先登录 B 站，把浏览器请求头里的 Cookie 粘贴保存为 cookie.txt（一行）")
    cookie = open(args.cookie, encoding="utf-8").read().strip()

    bv = parse_bv(args.input)
    view = get("https://api.bilibili.com/x/web-interface/view", {"bvid": bv}, cookie)
    if view["code"] != 0:
        raise SystemExit("view API 失败: " + view.get("message", ""))
    data = view["data"]
    print(f"标题: {data['title']}  |  分区: {data.get('tname', '')}  |  时长: {data['duration']}s")
    print(f"UP主: {data['owner']['name']}  |  分P数: {len(data['pages'])}")

    pages = data["pages"]
    if len(pages) == 1:
        targets = pages
    elif args.all:
        targets = pages
        print("将下载全部分P的字幕")
    else:
        print("\n分P列表（默认取第一个有字幕的）:")
        for p in pages:
            print(f"  P{p['page']} [{p['cid']}] {p['part']}")
        targets = pages

    os.makedirs(args.output, exist_ok=True)
    got_any = False
    for p in targets:
        subs = get_subtitles(bv, p["cid"], cookie)
        s = pick_subtitle(subs)
        if not s:
            print(f"\n[P{p['page']}] {p['part']}  ->  无 AI 字幕（{p['duration']}s）")
            continue
        got_any = True
        url = "https:" + s["subtitle_url"]
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.bilibili.com/video/"})
        with urllib.request.urlopen(req, timeout=30) as r:
            sub_data = json.load(r)
        body = sub_data.get("body", [])
        base = os.path.join(args.output, f"{bv}_P{p['page']}_{s['lan']}")
        with open(base + ".srt", "w", encoding="utf-8") as f:
            f.write(fmt_srt(body))
        with open(base + ".txt", "w", encoding="utf-8") as f:
            f.write("\n".join(l["content"] for l in body))
        print(f"\n[P{p['page']}] {p['part']}  字幕({s['lan_doc']}) {len(body)} 条")
        print(f"  -> {base}.srt")
        print(f"  -> {base}.txt")

    if not got_any:
        print("\n该视频没有 AI 字幕。兜底方案（音频转写）:")
        print("  1) 用 bili_quick.py 自动转写（中文 Qwen3-ASR / 英文 Parakeet）")
        print('  2) 下载音频后转写: yt-dlp -x --audio-format mp3 "%s"' % args.input)


if __name__ == "__main__":
    main()
