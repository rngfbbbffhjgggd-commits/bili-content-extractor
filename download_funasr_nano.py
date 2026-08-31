#!/usr/bin/env python3
"""download_funasr_nano.py — 下载 sherpa-onnx FunASR-Nano 模型（走 hf-mirror + 分片并行）

来源: csukuangfj/sherpa-onnx-funasr-nano-int8-2025-12-30
目标: D:\\BiliModels\\funasr-nano\\
用法: python download_funasr_nano.py [并发数]
"""
import os
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://hf-mirror.com/csukuangfj/sherpa-onnx-funasr-nano-int8-2025-12-30/resolve/main"
DEST_ROOT = r"D:\BiliModels\funasr-nano"

FILES = [
    "embedding.int8.onnx",
    "encoder_adaptor.int8.onnx",
    "llm.fp16.onnx",   # int8 版有复读退化 bug（issue #3062），必须用 fp16
    "llm.int8.onnx",   # 保留作为 fp16 缺失时的回退
    "Qwen3-0.6B/tokenizer.json",
    "Qwen3-0.6B/vocab.json",
    "Qwen3-0.6B/merges.txt",
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def real_size(url):
    """服务器 Content-Length 为准"""
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers.get("Content-Length") or 0)


def main():
    workers = sys.argv[1] if len(sys.argv) > 1 else "16"
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parallel_download.py")
    for rel in FILES:
        url = f"{BASE}/{rel}"
        size = real_size(url)
        dest = os.path.join(DEST_ROOT, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.exists(dest) and os.path.getsize(dest) >= size:
            print(f"[=] 已存在: {rel} ({size} bytes)", flush=True)
            continue
        print(f"\n>>> 下载 {rel} ({size/1048576:.0f} MB)", flush=True)
        subprocess.run([sys.executable, script, url, dest, workers], check=True)
        got = os.path.getsize(dest) if os.path.exists(dest) else 0
        if got < size:
            print(f"[x] {rel} 不完整 ({got}/{size})，请重跑本脚本续传", flush=True)
            sys.exit(1)
    print("\n[√] FunASR-Nano 全部就绪:", DEST_ROOT, flush=True)


if __name__ == "__main__":
    main()
