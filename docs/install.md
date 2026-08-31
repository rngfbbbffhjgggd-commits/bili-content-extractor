---
title: 安装
layout: default
---

# 🚀 安装

环境要求 + 克隆项目 + 装依赖，三步搞定。

## 1️⃣ 环境要求

| 项目 | 要求 |
|---|---|
| 操作系统 | Windows / Linux / macOS（sherpa-onnx / onnxruntime 跨平台） |
| Python | 3.10 及以上 |
| ffmpeg | 需要（用于转码音频） |

> 💡 还没装 Python？去 [python.org](https://www.python.org/) 下载安装，勾选 **Add Python to PATH**。
> 💡 还没装 ffmpeg？看下面的说明。

### 安装 ffmpeg

**Windows**：从 [ffmpeg.org](https://ffmpeg.org/) 下载后，把 `ffmpeg.exe` 所在目录加到系统 PATH。

**macOS**：`brew install ffmpeg`

**Linux**：`sudo apt install ffmpeg`（或发行版对应命令）

验证是否装好：

```bash
ffmpeg -version
```

## 2️⃣ 克隆项目

```bash
git clone https://github.com/rngfbbbffhjgggd-commits/bili-content-extractor.git
cd bili-content-extractor
```

> 不想用 git？直接到 [GitHub 仓库页](https://github.com/rngfbbbffhjgggd-commits/bili-content-extractor) 点 **Code → Download ZIP**，解压后进入该目录。

## 3️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

需要国内加速可以加镜像源：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## ✅ 装好了吗？

运行下面这行，看到帮助信息就说明环境 OK：

```bash
python bili_quick.py --help
```

接下来就可以 [下载模型](/bili-content-extractor/models) 了。
