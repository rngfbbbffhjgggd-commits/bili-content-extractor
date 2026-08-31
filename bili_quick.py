#!/usr/bin/env python3
"""bili_quick.py — B站视频内容一键提取（SenseVoice 语言检测 + 三引擎转写）

用法:
  交互模式:   python bili_quick.py           (双击 bat 即可)
  直接模式:   python bili_quick.py <链接或BV号>
  指定语言:   python bili_quick.py <链接> --lang zh|en|auto (默认 auto)

流程:
  有字幕: 抓AI字幕 -> txt/srt
  无字幕: 下载音频 -> SenseVoice 内容语言检测 ->
          <10分钟（任意语言） → Qwen3-ASR-1.7B（最准）
          ≥10分钟: 中文 → Qwen3-ASR-0.6B（快档）/ 英日粤 → Fun-ASR-Nano fp16（快档）
  产物:    投喂文件.md (视频信息 + 指令 + 带时间戳全文) -> 拖进 DeepSeek 网页版即可总结
输出目录: tools/BilibiliContent/<BV号>/
模型目录: D:\\BiliModels\\ (Qwen3-ASR 1.7B + 0.6B + Fun-ASR-Nano fp16 + SenseVoice)
"""
import json
import os
import re
import subprocess
import sys
import webbrowser
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS_DIR)
import bili_text as bt  # noqa: E402

OUT_ROOT = os.path.join(TOOLS_DIR, "BilibiliContent")
KEY_FILE = os.environ.get("BILI_DEEPSEEK_KEY_FILE", os.path.join(TOOLS_DIR, "deepseek_key.txt"))
COOKIE_FILE = os.environ.get("BILI_COOKIE_FILE", os.path.join(TOOLS_DIR, "cookie.txt"))
# 模型根目录：默认 D:\BiliModels，可用环境变量 BILI_MODELS_ROOT 覆盖
MODELS_ROOT = os.environ.get("BILI_MODELS_ROOT", r"D:\BiliModels")
QWEN_DIR = os.environ.get("QWEN_ASR_DIR", os.path.join(MODELS_ROOT, "qwen3-asr-1.7b", "qwen3-asr-1.7b-int4"))
QWEN06_DIR = os.environ.get("QWEN06_ASR_DIR", os.path.join(MODELS_ROOT, "qwen3-asr-0.6b", "qwen3-asr-0.6b-int4"))
FUNASR_DIR = os.environ.get("FUNASR_DIR", os.path.join(MODELS_ROOT, "funasr-nano"))
API_URL = "https://api.deepseek.com/chat/completions"
UA = bt.UA

SUMMARY_PROMPT = """你是一个专业的视频内容提炼助手。下面是某个B站视频的字幕，每行格式为 [时间] 字幕内容（时间格式 分:秒）。

请输出一份**详细**的中文总结 Markdown，包含以下四个部分：

## 一句话总结
用 1-2 句话概括整个视频的核心内容。

## 内容时间线
按**内容逻辑分段**（场景切换、话题切换即为新段落），用表格列出每一段：
| 时间段 | 段落主题 | 内容要点 |
要求：段落要细，宁可多分几段；"内容要点"写 2-4 句有信息量的话，包含具体细节、数字、人名、结论；时间段必须与字幕时间对应。

## 核心要点
分点列出全片最重要的信息、分析、结论。

## 金句 / 结论
列出原文中最值得记录的原句或高度概括的结论句。

要求：忠实于原文，不得编造字幕中没有的内容；时间节点必须准确对应字幕。"""


def fmt_time(sec):
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# ---------- 投喂文件 ----------

def build_feed_file(bv, title, owner, duration, segments, outdir, engine_note=""):
    lines = "\n".join(f"[{fmt_time(t)}] {txt}" for t, txt in segments)
    md = f"""# 📄 B站视频内容投喂包 — 请直接发送给 DeepSeek 网页版

## 【给你的指令】
请作为视频内容提炼助手，根据下面的【字幕全文】，输出一份**详细**的中文总结 Markdown，包含四个部分：
1. 【一句话总结】用 1-2 句话概括核心内容。
2. 【内容时间线】按内容逻辑分段（场景切换/话题切换即新段落），用表格列出：| 时间段 | 段落主题 | 内容要点 |。段落要细，宁可多分几段；"内容要点"写 2-4 句有信息量的话（含细节、数字、人名、结论）；时间段必须与字幕时间对应。
3. 【核心要点】分点列出全片最重要的信息、分析、结论。
4. 【金句/结论】原文中最值得记录的原句。
要求：忠实于原文，不得编造字幕中没有的内容。

## 【视频信息】
- 标题：{title}
- UP主：{owner}
- 时长：{duration} 秒
- 链接：https://www.bilibili.com/video/{bv}
- 转写引擎：{engine_note or "B站AI字幕"}

## 【字幕全文】(每行 [分:秒] 内容)
{lines}
"""
    path = os.path.join(outdir, "投喂DeepSeek网页版.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path


# ---------- 可选：API 自动总结 ----------

def call_deepseek(text, key):
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SUMMARY_PROMPT},
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


