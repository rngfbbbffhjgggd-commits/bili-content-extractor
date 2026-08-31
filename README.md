# 📺 Bili Content Extractor（B站/YouTube 视频内容一键提取）

**[English](README_EN.md) · 中文**

把 **B站 / YouTube** 视频变成**可读文本 + 可投喂的总结材料**，全程本地、免费、不消耗 token。

![工作流程](docs/flow.svg)

```
B站 / YouTube 视频链接
   │
   ├─ 有字幕 ──→ 直接下载字幕（B站 AI字幕 / YouTube Transcript API）
   │
   └─ 无字幕 ──→ SenseVoice 内容语言检测，本地转写
                  ├─ 中文<10分钟 → Qwen3-ASR-1.7B（最准）
                  ├─ 中文≥10分钟 → Qwen3-ASR-0.6B（快档）
                  ├─ 英/日/粤   → Fun-ASR-Nano fp16（标点+热词）
                  └─ 手动       → SenseVoice（极速无标点）
                        │
                        ▼
          生成「投喂文件.md」（视频信息 + 指令 + 带时间戳全文）
                        │
                        ▼
    拖进 DeepSeek 网页版 → 免费得到详细时间线总结（不花 token）
```

## ✨ 特性

- **多平台**：支持 **B站**（AI 字幕优先）和 **YouTube**（Transcript API 免费字幕，无字幕自动转写）
- **字幕优先**：有字幕的视频直接下载，零成本零延迟
- **中文双档**：<10 分钟用 Qwen3-ASR-1.7B（最准，52 语言）；≥10 分钟用 Qwen3-ASR-0.6B（快档，比 1.7B 快约 2 倍）
- **英文引擎 Fun-ASR-Nano-2512**：本地 CPU 英文最优解（带标点+热词），覆盖英/日/粤与中英混说
- **全链路标点**：所有转写引擎输出完整标点（SenseVoice 仅用于语言检测）——投喂 DeepSeek 总结质量更高
- **免费总结**：产出带指令的投喂文件，配合 DeepSeek **网页版**免费总结，不消耗 API token
- **全程本地**：音频转写完全本地运行，不上传
- **硬盘友好**：模型约 8GB，可放任意盘（默认 `D:\BiliModels`，环境变量可改）

## 📦 环境要求

