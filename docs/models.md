---
title: 模型下载
layout: default
---

# 🤖 模型下载

本项目的转写模型是**按语言和视频长度自动切换**的。你不需要全部下载——按你常处理的视频类型，下对应模型即可。

> 📦 模型总量约 **8GB**，默认放在 `D:\BiliModels`，可通过环境变量改到任意盘。下载一次即可长期使用。

## 模型怎么选

| 模型 | 体积 | 用途 | 适合场景 |
|---|---|---|---|
| **Qwen3-ASR-1.7B**（int4） | 3.9GB | 最准，52 语言 | **<10 分钟**（任意语言）自动用它 |
| **Qwen3-ASR-0.6B**（int4） | 约 2GB | 中文快档 | **中文 ≥10 分钟**自动用它 |
| **Fun-ASR-Nano-2512**（fp16） | 约 2GB | 英/日/粤快档 | **英/日/粤 ≥10 分钟**自动用它 |
| **SenseVoice**（int8） | 239MB | 语言检测 | 用于识别视频是什么语言（不参与转写，但建议装） |

> ⚠️ Fun-ASR-Nano **必须用 fp16 版**——int8 版有复读退化的 bug（详见 [sherpa-onnx issue #3062](https://github.com/k2-fsa/sherpa-onnx/issues/3062)）。

## 📥 下载方式

### Qwen3-ASR-1.7B（中文最准，手动下载）

从 [andrewleech/qwen3-asr-1.7b-onnx](https://huggingface.co/andrewleech/qwen3-asr-1.7b-onnx) 下载 `qwen3-asr-1.7b-int4.tar.gz`，解压到这个路径：

```
D:\BiliModels\qwen3-asr-1.7b\qwen3-asr-1.7b-int4\
```

### Qwen3-ASR-0.6B（中文长视频快档，一键下载）

```bash
python download_qwen06b.py
```

自动落到 `D:\BiliModels\qwen3-asr-0.6b\qwen3-asr-0.6b-int4\`（走 hf-mirror 国内镜像 + 分片并行 + 断点续传）。

### Fun-ASR-Nano-2512（英/日/粤长视频快档，一键下载）

```bash
python download_funasr_nano.py
```

自动落到 `D:\BiliModels\funasr-nano\`。

### SenseVoice（语言检测，239MB）

从 [sherpa-onnx releases](https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models) 下载 `sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2`，解压到：

```
D:\BiliModels\sensevoice\
```

## 🌐 网络不稳？用内置加速下载器

仓库自带的 `parallel_download.py` 支持**分片并行下载 + 断点续传**（官方宣称快 300 倍）：

```bash
python parallel_download.py <url> <保存路径> 16 2
```

参数说明：`<url>` 是要下载的文件地址，`<保存路径>` 是保存位置，`16` 是并发分片数，`2` 是重试次数。

## 🗂️ 环境变量（可选，想换盘/换路径时用）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `BILI_MODELS_ROOT` | `D:\BiliModels` | 模型根目录 |
| `QWEN_ASR_DIR` | `<MODELS_ROOT>\qwen3-asr-1.7b\...` | Qwen3-ASR-1.7B 模型目录 |
| `QWEN06_ASR_DIR` | `<MODELS_ROOT>\qwen3-asr-0.6b\...` | Qwen3-ASR-0.6B 模型目录 |
| `FUNASR_DIR` | `<MODELS_ROOT>\funasr-nano` | Fun-ASR-Nano 模型目录 |

模型就绪后，去 [使用教程](/bili-content-extractor/usage) 跑通第一条视频。
