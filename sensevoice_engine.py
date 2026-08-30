#!/usr/bin/env python3
"""sensevoice_engine.py — SenseVoice 中文/多语转写引擎（sherpa-onnx，RTF<0.1 极快）

模型目录: D:\\BiliModels\\sensevoice\\sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17
依赖: sherpa-onnx（pip install sherpa-onnx）
"""
import os
import re
import sys
import wave

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

MODEL_DIR = os.environ.get(
    "SENSEVOICE_DIR",
    r"D:\BiliModels\sensevoice\sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17",
)


class SenseVoiceEngine:
    def __init__(self, num_threads=8):
        import sherpa_onnx

        model = os.path.join(MODEL_DIR, "model.int8.onnx")
        if not os.path.exists(model):
            model = os.path.join(MODEL_DIR, "model.onnx")
        tokens = os.path.join(MODEL_DIR, "tokens.txt")
        if not os.path.exists(model) or not os.path.exists(tokens):
            raise FileNotFoundError(f"SenseVoice 模型缺失: {MODEL_DIR}")
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=model,
            tokens=tokens,
            num_threads=num_threads,
            use_itn=True,
        )
        print("[√] SenseVoice 引擎就绪 (RTF<0.1, 快 6-10 倍)")

    def transcribe(self, audio_path):
        """整段转写（wav 16k）-> 文本"""
        with wave.open(audio_path, "rb") as w:
            sr = w.getframerate()
            if w.getsampwidth() != 2:
                raise ValueError("仅支持 16bit PCM wav")
            samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        stream = self.recognizer.create_stream()
        stream.accept_waveform(sr, samples)
        self.recognizer.decode_stream(stream)
        text = stream.result.text
        # 清洗语言/情感标记，如 <|zh|> <|HAPPY|>
        text = re.sub(r"<\|[^|]*\|>", "", text).strip()
        return text


def transcribe_audio(audio_path, outdir, chunk_sec=60):
    """分段转写 -> [(start_sec, text)]（与 Qwen3-ASR 接口一致）"""
    import time

    with wave.open(audio_path, "rb") as w:
        sr = w.getframerate()
        audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)

    eng = SenseVoiceEngine()
    total = len(audio) / sr
    segs = []
    chunk_len = chunk_sec * sr
    n_chunks = max(1, int(np.ceil(total / chunk_sec)))
    for i in range(n_chunks):
        start = i * chunk_sec
        part = audio[i * chunk_len:(i + 1) * chunk_len]
        if len(part) < sr * 0.5:
            continue
        tmp = os.path.join(outdir, f"_sv_chunk_{i}.wav")
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
