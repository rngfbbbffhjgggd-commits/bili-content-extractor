# 📺 Bili Content Extractor

One-click extraction of content from **Bilibili & YouTube** videos: **subtitles first, local transcription as fallback, free AI summary** — all local, no token cost.

**[中文文档](README.md)**

![Workflow](docs/flow.svg)

```
Bilibili / YouTube video URL
   │
   ├─ Has subtitles ──→ Download subtitles directly (Bilibili AI subs / YouTube Transcript API)
   │
   └─ No subtitles ──→ Content language detection + local transcription
                       ├─ zh/en/ja → Fun-ASR-Nano-2512 (main: fast+accurate+PUNCTUATION, 7 dialects/26 accents)
                       ├─ Korean etc → Qwen3-ASR-1.7B fallback (52 languages)
                       └─ manual     → SenseVoice (ultra-fast, no punctuation) / Parakeet (English word timestamps)
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
- **Main engine Fun-ASR-Nano-2512**: Tongyi's next-gen model (0.8B, sherpa-onnx fp16), zh/en/ja + 7 Chinese dialects + 26 accents, built-in **punctuation**/ITN/hotwords; ~4-6 min per 10-min video (quality-first, complete punctuation)
- **Punctuation matters**: unlike SenseVoice/Parakeet (which emit raw word streams), Fun-ASR-Nano outputs properly punctuated sentences — noticeably better transcripts for LLM summarization
- **Korean/other-language fallback**: auto-switches to Qwen3-ASR (52 languages) when needed
- **English word timestamps** (manual): Parakeet keeps per-word timestamps + confidence; more noise-robust than Whisper
- **Free summaries**: generates a self-contained prompt file for **DeepSeek web** — get a detailed timeline summary for free, no API token consumed
- **100% local**: transcription runs entirely on your machine, nothing uploaded
- **Disk friendly**: models ≈ 6GB, on any drive (default `D:\BiliModels`, configurable via env vars)

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

## 🤖 Download Models (~6GB, into `D:\BiliModels` or your own directory)

### Main (recommended): Fun-ASR-Nano-2512 (fp16 ONNX, ~2GB)

One-command download (hf-mirror mirror + parallel chunks, resumable):
```bash
python download_funasr_nano.py
```
Lands in `D:\BiliModels\funasr-nano\` (official sherpa-onnx export; zh/en/ja + 7 Chinese dialects + 26 accents, built-in punctuation/ITN).
> ⚠️ Must use the **fp16** LLM weights — the int8 export has a repetition-loop bug (sherpa-onnx issue [#3062](https://github.com/k2-fsa/sherpa-onnx/issues/3062)).

### Chinese (optional, fast): SenseVoice (int8 ONNX, 239MB)

Download `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2` from [k2-fsa/sherpa-onnx releases](https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models), extract to:
```
D:\BiliModels\sensevoice\
```
> ⚡ SenseVoice: RTF<0.1 — a 10-min Chinese video transcribes in ~50s; kept for language detection.

### Chinese (optional, fallback): Qwen3-ASR-1.7B (int4 ONNX, 3.9GB)

Download `qwen3-asr-1.7b-int4.tar.gz` from [andrewleech/qwen3-asr-1.7b-onnx](https://huggingface.co/andrewleech/qwen3-asr-1.7b-onnx) and extract to:
```
D:\BiliModels\qwen3-asr-1.7b\qwen3-asr-1.7b-int4\
```
> Auto-fallback for Korean/other languages (52 languages).

### English (optional, manual): Parakeet-TDT-0.6B (675MB)

1. Download the Windows CPU build `parakeet-v0.5.0-bin-win-cpu-x64.zip` from [parakeet.cpp releases](https://github.com/mudler/parakeet.cpp/releases), extract to:
```
D:\BiliModels\parakeet\parakeet-v0.5.0-bin-win-cpu-x64\
```
2. Download `tdt-0.6b-v3-q4_k.gguf` from [mudler/parakeet-cpp-gguf](https://huggingface.co/mudler/parakeet-cpp-gguf) into:
```
D:\BiliModels\parakeet\
```
> Optional — kept only as a manual option for word-level timestamps / verbatim transcripts (English, no punctuation).

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
python bili_quick.py <url> --engine=funasr                          # main: Fun-ASR-Nano (default)
python bili_quick.py <url> --engine=qwen                            # Qwen3-ASR (52-language fallback)
python bili_quick.py <url> --engine=sensevoice                      # SenseVoice (ultra-fast, no punctuation)
python bili_quick.py <url> --engine=parakeet                        # Parakeet (English only, word timestamps)
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
| `FUNASR_DIR` | `<MODELS_ROOT>\funasr-nano` | Fun-ASR-Nano model dir |
| `QWEN_ASR_DIR` | `<MODELS_ROOT>\qwen3-asr-1.7b\...` | Qwen3-ASR model dir |
| `PARAKET_EXE` | `<MODELS_ROOT>\parakeet\...\parakeet-cli.exe` | parakeet executable |
| `PARAKET_GGUF` | `<MODELS_ROOT>\parakeet\tdt-0.6b-v3-q4_k.gguf` | parakeet model |
| `BILI_COOKIE_FILE` | `./cookie.txt` | cookie file path |
| `BILI_DEEPSEEK_KEY_FILE` | `./deepseek_key.txt` | DeepSeek key file (only for `--api`) |

## ⚖️ Disclaimer

- For personal learning and research only; subtitle/audio content belongs to the original creators and Bilibili
- Respect [Bilibili Terms of Service](https://www.bilibili.com/blackboard/activity-9pg6xIqxDZ.html) and video copyright
- Not for commercial use or large-scale scraping
- Not affiliated with Bilibili

## 📄 License

MIT
