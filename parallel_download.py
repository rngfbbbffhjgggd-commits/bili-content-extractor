"""parallel_download.py — 分片并行下载（专治单连接限速/频繁断流）

用法:
  python parallel_download.py <URL> <保存路径> [并发数] [分片大小MB]

特性: 并发 Range 分片下载，每片断流自动原地续传，可反复运行续传。
"""
import os
import queue
import sys
import threading
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def get_total(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers.get("Content-Length") or 0)


def fetch_piece(url, tmp, start, end, lock, progress, total):
    """下载 [start, end) 段；断流则原地续传直至完成。"""
    written = start
    while written < end:
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Range": f"bytes={written}-{end - 1}"}
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                if r.status != 206:
                    # 服务器忽略 Range 返回全文件 -> 丢弃本次连接，避免错位
                    raise ValueError(f"expected 206, got {r.status}")
                with open(tmp, "r+b") as f:
                    f.seek(written)
                    while written < end:
                        try:
                            c = r.read(262144)
                        except Exception:
                            break
                        if not c:
                            break
                        f.write(c)
                        written += len(c)
                        with lock:
                            progress[0] += len(c)
        except Exception:
            pass


def main():
    url, dest = sys.argv[1], sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    piece_mb = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0

    tmp = dest + ".part"
    total = get_total(url)
    exist = os.path.getsize(tmp) if os.path.exists(tmp) else 0
    print(f"total {total} bytes, existing {exist}, workers {workers}", flush=True)

    if exist == 0:
        with open(tmp, "wb") as f:
            f.truncate(total)
    elif exist < total:
        pass

    piece = int(piece_mb * 1048576)
    ranges = [(s, min(s + piece, total)) for s in range(0, total, piece)]

    def piece_done(path, s, e):
        """已完成的分片开头应有真实数据（truncate/空洞为 0）"""
        with open(path, "rb") as f:
            f.seek(s)
            sample = f.read(min(16384, e - s))
            return any(b != 0 for b in sample)

    todo = [(s, e) for s, e in ranges if not piece_done(tmp, s, e)]
    if not todo:
        os.replace(tmp, dest)
        print(f"already complete -> {dest}", flush=True)
        return

    print(f"pieces todo: {len(todo)}", flush=True)
    q = queue.Queue()
    for s, e in todo:
        q.put((s, e))
    progress = [exist]
    lock = threading.Lock()
    t0 = time.time()

    def worker():
        while True:
            try:
                s, e = q.get_nowait()
            except queue.Empty:
                return
            fetch_piece(url, tmp, s, e, lock, progress, total)
            with lock:
                done = progress[0]
            if done // 4194304 != (done - 4194304) // 4194304 and done > 0:
                rate = done / max(time.time() - t0, 0.1) / 1024
                print(f"\r  {done*100//total}% ({done}/{total}) @ {rate:.0f} KB/s", end="", flush=True)
            q.task_done()

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final = os.path.getsize(tmp)
    if final >= total:
        os.replace(tmp, dest)
        print(f"\n  COMPLETE -> {dest} ({final} bytes)", flush=True)
    else:
        print(f"\n  partial {final}/{total} (再运行一次继续)", flush=True)


if __name__ == "__main__":
    main()
