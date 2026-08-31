#!/usr/bin/env python3
"""download_qwen06b.py — 下载 Qwen3-ASR-0.6B int4 ONNX（走 hf-mirror + 分片并行）

来源: andrewleech/qwen3-asr-0.6b-onnx
目标: D:\\BiliModels\\qwen3-asr-0.6b\\qwen3-asr-0.6b-int4\\
用法: python download_qwen06b.py [并发数]
"""
import os
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://hf-mirror.com/andrewleech/qwen3-asr-0.6b-onnx/resolve/main"
DEST_ROOT = r"D:\BiliModels\qwen3-asr-0.6b\qwen3-asr-0.6b-int4"

FILES = [
    "encoder.int4.onnx",
    "decoder_init.int4.onnx",
    "decoder_step.int4.onnx",
    "decoder_weights.int4.data",
    "embed_tokens.bin",
    "config.json",
    "added_tokens.json",
    "preprocessor_config.json",
    "tokenizer_config.json",
    "tokenizer.json",
    "vocab.json",
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def real_size(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers.get("Content-Length") or 0)


def main():
    workers = sys.argv[1] if len(sys.argv) > 1 else "16"
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parallel_download.py")
    os.makedirs(DEST_ROOT, exist_ok=True)
    for rel in FILES:
        url = f"{BASE}/{rel}"
        try:
            size = real_size(url)
        except Exception as e:
            print(f"[!] HEAD 失败 {rel}: {e}，跳过", flush=True)
            continue
        dest = os.path.join(DEST_ROOT, rel)
        if os.path.exists(dest) and os.path.getsize(dest) >= size:
            print(f"[=] 已存在: {rel} ({size} bytes)", flush=True)
            continue
        print(f"\n>>> 下载 {rel} ({size/1048576:.0f} MB)", flush=True)
        subprocess.run([sys.executable, script, url, dest, workers], check=True)
        got = os.path.getsize(dest) if os.path.exists(dest) else 0
        if got < size:
            print(f"[x] {rel} 不完整 ({got}/{size})，请重跑本脚本续传", flush=True)
            sys.exit(1)
    print("\n[√] Qwen3-ASR-0.6B int4 全部就绪:", DEST_ROOT, flush=True)


if __name__ == "__main__":
    main()