- Windows / Linux / macOS（sherpa-onnx / onnxruntime 跨平台）
- Python 3.10+
- [ffmpeg](https://ffmpeg.org/)（转码音频）

## 🚀 安装

```bash
git clone https://github.com/rngfbbbffhjgggd-commits/bili-content-extractor.git
cd bili-content-extractor
pip install -r requirements.txt
```

## 🤖 模型下载（约 8GB，放 `D:\BiliModels` 或自定义目录）

### 中文（默认，最准）：Qwen3-ASR-1.7B（int4 ONNX，3.9GB）

从 [andrewleech/qwen3-asr-1.7b-onnx](https://huggingface.co/andrewleech/qwen3-asr-1.7b-onnx) 下载 `qwen3-asr-1.7b-int4.tar.gz`，解压到：
```
D:\BiliModels\qwen3-asr-1.7b\qwen3-asr-1.7b-int4\
```
> 中文 <10 分钟自动用它（最准，52 语言）。

### 中文（长视频快档）：Qwen3-ASR-0.6B（int4 ONNX，约 2GB）

一键下载（hf-mirror 国内镜像 + 分片并行，断点续传）：
```bash
python download_qwen06b.py
```
落到 `D:\BiliModels\qwen3-asr-0.6b\qwen3-asr-0.6b-int4\`。
> 中文 ≥10 分钟自动用它（同引擎体系，比 1.7B 快约 2 倍）。

### 英文/日文/粤语：Fun-ASR-Nano-2512（fp16 ONNX，约 2GB）

一键下载（hf-mirror 国内镜像 + 分片并行，断点续传）：
```bash
python download_funasr_nano.py
```
模型落到 `D:\BiliModels\funasr-nano\`（官方 sherpa-onnx 导出，中/英/日 + 7 方言 + 26 口音，自带标点/ITN）。
> ⚠️ 必须用 **fp16** 版 llm——int8 版有复读退化 bug（[sherpa-onnx issue #3062](https://github.com/k2-fsa/sherpa-onnx/issues/3062)）。
> 英文默认用它：本地 CPU 英文最优解（官方 LibriSpeech-clean WER 1.76，优于 Qwen3-ASR-0.6B 2.11 / GLM-ASR-nano 2.00），支持中英混说。

### 语言检测：SenseVoice（int8 ONNX，239MB）

从 [k2-fsa/sherpa-onnx releases](https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models) 下载 `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2`，解压到：
```
D:\BiliModels\sensevoice\
```
> 仅用于 40 秒内容语言检测（`result.lang`），不再参与转写。

> 💡 网络不稳时可用仓库自带的 `parallel_download.py` 分片并行下载（快 300 倍）：
> ```bash
> python parallel_download.py <url> <保存路径> 16 2
> ```

## 🔑 配置 B 站 Cookie（一次性）

B 站的 AI 字幕列表**需要登录态**才能获取：

1. 浏览器登录 bilibili.com，打开任意视频页
2. F12 → Network → 刷新 → 点任意 `api.bilibili.com` 请求
3. 复制 Request Headers 里整段 `Cookie:` 的值
4. 保存为 `cookie.txt`（放在脚本目录，一行）

> 🔒 cookie 仅保存在本地、只用于调用 B 站接口，不会上传；约一个月过期，过期后重新复制即可。

## 🎯 使用

**Windows 一键版**：双击 `B站一键提取.bat` → 粘贴链接 → 回车。

**命令行**：
```bash
python bili_quick.py "https://www.bilibili.com/video/BVxxxx"          # B站
python bili_quick.py "https://www.youtube.com/watch?v=xxxx"           # YouTube
python bili_quick.py <链接> --lang=zh                                 # 强制中文
python bili_quick.py <链接> --lang=en                                 # 强制英文
python bili_quick.py <链接> --engine=qwen                            # 中文强制 Qwen3-1.7B（最准）
python bili_quick.py <链接> --engine=qwen06                          # 中文强制 Qwen3-0.6B（长视频快档）
python bili_quick.py <链接> --engine=funasr                          # 强制 Fun-ASR-Nano（英/日/粤）
python bili_quick.py <链接> --engine=sensevoice                      # SenseVoice（极速，无标点）
python bili_quick.py <链接> --api                                     # 可选：用 DeepSeek API 自动总结（消耗 token）
```

**产物**（`BilibiliContent/<BV号>/`）：
- 有字幕：`P1_ai-zh.txt` / `.srt`
- 无字幕：`transcript.txt` + `投喂DeepSeek网页版.md`
- 投喂文件内含完整指令，拖进 [chat.deepseek.com](https://chat.deepseek.com) 回车即可得到详细时间线总结

## 🧩 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `BILI_MODELS_ROOT` | `D:\BiliModels` | 模型根目录 |
| `QWEN_ASR_DIR` | `<MODELS_ROOT>\qwen3-asr-1.7b\...` | Qwen3-ASR-1.7B 模型目录 |
| `QWEN06_ASR_DIR` | `<MODELS_ROOT>\qwen3-asr-0.6b\...` | Qwen3-ASR-0.6B 模型目录 |
| `FUNASR_DIR` | `<MODELS_ROOT>\funasr-nano` | Fun-ASR-Nano 模型目录 |
| `BILI_COOKIE_FILE` | `./cookie.txt` | cookie 文件路径 |
| `BILI_DEEPSEEK_KEY_FILE` | `./deepseek_key.txt` | DeepSeek key 文件路径（仅 `--api` 用） |

## ⚖️ 免责声明

- 本项目仅用于个人学习与研究，字幕/音频内容版权归原作者与 B 站所有
- 请遵守 [Bilibili 服务条款](https://www.bilibili.com/blackboard/activity-9pg6xIqxDZ.html) 及视频版权规定
- 请勿用于商业用途或大规模抓取
- 本项目与哔哩哔哩官方无任何关联

## 📄 License

MIT