def api_summarize(segments, outdir):
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key and os.path.exists(KEY_FILE):
        key = open(KEY_FILE, encoding="utf-8").read().strip()
    if not key:
        print("[!] 未配置 DeepSeek API key，跳过 API 总结（已生成投喂文件）")
        return
    text = "\n".join(f"[{fmt_time(t)}] {txt}" for t, txt in segments)
    if len(text) > 20000:
        chunks = [text[i:i + 16000] for i in range(0, len(text), 16000)]
        md = "\n\n---\n\n".join(call_deepseek(c, key) for c in chunks)
    else:
        md = call_deepseek(text, key)
    path = os.path.join(outdir, "总结.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[√] API 总结已保存 -> {path}")


# ---------- 音频下载 ----------

def download_audio(bv, cid, outpath):
    p = bt.get("https://api.bilibili.com/x/player/playurl",
               {"bvid": bv, "cid": cid, "fnval": 16})
    audios = p["data"]["dash"]["audio"]
    a = max(audios, key=lambda x: x.get("bandwidth", 0))
    url = a["baseUrl"]
    if not url.startswith("https"):
        url = (a.get("backupUrl") or [url])[0]
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.bilibili.com/"})
    with urllib.request.urlopen(req, timeout=300) as r:
        with open(outpath, "wb") as f:
            while True:
                c = r.read(65536)
                if not c:
                    break
                f.write(c)
    return outpath


# ---------- 中文转写：Qwen3-ASR（1.7B 最准 / 0.6B 长视频快档） ----------

def zh_transcribe(audio_path, outdir, engine="auto", duration=0):
    """转写调度：auto → <10分钟用 Qwen3-ASR-1.7B（最准），≥10分钟中文用 Qwen3-ASR-0.6B
    英日粤长视频由调用方传入 funasr；可强制指定 funasr / sensevoice / qwen / qwen06"""
    if engine == "auto":
        engine = "qwen06" if duration >= 600 else "qwen"
        print(f"[√] 自动选择引擎: {'Qwen3-ASR-0.6B (长视频,快档)' if engine == 'qwen06' else 'Qwen3-ASR-1.7B (短视频,最准)'}")
    if engine == "funasr":
        try:
            from funasr_nano_engine import transcribe_audio as fn_transcribe

            print("[√] 转写引擎: Fun-ASR-Nano-2512 (标点+热词)")
            return fn_transcribe(audio_path, outdir)
        except (ImportError, FileNotFoundError) as e:
            print(f"[!] funasr-nano 不可用 ({e})，回退 Qwen3-ASR-1.7B")
            engine = "qwen"
    if engine == "sensevoice":
        try:
            from sensevoice_engine import transcribe_audio as sv_transcribe

            print("[√] 中文转写引擎: SenseVoice (RTF<0.1, 快8倍, 无标点)")
            return sv_transcribe(audio_path, outdir)
        except ImportError:
            print("[!] sensevoice_engine 不可用，回退 Qwen3-ASR-1.7B")
        except FileNotFoundError as e:
            print(f"[!] {e}，回退 Qwen3-ASR-1.7B")
        engine = "qwen"
    if engine == "qwen06":
        print(f"[√] 加载 Qwen3-ASR-0.6B (长视频快档)...")
        return qwen_transcribe(audio_path, outdir, model_dir=QWEN06_DIR)
    return qwen_transcribe(audio_path, outdir)


# ---------- 中文转写：Qwen3-ASR ----------

