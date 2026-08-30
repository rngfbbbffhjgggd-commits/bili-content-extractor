# 📺 Bili Content Extractor

One-click extraction of content from **Bilibili & YouTube** videos: **subtitles first, local transcription as fallback, free AI summary** — all local, no token cost.

**[中文文档](README.md)**

![Workflow](docs/flow.svg)

```
Bilibili / YouTube video URL
   │
   ├─ Has subtitles ──→ Download subtitles directly (Bilibili AI subs / YouTube Transcript API)
   │
   └─ No subtitles ──→ Auto language detection + local transcription
                       ├─ Chinese → SenseVoice (RTF<0.1, 10× faster) or Qwen3-ASR (more accurate)
                       └─ English → Parakeet-TDT-0.6B (word-level timestamps, RTF 0.16)
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
- **Ultra-fast Chinese**: SenseVoice (RTF<0.1, **10× faster than real-time**, a 10-min video ≈ 50s); optional Qwen3-ASR (22 Chinese dialects, higher accuracy)
- **English word-level timestamps**: Parakeet outputs per-word timestamps + confidence; more noise-robust than Whisper
- **Free summaries**: generates a self-contained prompt file for **DeepSeek web** — get a detailed timeline summary for free, no API token consumed
- **100% local**: transcription runs entirely on your machine, nothing uploaded
- **Disk friendly**: models ≈ 5GB, on any drive (default `D:\BiliModels`, configurable via env vars)

## 📦 Requirements

- Windows / Linux / macOS (parakeet.cpp needs a matching platform binary)
- Python 3.10+
- [ffmpeg](https://ffmpeg.org/)

## 🚀 Install

```bash
git clone https://github.com/rngfbbbffhjgggd-commits/bili-content-extractor.git
cd bili-content-extractor
pip install -r requirements.txt
```

## 🤖 Download Models (~5GB, into `D:\BiliModels` or your own directory)

### Chinese (default, ultra-fast): SenseVoice (int8 ONNX, 239MB)

Download `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2` from [k2-fsa/sherpa-onnx releases](https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models), extract to:
```
D:\BiliModels\sensevoice\
```
> ⚡ SenseVoice: RTF<0.1 — a 10-min Chinese video transcribes in ~50s.

### Chinese (optional, higher accuracy): Qwen3-ASR-1.7B (int4 ONNX, 3.9GB)

Download `qwen3-asr-1.7b-int4.tar.gz` from [andrewleech/qwen3-asr-1.7b-onnx](https://huggingface.co/andrewleech/qwen3-asr-1.7b-onnx) and extract to:
```
D:\BiliModels\qwen3-asr-1.7b\qwen3-asr-1.7b-int4\
```
> Use `--engine=qwen` to switch (22 Chinese dialects, more accurate but ~8× slower).

### English: Parakeet-TDT-0.6B (675MB)

1. Download the Windows CPU build `parakeet-v0.5.0-bin-win-cpu-x64.zip` from [parakeet.cpp releases](https://github.com/mudler/parakeet.cpp/releases), extract to:
```
D:\BiliModels\parakeet\parakeet-v0.5.0-bin-win-cpu-x64\
```
2. Download `tdt-0.6b-v3-q4_k.gguf` from [mudler/parakeet-cpp-gguf](https://huggingface.co/mudler/parakeet-cpp-gguf) into:
```
D:\BiliModels\parakeet\
```

> 💡 On unstable networks, use the bundled `parallel_download.py` for parallel chunked downloads (up to 300× faster):
> ```bash
> python parallel_download.py <url> <output_path> 16 2
> ```

## 🔑 Configure Bilibili Cookie (one-time, Bilibili only)

Bilibili's AI subtitle list **requires a logged-in session**:

1. Log in to bilibili.com and open any video page
2. F12 → Network → Reload → click any `api.bilibili.com` request
3. Copy the full `Cookie:` value from Request Headers
4. Save it as `cookie.txt` (single line, next to the scripts)

> 🔒 The cookie stays local and is only used to call Bilibili's API. It expires in about a month — just re-copy it then.

> 💡 **YouTube needs no cookie**: free Transcript API for subtitles, yt-dlp for audio — no login required.

## 🎯 Usage

**Windows one-click**: double-click `B站一键提取.bat` → paste a link → Enter.

**CLI**: 
```bash
python bili_quick.py "https://www.bilibili.com/video/BVxxxx"          # Bilibili
python bili_quick.py "https://www.youtube.com/watch?v=xxxx"           # YouTube
python bili_quick.py <url> --lang=zh                                 # force Chinese
python bili_quick.py <url> --lang=en                                 # force English
python bili_quick.py <url> --engine=qwen                            # Chinese via Qwen3-ASR (more accurate, 8× slower)
python bili_quick.py <url> --api                                     # optional: auto-summarize via DeepSeek API (costs tokens)
```

**Outputs** (in `BilibiliContent/<BV-id-or-yt-id>/`):
- With subtitles: `P1_ai-zh.txt` / `.srt` or `youtube_subtitle.txt`
- Without subtitles: `transcript.txt` + `prompt file.md`
- The prompt file contains full instructions — paste it into [chat.deepseek.com](https://chat.deepseek.com) for a detailed timeline summary

## 🧩 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `BILI_MODELS_ROOT` | `D:\BiliModels` | models root directory |
| `QWEN_ASR_DIR` | `<MODELS_ROOT>\qwen3-asr-1.7b\...` | Qwen3-ASR model dir |
| `SENSEVOICE_DIR` | `<MODELS_ROOT>\sensevoice\...` | SenseVoice model dir |
| `PARAKET_EXE` | `<MODELS_ROOT>\parakeet\...\parakeet-cli.exe` | parakeet executable |
| `PARAKET_GGUF` | `<MODELS_ROOT>\parakeet\tdt-0.6b-v3-q4_k.gguf` | parakeet model |
| `BILI_COOKIE_FILE` | `./cookie.txt` | cookie file path (Bilibili only) |
| `BILI_DEEPSEEK_KEY_FILE` | `./deepseek_key.txt` | DeepSeek key file (only for `--api`) |

## ⚖️ Disclaimer

- For personal learning and research only; subtitle/audio content belongs to the original creators and platforms
- Respect [Bilibili Terms of Service](https://www.bilibili.com/blackboard/activity-9pg6xIqxDZ.html) and video copyright
- Not for commercial use or large-scale scraping
- Not affiliated with Bilibili or YouTube

## 📄 License

MIT
