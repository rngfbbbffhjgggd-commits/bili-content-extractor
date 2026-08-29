"""Resumable downloader for HuggingFace model files (urllib + Range retry)."""
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def download(url, dest, chunk=262144, max_retries=500):
    """Download with Range-based resume on connection breaks."""
    tmp = dest + ".part"
    done = os.path.getsize(tmp) if os.path.exists(tmp) else 0
    total = None
    for attempt in range(max_retries):
        headers = {"User-Agent": UA}
        if done:
            headers["Range"] = f"bytes={done}-"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                if total is None:
                    total = int(r.headers.get("Content-Length") or 0) + done
                with open(tmp, "ab") as f:
                    while True:
                        try:
                            c = r.read(chunk)
                        except Exception:
                            print(f"\n  [break at {done}, retry {attempt+1}]", flush=True)
                            break
                        if not c:
                            break
                        f.write(c)
                        done += len(c)
                        if total:
                            print(f"\r  {done*100//total}% ({done}/{total})", end="", flush=True)
                if done >= total:
                    os.replace(tmp, dest)
                    print(f"\n  saved {dest} ({done} bytes)")
                    return True
        except Exception as e:
            print(f"\n  [err {type(e).__name__} at {done}, retry {attempt+1}]", flush=True)
            time.sleep(1)
    print(f"\n  FAILED after retries, partial at {done}")
    return False


if __name__ == "__main__":
    base = sys.argv[1]          # e.g. https://hf-mirror.com/Systran/faster-whisper-base/resolve/main
    outdir = sys.argv[2]        # e.g. models/faster-whisper-base
    os.makedirs(outdir, exist_ok=True)
    files = sys.argv[3].split(",")  # e.g. config.json,model.bin,tokenizer.json,vocabulary.txt
    for f in files:
        dest = os.path.join(outdir, f)
        if os.path.exists(dest):
            print(f"exists: {f}")
            continue
        print(f"downloading {f} ...", flush=True)
        download(f"{base}/{f}", dest)