def qwen_transcribe(audio_path, outdir, chunk_sec=30, model_dir=None):
    """Qwen3-ASR 分段转写 -> [(start_sec, text)]；model_dir 可切换 1.7B/0.6B

    chunk_sec=30 实测最快（60s 块 RTF≈0.48 -> 30s 块 RTF≈0.35，短上下文解码更便宜）。"""
    import numpy as np
    import wave

    from qwen_asr_engine import QwenASREngine, SAMPLE_RATE

    if model_dir is None:
        model_dir = QWEN_DIR
    if not os.path.exists(os.path.join(model_dir, "encoder.int4.onnx")):
        print("[!] Qwen3-ASR 模型缺失:", model_dir)
        return None

    # 读音频为 16k mono float32
    try:
        import soundfile as sf

        audio, sr = sf.read(audio_path, dtype="float32", always_2d=False)
    except Exception:
        with wave.open(audio_path, "rb") as w:
            sr = w.getframerate()
            audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != SAMPLE_RATE:
        n = int(len(audio) * SAMPLE_RATE / sr)
        audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio)
    audio = audio.astype(np.float32)

    eng = QwenASREngine(model_dir)

    total = len(audio) / SAMPLE_RATE
    segs = []
    chunk_len = chunk_sec * SAMPLE_RATE
    n_chunks = max(1, int(np.ceil(total / chunk_sec)))
    for i in range(n_chunks):
        start = i * chunk_sec
        part = audio[i * chunk_len:(i + 1) * chunk_len]
        if len(part) < SAMPLE_RATE * 0.5:
            continue
        tmp = os.path.join(outdir, f"_chunk_{i}.wav")
        with wave.open(tmp, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes((part * 32767).astype(np.int16).tobytes())
        print(f"  [块 {i+1}/{n_chunks} {fmt_time(start)}] ", end="", flush=True)
        text = eng.transcribe(tmp)
        os.remove(tmp)
        if text:
            segs.append((start, text))
    return segs


# ---------- 引擎分发（统一入口，用户拍板方案） ----------

def transcribe_with_engine(wav, outdir, lang, duration, engine):
    """引擎分发（统一双档方案）:
       <10分钟（任意语言） → Qwen3-ASR-1.7B（最准，52语言）
       ≥10分钟: 中文 → Qwen3-ASR-0.6B（中文快档）
                英/日/粤 → Fun-ASR-Nano fp16（快档，标点+热词）
       其他语言 → Qwen3-ASR-1.7B 兜底
       Parakeet 已移除（无标点）
    返回 (segments, engine_note)"""
    if engine == "parakeet":
        print("[!] Parakeet 已移除（输出无标点），改用自动方案")
        engine = "auto"
    engine = ask_engine(engine, duration)
    if engine == "auto":
        if duration < 600:
            engine = "qwen"
            print("[√] 自动选择引擎: Qwen3-ASR-1.7B (短视频,最准)")
        elif lang == "zh":
            engine = "qwen06"
            print("[√] 自动选择引擎: Qwen3-ASR-0.6B (中文长视频,快档)")
        else:
            engine = "funasr"
            print("[√] 自动选择引擎: Fun-ASR-Nano fp16 (英/日/粤长视频,快档)")
    segs = zh_transcribe(wav, outdir, engine, duration)
    note = {
        "funasr": "Fun-ASR-Nano-2512 (英日粤, 标点+热词)",
        "sensevoice": "SenseVoice (极速, 无标点)",
        "qwen": "Qwen3-ASR-1.7B (最准, 52语言)",
        "qwen06": "Qwen3-ASR-0.6B (中文长视频, 快档)",
    }.get(engine, "中文引擎")
    return segs, note


# ---------- 语言选择 ----------

def detect_lang(title, desc, manual):
    """检测语言：日文假名→ja，韩文谚文→ko，中文字符→zh，否则→en
    （日文优先：日文标题必含假名，且日文汉字与中文共用 CJK 区）"""
    if manual:
        return manual
    text = title + (desc or "")[:200]
    if re.search(r"[\u3040-\u30ff\u31f0-\u31ff]", text):  # 日文假名
        return "ja"
    if re.search(r"[\uac00-\ud7af]", text):  # 韩文谚文
        return "ko"
    if re.search(r"[\u4e00-\u9fff]", text):  # 中文字符
        return "zh"
    return "en"


LANG_NAMES = {"zh": "中文", "ja": "日语", "ko": "韩语", "yue": "粤语", "en": "英文"}


def decide_lang(title, desc, wav, lang_manual):
    """语言决策：SenseVoice 内容检测优先（比标题可靠），标题检测为 fallback"""
    if lang_manual:
        return lang_manual
    try:
        from sensevoice_engine import detect_content_lang

        clang = detect_content_lang(wav)
        if clang:
            print(f"[√] 内容语言检测: {LANG_NAMES.get(clang, clang)}")
            return clang
        print("[!] 内容检测未返回结果，回退标题判断")
    except Exception:
        pass
    return detect_lang(title, desc, None)


def ask_engine(engine, duration):
    """交互选择转写引擎。engine 已指定（非auto）则直接用；否则弹选项菜单。"""
    if engine and engine != "auto":
        return engine
    try:
        if not sys.stdin.isatty():
            return "auto"
    except Exception:
        return "auto"
    dur_min = duration / 60 if duration else 0
    print(f"\n请选择转写引擎（视频时长约 {dur_min:.0f} 分钟）:")
    print("  1) auto（推荐，直接回车）— <10分钟一律用 Qwen3-ASR-1.7B（最准）；≥10分钟 中文→0.6B，英日粤→Fun-ASR-Nano")
    print("  2) Qwen3-ASR-1.7B — 最准，多语言52种；较慢")
    print("  3) Qwen3-ASR-0.6B — 中文长视频快档（比1.7B快约2倍）")
    print("  4) SenseVoice — 极速无标点；仅对比用")
    print("  5) Fun-ASR-Nano — 英日粤长视频快档（标点+热词）")
    while True:
        try:
            c = input("输入数字或直接回车(默认1 auto): ").strip().lower()
        except EOFError:
            return "auto"
        if c in ("", "1", "auto"):
            return "auto"
        if c in ("2", "qwen", "qwen3", "qwen3-asr", "17b"):
            return "qwen"
        if c in ("3", "qwen06", "qwen06b", "0.6b", "06"):
            return "qwen06"
        if c in ("4", "sensevoice", "sv"):
            return "sensevoice"
        if c in ("5", "funasr", "fn", "nano"):
            return "funasr"
        print("无效输入，请输入 1-5 或直接回车")


# ---------- YouTube 支持 ----------

def parse_youtube_id(url):
    m = re.search(r"(?:youtu\.be/|watch\?v=|shorts/|embed/|live/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None


def youtube_meta(video_id):
    """oEmbed API 获取标题/作者（无需登录）"""
    try:
        u = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        req = urllib.request.Request(u, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
        return d.get("title", ""), d.get("author_name", "")
    except Exception:
        return video_id, "YouTube"


def youtube_subtitles(video_id):
    """youtube-transcript-api 获取字幕 -> [(start, text)]（字幕优先路径）"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return None, "缺少 youtube-transcript-api，请 pip install youtube-transcript-api"
    try:
        api = YouTubeTranscriptApi()
        for lang in (["zh-Hans", "zh-CN", "zh", "en"], None):
            try:
                if lang:
                    tr = api.fetch(video_id, languages=lang)
                else:
                    tr = api.fetch(video_id)
                segs = [(float(s.start), s.text.replace("\n", " ")) for s in tr]
                return segs, None
            except Exception:
                continue
        return None, "该视频没有可用字幕"
    except Exception as e:
        return None, f"字幕获取失败: {type(e).__name__}: {str(e)[:120]}"


def download_youtube_audio(video_id, outdir):
    """yt-dlp 下载最佳音频并转 16k mono wav"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    out = os.path.join(outdir, "yt_audio.%(ext)s")
    cmd = [sys.executable, "-m", "yt_dlp", "-x", "--audio-format", "wav",
           "--audio-quality", "0", "--postprocessor-args", "ffmpeg:-ar 16000 -ac 1",
           "-o", out, url]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=1800)
    if proc.returncode != 0:
        print("[x] yt-dlp 下载失败:", proc.stderr[-300:])
        return None
    wav = os.path.join(outdir, "yt_audio.wav")
    if os.path.exists(wav):
        return wav
    # 兜底：找实际生成的 wav
    import glob
    hits = glob.glob(os.path.join(outdir, "yt_audio*.wav"))
    return hits[0] if hits else None


def run_youtube(url, use_api=False, lang_manual=None, engine="auto"):
    video_id = parse_youtube_id(url)
    if not video_id:
        print("[x] 无法解析 YouTube 链接")
        return
    title, author = youtube_meta(video_id)
    print(f"[√] {title}  |  UP主: {author}")
    outdir = os.path.join(OUT_ROOT, f"yt-{video_id}")
    os.makedirs(outdir, exist_ok=True)

    # 1) 字幕优先（免费、无需下载）
    segs, err = youtube_subtitles(video_id)
    engine_note = "YouTube 字幕"
    if segs:
        print(f"[√] 字幕 {len(segs)} 条")
        txt_path = os.path.join(outdir, "youtube_subtitle.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(f"[{fmt_time(t)}] {x}" for t, x in segs))
    else:
        # 2) 无字幕 -> 音频转写
        print(f"\n[!] 无字幕（{err}），走音频转写兜底 ...")
        wav = download_youtube_audio(video_id, outdir)
        if not wav:
            print("[x] 音频下载失败")
            return
        print(f"[√] 音频已下载 {wav}")
        lang = decide_lang(title, "", wav, lang_manual)
        print(f"[√] 语言: {LANG_NAMES.get(lang, lang)}")
        import wave as _wave

        with _wave.open(wav) as _wf:
            dur = _wf.getnframes() / _wf.getframerate()
        segs, engine_note = transcribe_with_engine(wav, outdir, lang, dur, engine)
        if segs is None:
            return
        txt_path = os.path.join(outdir, "transcript.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(f"[{fmt_time(t)}] {x}" for t, x in segs))
        print(f"[√] 转写完成 {len(segs)} 段")

    # 生成投喂文件
    feed = build_feed_file(f"yt-{video_id}", title, author, 0, segs, outdir, engine_note)
    print(f"\n{'='*52}")
    print(f"  ✅ 已生成投喂文件:")
    print(f"     {feed}")
    print(f"{'='*52}")
    print("  下一步: 把该文件拖进 DeepSeek 网页版 (chat.deepseek.com)")

    if use_api:
        api_summarize(segs, outdir)
    try:
        webbrowser.open("https://chat.deepseek.com")
        os.startfile(outdir)
        print("\n[√] 已自动打开 DeepSeek 网页版和文件所在文件夹，把 md 拖进去即可")
    except (EOFError, KeyboardInterrupt, OSError):
        pass


# ---------- 平台分发 ----------

def run_any(url, use_api=False, lang_manual=None, engine="auto"):
    if "bilibili.com" in url or "b23.tv" in url or re.search(r"BV[0-9A-Za-z]{10}", url):
        run(url, use_api, lang_manual, engine)
    elif "youtube.com" in url or "youtu.be" in url:
        run_youtube(url, use_api, lang_manual, engine)
    else:
        print("[x] 不支持的平台（目前支持: B站 / YouTube）")


# ---------- 主流程 ----------

def run(url, use_api=False, lang_manual=None, engine="auto"):
    bv = bt.parse_bv(url)
    if not os.path.exists(COOKIE_FILE):
        print(f"[x] 缺少 cookie 文件 {COOKIE_FILE}")
        return
    cookie = open(COOKIE_FILE, encoding="utf-8").read().strip()

    view = bt.get("https://api.bilibili.com/x/web-interface/view", {"bvid": bv}, cookie)
    if view["code"] != 0:
        msg = str(view.get("message", ""))
        print(f"[x] view API 失败: {msg}")
        if "登录" in msg or "风控" in msg or "-101" in msg:
            print("[!] 可能是 cookie 过期：打开 bilibili.com 登录后重新复制 Cookie 到 cookie.txt")
        return
    data = view["data"]
    title, owner, duration = data["title"], data["owner"]["name"], data["duration"]
    print(f"[√] {title}  ({duration}s, {len(data['pages'])}P)")

    outdir = os.path.join(OUT_ROOT, bv)
    os.makedirs(outdir, exist_ok=True)

    segments = None
    engine_note = ""
    for p in data["pages"]:
        subs = bt.get_subtitles(bv, p["cid"], cookie)
        s = bt.pick_subtitle(subs)
        if not s:
            print(f"    P{p['page']} {p['part']}: 无AI字幕")
            continue
        url2 = "https:" + s["subtitle_url"]
        req = urllib.request.Request(url2, headers={"User-Agent": UA, "Referer": "https://www.bilibili.com/video/"})
        with urllib.request.urlopen(req, timeout=30) as r:
            sub_data = json.load(r)
        body = sub_data.get("body", [])
        base = os.path.join(outdir, f"P{p['page']}_{s['lan']}")
        with open(base + ".srt", "w", encoding="utf-8") as f:
            f.write(bt.fmt_srt(body))
        with open(base + ".txt", "w", encoding="utf-8") as f:
            f.write("\n".join(l["content"] for l in body))
        print(f"    P{p['page']}: 字幕 {len(body)} 条")
        segments = [(l["from"], l["content"]) for l in body]
        break

    if segments is None:
        # 区分「真没字幕」与「cookie 过期」：字幕接口非 0 返回码即过期/风控
        try:
            probe = bt.get("https://api.bilibili.com/x/player/wbi/v2",
                           bt.sign({"bvid": bv, "cid": data["pages"][0]["cid"]}, cookie), cookie)
            if probe.get("code") != 0:
                print(f"[!] 字幕接口返回 code={probe.get('code')}（{probe.get('message', '')}）—— 很可能是 cookie 过期：")
                print("    请打开 bilibili.com 登录后重新复制 Cookie 覆盖 cookie.txt，再试一次")
        except Exception:
            pass
        print("\n[!] 无AI字幕，走音频转写兜底 ...")
        audio = os.path.join(outdir, "audio.m4s")
        try:
            download_audio(bv, data["pages"][0]["cid"], audio)
            print(f"[√] 音频已下载 {audio}")
        except Exception as e:
            print(f"[x] 音频下载失败: {e}")
            return
        # 统一转 16k mono wav（m4s 需转码）
        wav = os.path.join(outdir, "audio_16k.wav")
        subprocess.run(["ffmpeg", "-y", "-i", audio, "-ar", "16000", "-ac", "1", wav],
                       capture_output=True, timeout=600)
        if not os.path.exists(wav):
            print("[x] ffmpeg 转码失败")
            return
        lang = decide_lang(title, data.get("desc", ""), wav, lang_manual)
        print(f"[√] 语言: {LANG_NAMES.get(lang, lang)}")
        segments, engine_note = transcribe_with_engine(wav, outdir, lang, data["duration"], engine)
        if segments is None:
            return
        txt_path = os.path.join(outdir, "transcript.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(f"[{fmt_time(t)}] {x}" for t, x in segments))
        print(f"[√] 转写完成 {len(segments)} 段")

    # 生成投喂文件（默认，不消耗 token）
    feed = build_feed_file(bv, title, owner, duration, segments, outdir, engine_note)
    print(f"\n{'='*52}")
    print(f"  ✅ 已生成投喂文件:")
    print(f"     {feed}")
    print(f"{'='*52}")
    print("  下一步: 把该文件拖进 DeepSeek 网页版 (chat.deepseek.com)")

    if use_api:
        api_summarize(segments, outdir)

    try:
        webbrowser.open("https://chat.deepseek.com")
        os.startfile(outdir)
        print("\n[√] 已自动打开 DeepSeek 网页版和文件所在文件夹，把 md 拖进去即可")
    except (EOFError, KeyboardInterrupt, OSError):
        pass


def show_banner():
    """启动横幅：顶部像素风彩条（ANSI 彩色，仅交互模式）"""
    try:
        tty = sys.stdin.isatty()
    except Exception:
        tty = False
    if not tty:
        print("=" * 52)
        print("  视频内容一键提取 -> 投喂文件 (免费总结)")
        print("  支持: B站 / YouTube | 内容语言检测 + 多引擎")
        print("=" * 52)
        return
    P = "\033[38;2;251;114;153m"   # B站粉
    B = "\033[38;2;137;180;250m"   # 蓝
    C = "\033[38;2;94;226;213m"    # 青
    Y = "\033[38;2;249;226;175m"   # 黄
    R = "\033[0m"
    strip = P + "█" * 13 + B + "█" * 13 + C + "█" * 13 + Y + "█" * 13 + R
    print(strip)
    print(P + "▓" + R + "  视频内容一键提取 → 投喂文件（免费总结）  " + P + "▓" + R)
    print(P + "▓" + R + "  B站 / YouTube | 内容语言检测 + 多引擎选择 " + P + "▓" + R)
    print(strip)


def main():
    args = sys.argv[1:]
    use_api = "--api" in args
    args = [a for a in args if a != "--api"]
    lang_manual = None
    for a in args:
        if a.startswith("--lang="):
            lang_manual = a.split("=", 1)[1]
    engine = "auto"
    for a in args:
        if a.startswith("--engine="):
            engine = a.split("=", 1)[1]
    args = [a for a in args if not a.startswith("--lang") and not a.startswith("--engine")]
    if args:
        run_any(args[0], use_api, lang_manual, engine)
        return
    show_banner()
    while True:
        url = input("\n粘贴 视频链接或BV号 (输入 q 退出): ").strip()
        if url.lower() in ("q", "quit", "exit"):
            break
        if not url:
            continue
        try:
            run_any(url, use_api, lang_manual, engine)
        except KeyboardInterrupt:
            break
        except SystemExit as e:
            print(f"[x] {e}")
        except Exception as e:
            print(f"[x] 出错: {type(e).__name__}: {e}")
    print("\n再见~")


if __name__ == "__main__":
    main()
