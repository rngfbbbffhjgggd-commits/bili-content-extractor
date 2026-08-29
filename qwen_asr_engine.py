#!/usr/bin/env python3
"""qwen_asr_engine.py — Qwen3-ASR ONNX int4 CPU 推理引擎（纯 numpy + onnxruntime）

模型目录: D:\\BiliModels\\qwen3-asr-1.7b\\qwen3-asr-1.7b-int4
依赖: numpy, onnxruntime, tokenizers (librosa 可选，无则用手写 mel)
"""
import json
import os
import re
import sys
import time

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

MODEL_DIR = os.environ.get("QWEN_ASR_DIR", r"D:\BiliModels\qwen3-asr-1.7b\qwen3-asr-1.7b-int4")
SAMPLE_RATE = 16000
N_FFT = 400
HOP_LENGTH = 160
N_MELS = 128
FMIN = 0.0
FMAX = 8000.0

# ---- special tokens (Qwen3-ASR) ----
ENDOFTEXT = 151643
IM_START = 151644
IM_END = 151645
AUDIO_START = 151669
AUDIO_END = 151670
AUDIO_PAD = 151676
EOS_IDS = [ENDOFTEXT, IM_END]


def _get_feat_extract_output_lengths(t):
    """encoder 输出的 token 数（与官方一致）"""
    CONV_WINDOW = 100
    TOKENS_PER_WINDOW = 13
    leave = t % CONV_WINDOW
    n = (leave + 1) // 2
    n = (n + 1) // 2
    n = (n + 1) // 2
    return n + (t // CONV_WINDOW) * TOKENS_PER_WINDOW


def build_prompt_ids(audio_token_count):
    """构造 ASR prompt token id 序列（v3: input_ids 版）"""
    ids = [IM_START, 9125, 198, IM_END, 198]  # system
    ids += [IM_START, 882, 198, AUDIO_START]  # user + audio_start
    ids += [AUDIO_PAD] * audio_token_count
    ids += [AUDIO_END, IM_END, 198]
    ids += [IM_START, 77091, 198]  # assistant
    return ids


def audio_pad_range(prompt_ids):
    start = None
    end = None
    for i, tid in enumerate(prompt_ids):
        if tid == AUDIO_PAD:
            if start is None:
                start = i
            end = i + 1
    return start, end


# ---------- mel 特征（librosa 优先，无则手写） ----------

def _hand_mel_filterbank(sr, n_fft, n_mels, fmin, fmax):
    """Slaney-normalized mel filterbank（纯 numpy，等价 librosa norm='slaney'）"""
    def hz_to_mel(f):
        f_sp = 200.0 / 3
        mels = f / f_sp
        min_log_hz = 1000.0
        min_log_mel = min_log_hz / f_sp
        logstep = np.log(6.4) / 27.0
        mask = f > min_log_hz
        mels[mask] = min_log_mel + np.log(f[mask] / min_log_hz) / logstep
        return mels

    def mel_to_hz(m):
        f_sp = 200.0 / 3
        freqs = f_sp * m
        min_log_hz = 1000.0
        min_log_mel = min_log_hz / f_sp
        logstep = np.log(6.4) / 27.0
        mask = m > min_log_mel
        freqs[mask] = min_log_hz * np.exp(logstep * (m[mask] - min_log_mel))
        return freqs

    min_mel = float(hz_to_mel(np.array([fmin]))[0])
    max_mel = float(hz_to_mel(np.array([fmax]))[0])
    mels = np.linspace(min_mel, max_mel, n_mels + 2)
    hz = mel_to_hz(mels)
    bins = np.floor((n_fft + 1) * hz / sr)
    fbank = np.zeros((n_mels, n_fft // 2 + 1))
    for i in range(n_mels):
        b_left, b_center, b_right = bins[i], bins[i + 1], bins[i + 2]
        l, c, r = int(b_left), int(b_center), int(b_right)
        if c > l:
            fbank[i, l:c] = (np.arange(l, c) - b_left) / (b_center - b_left)
        if r > c:
            fbank[i, c:r] = (b_right - np.arange(c, r)) / (b_right - b_center)
    return fbank


def log_mel(audio):
    """audio: 1-D float32 16k mono -> [1, 128, T]"""
    try:
        import librosa

        mel_filters = librosa.filters.mel(sr=SAMPLE_RATE, n_fft=N_FFT, n_mels=N_MELS,
                                          fmin=FMIN, fmax=FMAX, norm="slaney")
    except ImportError:
        mel_filters = _hand_mel_filterbank(SAMPLE_RATE, N_FFT, N_MELS, FMIN, FMAX)

    # periodic hann window（与 torch.hann_window(periodic) 一致）
    try:
        from scipy.signal import windows as scipy_windows

        window = scipy_windows.hann(N_FFT, sym=False).astype(np.float32)
    except ImportError:
        window = np.hanning(N_FFT + 1)[:-1].astype(np.float32)

    n_frames = 1 + (len(audio) - N_FFT) // HOP_LENGTH
    if len(audio) < N_FFT:
        audio = np.pad(audio, (0, N_FFT - len(audio)))
        n_frames = 1
    frames = np.stack(
        [audio[i * HOP_LENGTH:i * HOP_LENGTH + N_FFT] for i in range(n_frames)]
    )
    frames = frames * window
    spec = np.fft.rfft(frames, n=N_FFT, axis=1)
    mag = (np.abs(spec) ** 2).T  # [n_fft//2+1, T]
    mel = mel_filters @ mag  # [n_mels, T]
    log_spec = np.clip(mel, 1e-10, None).astype(np.float64)
    log_spec = np.log10(log_spec)
    log_spec = np.maximum(log_spec, log_spec.max() - 8.0)
    log_spec = (log_spec + 4.0) / 4.0
    log_spec = log_spec[:, :-1]  # drop last frame
    return log_spec[np.newaxis].astype(np.float32)  # [1, 128, T]


# ---------- 推理 ----------

class QwenASREngine:
    def __init__(self, model_dir=MODEL_DIR, threads=0):
        import onnxruntime as ort

        opts = ort.SessionOptions()
        if threads > 0:
            opts.intra_op_num_threads = threads
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.encoder = ort.InferenceSession(os.path.join(model_dir, "encoder.int4.onnx"), opts)
        self.decoder_init = ort.InferenceSession(os.path.join(model_dir, "decoder_init.int4.onnx"), opts)
        self.decoder_step = ort.InferenceSession(os.path.join(model_dir, "decoder_step.int4.onnx"), opts)
        self.embed_tokens = np.fromfile(os.path.join(model_dir, "embed_tokens.bin"), dtype=np.float16).astype(np.float32)
        with open(os.path.join(model_dir, "config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        self.hidden = cfg.get("decoder", {}).get("hidden_size") or cfg.get("hidden_size")
        self.embed_tokens = self.embed_tokens.reshape(-1, self.hidden)

        from tokenizers import Tokenizer

        self.tokenizer = Tokenizer.from_file(os.path.join(model_dir, "tokenizer.json"))
        print(f"[√] Qwen3-ASR 引擎就绪 ({model_dir})")

    def transcribe(self, audio_path, max_tokens=2048, start_time=0.0):
        import wave

        # 优先 soundfile（m4s/mp4 等），fallback wave（wav）
        try:
            import soundfile as sf

            audio, sr = sf.read(audio_path, dtype="float32", always_2d=False)
        except Exception:
            with wave.open(audio_path, "rb") as w:
                sr = w.getframerate()
                audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != SAMPLE_RATE:
            # 简单线性重采样
            n = int(len(audio) * SAMPLE_RATE / sr)
            audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio)
        audio = audio.astype(np.float32)

        mel = log_mel(audio)  # [1, 128, T]
        feat_len = _get_feat_extract_output_lengths(mel.shape[2])
        if feat_len < 1:
            return ""

        t0 = time.time()
        audio_features = self.encoder.run(["audio_features"], {"mel": mel})[0]  # [1, feat_len, hidden]
        print(f"  [encoder {time.time()-t0:.1f}s, tokens={feat_len}]", flush=True)

        prompt_ids = build_prompt_ids(feat_len)
        position_ids = np.arange(len(prompt_ids), dtype=np.int64)[np.newaxis, :]
        audio_start, _ = audio_pad_range(prompt_ids)
        input_ids = np.array(prompt_ids, dtype=np.int64)[np.newaxis, :]
        audio_offset = np.array([audio_start], dtype=np.int64)

        t0 = time.time()
        logits, pk, pv = self.decoder_init.run(
            ["logits", "present_keys", "present_values"],
            {"input_ids": input_ids, "position_ids": position_ids,
             "audio_features": audio_features, "audio_offset": audio_offset},
        )
        tokens = [int(np.argmax(logits[0, -1, :]))]
        if tokens[0] not in EOS_IDS:
            pos = len(prompt_ids)
            for _ in range(max_tokens - 1):
                token_embed = self.embed_tokens[tokens[-1]][np.newaxis, np.newaxis, :]
                logits, pk, pv = self.decoder_step.run(
                    ["logits", "present_keys", "present_values"],
                    {"input_embeds": token_embed, "position_ids": np.array([[pos]], dtype=np.int64),
                     "past_keys": pk, "past_values": pv},
                )
                tok = int(np.argmax(logits[0, -1, :]))
                tokens.append(tok)
                pos += 1
                if tok in EOS_IDS:
                    break
        print(f"  [decode {time.time()-t0:.1f}s, {len(tokens)} tokens]", flush=True)

        # 去掉 prompt 部分（我们只解码生成 tokens），解码文本
        text = self.tokenizer.decode(tokens, skip_special_tokens=True).strip()
        # 清洗语言标记前缀（如 "language Chinese<asr_text>" 或 "language English"）
        text = re.sub(r"^language\s+\S+\s*<?asr_text>?", "", text).strip()
        text = text.replace("<asr_text>", "").strip()
        return text


if __name__ == "__main__":
    eng = QwenASREngine()
    result = eng.transcribe(sys.argv[1])
    print("\n==== 转写结果 ====")
    print(result)
