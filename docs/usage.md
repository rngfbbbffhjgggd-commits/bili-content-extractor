---
title: 使用教程
layout: default
---

# 🎯 使用教程

从配置一次 B 站 Cookie，到把一条视频变成可读文本 + 投喂文件，跟着做就行。

## 🔑 第一步：配置 B 站 Cookie（一次性）

B 站的 **AI 字幕列表需要登录态**才能获取，所以要配置一次 cookie：

1. 浏览器登录 **bilibili.com**，打开任意视频页
2. 按 **F12** 打开开发者工具 → 切到 **Network** 标签 → 刷新页面
3. 点任意一条 `api.bilibili.com` 请求
4. 在右侧 **Request Headers** 里找到 `Cookie:` 这一行，复制它后面的整段内容
5. 保存为 `cookie.txt`，放在脚本目录里（文本文件，内容就是那一行 cookie，不要换行）

> 🔒 cookie 只保存在本地、只用于调用 B 站接口，**不会上传**。
> ⏰ 约**一个月**过期，过期后重新复制即可（报错会提示你）。

## ▶️ 第二步：运行

### 方式 A：Windows 一键版（最省事）

双击项目里的 **`B站一键提取.bat`** → 粘贴视频链接 → 回车。

### 方式 B：命令行

```bash
# B站视频
python bili_quick.py "https://www.bilibili.com/video/BVxxxx"

# YouTube视频
python bili_quick.py "https://www.youtube.com/watch?v=xxxx"
```

## 🧰 常用参数

| 参数 | 作用 |
|---|---|
| `--lang=zh` / `--lang=en` | 强制指定语言 |
| `--engine=qwen` | 中文强制用 Qwen3-ASR-1.7B（最准） |
| `--engine=qwen06` | 中文强制用 Qwen3-ASR-0.6B（长视频快档） |
| `--engine=funasr` | 强制用 Fun-ASR-Nano（英/日/粤） |
| `--engine=sensevoice` | SenseVoice（极速，无标点） |
| `--api` | 可选：用 DeepSeek API 自动总结（**消耗 token**，想免费就别加） |

### 示例

```bash
# 强制中文、用最准的 1.7B
python bili_quick.py "视频链接" --lang=zh --engine=qwen

# 英文长视频，用快档
python bili_quick.py "链接" --lang=en --engine=funasr
```

## 📄 第三步：看产物

运行后在 `BilibiliContent/<BV号>/` 目录下会得到：

| 情况 | 产物 |
|---|---|
| 有字幕的视频 | `P1_ai-zh.txt` / `.srt` |
| 无字幕的视频 | `transcript.txt` + `投喂DeepSeek网页版.md` |

> 🍬 那个 **`投喂DeepSeek网页版.md`** 是精华：里面已经写好了**完整指令 + 带时间戳的全文**。把它拖进 [chat.deepseek.com](https://chat.deepseek.com)，回车，就能免费得到一份详细的时间线总结，不花任何 token。

## ✅ 小结（一句话流程）

```
配 cookie → 跑 bili_quick.py → 拿到 txt / 投喂文件 → 丢给 DeepSeek 网页版 → 得到总结
```
