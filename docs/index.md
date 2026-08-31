---
title: 欢迎
layout: default
---

# 📺 Bili Content Extractor 文档站

> 把 **B站 / YouTube** 视频变成**可读文本 + 可投喂的总结材料**，全程本地、免费、不消耗 token。

这是该项目给观众和用户的**配套文档**：从这里可以了解它能做什么、怎么安装、怎么下载模型、怎么使用，以及常见问题。视频里的讲解步骤，都可以在这个站上对照着做。

## 🧭 这个站有哪些内容

- **[安装](/bili-content-extractor/install)** —— 环境要求、克隆、装依赖
- **[模型下载](/bili-content-extractor/models)** —— 不同语言的模型怎么选、怎么下载
- **[使用教程](/bili-content-extractor/usage)** —— 看图说话，从零跑通一条视频
- **[常见问题](/bili-content-extractor/faq)** —— 遇到报错先来这里
- **[视频讲解稿](/bili-content-extractor/video)** —— 对应视频的图文讲解文案

## ✨ 它做了什么

一句话：**把你正在关注的一个视频，变成一个带时间戳的全文字脚本，再丢给 DeepSeek 免费总结。**

```
B站 / YouTube 视频链接
   │
   ├─ 有字幕 ──→ 直接下载字幕（B站 AI字幕 / YouTube Transcript API）
   │
   └─ 无字幕 ──→ 本地转写
                  ├─ <10分钟（任意语言） → Qwen3-ASR-1.7B（最准）
                  ├─ ≥10分钟 中文      → Qwen3-ASR-0.6B（快档）
                  ├─ ≥10分钟 英/日/粤  → Fun-ASR-Nano fp16（快档）
                  └─ 手动             → SenseVoice（极速无标点）
                        │
                        ▼
          生成「投喂文件.md」（视频信息 + 指令 + 带时间戳全文）
                        │
                        ▼
    拖进 DeepSeek 网页版 → 免费得到详细时间线总结（不花 token）
```

## 💡 为什么值得用它

- **免费**：转写本地跑，不消耗任何 API token；总结用 DeepSeek **网页版**就行
- **全本地**：音频不上传，隐私放心
- **多平台**：B站（AI 字幕优先）+ YouTube（Transcript API 免费字幕）
- **多语言**：中 / 英 / 日 / 粤，52 语言转写
- **硬盘友好**：模型约 8GB，可放任意盘

## 🚀 30 秒了解怎么用

1. 安装环境 + 克隆项目（见 [安装](/bili-content-extractor/install)）
2. 下载需要的模型（见 [模型下载](/bili-content-extractor/models)）
3. 配置一次 B 站 Cookie（见 [使用教程](/bili-content-extractor/usage)）
4. `python bili_quick.py "视频链接"` → 拿到文本和投喂文件

完整步骤都在 [使用教程](/bili-content-extractor/usage)。

> 📄 **源码地址**：[GitHub 仓库](https://github.com/rngfbbbffhjgggd-commits/bili-content-extractor) · **许可证**：MIT
