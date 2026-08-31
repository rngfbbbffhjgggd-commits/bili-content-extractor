# 📺 Bili Content Extractor

One-click extraction of content from **Bilibili & YouTube** videos: **subtitles first, local transcription as fallback, free AI summary** — all local, no token cost.

**[中文文档](README.md)**

![Workflow](docs/flow.svg)

```
Bilibili / YouTube video URL
   │
   ├─ Has subtitles ──→ Download subtitles directly (Bilibili AI subs / YouTube Transcript API)
   │
   └─ No subtitles ──→ SenseVoice content language detection + local transcription
                       ├─ <10min (any language) → Qwen3-ASR-1.7B (most accurate)
                       ├─ ≥10min zh           → Qwen3-ASR-0.6B (faster tier)
                       ├─ ≥10min en/ja/yue    → Fun-ASR-Nano fp16 (faster tier)
                       └─ manual               → SenseVoice (ultra-fast, no punctuation)
                             │
                             ▼
                Generates a "prompt file.md" (instructions + timestamped transcript)
                             │
                             ▼
        Paste into DeepSeek web → free detailed timeline summary (no token usage)
```

## ✨ Features

- **Multi-platform**: **Bilibili** (AI subtitles first) + **YouTube** (free Transcript API subtitles, auto-transcribe when missing)
- **Subtitles first**: videos with subtitles are downloaded directly — zero cost, zero delay
- **Unified dual-tier**: <10min (any language) uses Qwen3-ASR-1.7B (most accurate, 52 languages); ≥10min uses Qwen3-ASR-0.6B for Chinese and Fun-ASR-Nano for en/ja/yue (~2× faster, punctuation included)
- **English engine Fun-ASR-Nano-2512**: fast tier for long en/ja/yue videos (punctuation + hotwords + code-switching); short videos stay on 1.7B since its accuracy is higher
- **Full punctuation**: every transcription engine outputs properly punctuated sentences (SenseVoice is used for language detection only) — better transcripts for LLM summarization
- **Free summaries**: generates a self-contained prompt file for **DeepSeek web** — get a detailed timeline summary for free, no API token consumed
- **100% local**: transcription runs entirely on your machine, nothing uploaded
- **Disk friendly**: models ≈ 8GB, on any drive (default `D:\BiliModels`, configurable via env vars)

## 📦 Requirements

