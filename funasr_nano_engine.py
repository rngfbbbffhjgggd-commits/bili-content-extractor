#!/usr/bin/env python3
"""funasr_nano_engine.py — Fun-ASR-Nano-2512 转写引擎（sherpa-onnx，中英日 + 7方言 + 26口音）

模型目录: D:\\BiliModels\\funasr-nano\\  (csukuangfj/sherpa-onnx-funasr-nano-int8-2025-12-30)
依赖: sherpa-onnx >= 1.13（OfflineRecognizer.from_funasr_nano）
特点: 自带标点 + ITN、热词纠偏、远场噪声优化（必须用 fp16 llm，int8 有复读退化 bug）
"""
import os
import re
import sys
import wave

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

MODEL_DIR = os.environ.get("FUNASR_DIR", r"D:\BiliModels\funasr-nano")


class FunASRNanoEngine:
    def __init__(self, num_threads=8, hotwords=""):
        import sherpa_onnx

        # 注意: int8 版 llm 会复读退化/漏译（sherpa-onnx issue #3062），必须用 fp16
        llm = os.path.join(MODEL_DIR, "llm.fp16.onnx")
        needed = {
            "encoder_adaptor.int8.onnx": "编码器",
            "embedding.int8.onnx": "Embedding",
            "Qwen3-0.6B": "Tokenizer",
        }
        for f, name in needed.items():
            if not os.path.exists(os.path.join(MODEL_DIR, f)):
                raise FileNotFoundError(f"Fun-ASR-Nano 模型缺失: {os.path.join(MODEL_DIR, f)} ({name})")
        if not os.path.exists(llm):
            raise FileNotFoundError(f"Fun-ASR-Nano 模型缺失: {llm} (LLM)")
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_funasr_nano(
            encoder_adaptor=os.path.join(MODEL_DIR, "encoder_adaptor.int8.onnx"),
            llm=llm,
            embedding=os.path.join(MODEL_DIR, "embedding.int8.onnx"),
            tokenizer=os.path.join(MODEL_DIR, "Qwen3-0.6B"),
            num_threads=num_threads,
            provider="cpu",
            itn=True,
            hotwords=hotwords,
        )
        print("[√] Fun-ASR-Nano-2512 引擎就绪 (fp16, 标点+ITN)")

    def transcribe(self, audio_path):
        """整段转写（wav 16k）-> 文本（自带标点）"""
        with wave.open(audio_path, "rb") as w:
            sr = w.getframerate()
            if w.getsampwidth() != 2:
                raise ValueError("仅支持 16bit PCM wav")
            samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        stream = self.recognizer.create_stream()
        stream.accept_waveform(sr, samples)
        self.recognizer.decode_stream(stream)
        text = stream.result.text
        # 清洗可能存在的语言/情感标记，如 <|zh|>
        text = re.sub(r"<\|[^|]*\|>", "", text).strip()
        return text


def transcribe_audio(audio_path, outdir, chunk_sec=25, hotwords=""):
    """分段转写 -> [(start_sec, text)]（与 SenseVoice/Qwen 接口一致）

    注意: funasr-nano 的 ONNX 导出 max_total_len=512（KV 容量），
    音频 token 率约 16.65/s -> 单块上限约 29s，默认 25s 留余量。
    """
    import time

    if chunk_sec > 29:
        print(f"[!] funasr-nano 单块上限约 29s，{chunk_sec}s 已自动调整为 25s")
        chunk_sec = 25

    with wave.open(audio_path, "rb") as w:
        sr = w.getframerate()
        audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)

    eng = FunASRNanoEngine(hotwords=hotwords)
    total = len(audio) / sr
    segs = []
    chunk_len = chunk_sec * sr
    n_chunks = max(1, int(np.ceil(total / chunk_sec)))
    for i in range(n_chunks):
        start = i * chunk_sec
        part = audio[i * chunk_len:(i + 1) * chunk_len]
        if len(part) < sr * 0.5:
            continue
        tmp = os.path.join(outdir, f"_fn_chunk_{i}.wav")
        with wave.open(tmp, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(part.tobytes())
        t0 = time.time()
        text = eng.transcribe(tmp)
        os.remove(tmp)
        dt = time.time() - t0
        print(f"  [块 {i+1}/{n_chunks} {start//60:02d}:{start%60:02d} {dt:.1f}s]", flush=True)
        if text:
            segs.append((start, text))
    return segs


if __name__ == "__main__":
    result = transcribe_audio(sys.argv[1], os.path.dirname(os.path.abspath(sys.argv[1])))
    for t, x in result:
        print(f"[{int(t)//60:02d}:{int(t)%60:02d}] {x}")