- Windows / Linux / macOS (sherpa-onnx / onnxruntime cross-platform)
- Python 3.10+
- [ffmpeg](https://ffmpeg.org/)

## 🚀 Install

```bash
git clone https://github.com/rngfbbbffhjgggd-commits/bili-content-extractor.git
cd bili-content-extractor
pip install -r requirements.txt
```

## 🤖 Download Models (~8GB, into `D:\BiliModels` or your own directory)

### Chinese (default, most accurate): Qwen3-ASR-1.7B (int4 ONNX, 3.9GB)

Download `qwen3-asr-1.7b-int4.tar.gz` from [andrewleech/qwen3-asr-1.7b-onnx](https://huggingface.co/andrewleech/qwen3-asr-1.7b-onnx) and extract to:
```
D:\BiliModels\qwen3-asr-1.7b\qwen3-asr-1.7b-int4\
```
> Used automatically for videos <10 min (any language, most accurate, 52 languages).

### Chinese (long-video faster tier): Qwen3-ASR-0.6B (int4 ONNX, ~2GB)

One-command download (hf-mirror mirror + parallel chunks, resumable):
```bash
python download_qwen06b.py
```
Lands in `D:\BiliModels\qwen3-asr-0.6b\qwen3-asr-0.6b-int4\`.
> Used automatically for Chinese videos ≥10 min (~2× faster than 1.7B, same engine).

### English/Japanese/Cantonese (long-video fast tier): Fun-ASR-Nano-2512 (fp16 ONNX, ~2GB)

One-command download (hf-mirror mirror + parallel chunks, resumable):
```bash
python download_funasr_nano.py
```
Lands in `D:\BiliModels\funasr-nano\` (official sherpa-onnx export; zh/en/ja + 7 Chinese dialects + 26 accents, built-in punctuation/ITN).
> ⚠️ Must use the **fp16** LLM weights — the int8 export has a repetition-loop bug (sherpa-onnx issue [#3062](https://github.com/k2-fsa/sherpa-onnx/issues/3062)).
> Used automatically for en/ja/yue videos ≥10 min (punctuation + hotwords + code-switching; 1.7B is more accurate so short videos stay on 1.7B).

### Language detection: SenseVoice (int8 ONNX, 239MB)

Download `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2` from [k2-fsa/sherpa-onnx releases](https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models), extract to:
```
D:\BiliModels\sensevoice\
```
> Used only for the 40-second content-language scan (`result.lang`), not for transcription.

> 💡 On unstable networks, use the bundled `parallel_download.py` for parallel chunked downloads (up to 300× faster):
> ```bash
> python parallel_download.py <url> <output_path> 16 2
> ```

## 🔑 Configure Bilibili Cookie (one-time)

Bilibili's AI subtitle list **requires a logged-in session**:

1. Log in to bilibili.com and open any video page
2. F12 → Network → Reload → click any `api.bilibili.com` request
3. Copy the full `Cookie:` value from Request Headers
4. Save it as `cookie.txt` (single line, next to the scripts)

> 🔒 The cookie stays local and is only used to call Bilibili's API. It expires in about a month — just re-copy it then.

## 🎯 Usage

**Windows one-click**: double-click `B站一键提取.bat` → paste a link → Enter.

**CLI**:
```bash
python bili_quick.py "https://www.bilibili.com/video/BVxxxx"          # Bilibili
python bili_quick.py "https://www.youtube.com/watch?v=xxxx"           # YouTube
python bili_quick.py <url> --lang=zh                                 # force Chinese
python bili_quick.py <url> --lang=en                                 # force English
python bili_quick.py <url> --engine=qwen                            # force Qwen3-ASR-1.7B (most accurate)
python bili_quick.py <url> --engine=qwen06                          # force Qwen3-ASR-0.6B (long-video tier)
python bili_quick.py <url> --engine=funasr                          # force Fun-ASR-Nano (en/ja/yue)
python bili_quick.py <url> --engine=sensevoice                      # SenseVoice (ultra-fast, no punctuation)
python bili_quick.py <url> --api                                     # optional: auto-summarize via DeepSeek API (costs tokens)
```

**Outputs** (in `BilibiliContent/<BV-id>/`):
- With subtitles: `P1_ai-zh.txt` / `.srt`
- Without subtitles: `transcript.txt` + `prompt file.md`
- The prompt file contains full instructions — paste it into [chat.deepseek.com](https://chat.deepseek.com) for a detailed timeline summary

## 🧩 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `BILI_MODELS_ROOT` | `D:\BiliModels` | models root directory |
| `QWEN_ASR_DIR` | `<MODELS_ROOT>\qwen3-asr-1.7b\...` | Qwen3-ASR-1.7B model dir |
| `QWEN06_ASR_DIR` | `<MODELS_ROOT>\qwen3-asr-0.6b\...` | Qwen3-ASR-0.6B model dir |
| `FUNASR_DIR` | `<MODELS_ROOT>\funasr-nano` | Fun-ASR-Nano model dir |
| `BILI_COOKIE_FILE` | `./cookie.txt` | cookie file path |
| `BILI_DEEPSEEK_KEY_FILE` | `./deepseek_key.txt` | DeepSeek key file (only for `--api`) |

## ⚖️ Disclaimer

- For personal learning and research only; subtitle/audio content belongs to the original creators and Bilibili
- Respect [Bilibili Terms of Service](https://www.bilibili.com/blackboard/activity-9pg6xIqxDZ.html) and video copyright
- Not for commercial use or large-scale scraping
- Not affiliated with Bilibili

## 📄 License

MIT
