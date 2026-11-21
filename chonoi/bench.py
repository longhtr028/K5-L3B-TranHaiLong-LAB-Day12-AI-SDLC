"""Đo từng khung Canvas từ cảnh Gather thật trong Chrome/Chromium."""

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time

from .contract import load_contract
from .live import LiveGame, LiveServer, _Handler


def browser_binary():
    candidates = [os.environ.get("CHONOI_BROWSER"), shutil.which("chromium"), shutil.which("chromium-browser"),
                  shutil.which("google-chrome"), shutil.which("google-chrome-stable"),
                  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    return next((path for path in candidates if path and os.access(path, os.X_OK)), None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--duration", required=True, type=float)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if not math.isfinite(args.duration) or args.duration <= 0:
        parser.error("duration phải dương và hữu hạn")
    browser = browser_binary()
    if not browser:
        parser.error("cần Chrome/Chromium hoặc CHONOI_BROWSER trỏ tới trình duyệt")

    ready = threading.Event()
    result = {}
    launched = 0.0

    class BenchHandler(_Handler):
        def do_POST(self):
            if self.path == "/bench/frame":
                result["load_ms"] = (time.perf_counter() - launched) * 1000
            elif self.path == "/bench/result":
                size = int(self.headers["Content-Length"])
                result.update(json.loads(self.rfile.read(size)))
                ready.set()
            else:
                return super().do_POST()
            self._send(200, b'{}')

    tuning = load_contract()["tuning"]
    server = LiveServer(LiveGame("gather", tuning, {}, args.seed), port=0, handler_class=BenchHandler)
    server.start()
    try:
        with tempfile.TemporaryDirectory(prefix="chonoi-browser-") as profile:
            launched = time.perf_counter()
            command = [browser, "--headless=new", f"--user-data-dir={profile}", "--window-size=1280,720",
                       "--force-device-scale-factor=1", "--disable-background-timer-throttling",
                       "--no-first-run", "--disable-default-apps", "--disable-renderer-backgrounding",
                       f"{server.url}?bench={args.duration}"]
            if hasattr(os, "geteuid") and os.geteuid() == 0:
                # Chrom(e|ium) yêu cầu tài khoản không phải root. Giữ sandbox mặc định.
                parser.error("chạy benchmark bằng tài khoản người dùng thông thường")
            with subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as process:
                try:
                    if not ready.wait(args.duration + 20):
                        parser.exit(1, "Không nhận được dữ liệu render từ Chrome/Chromium.\n")
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
    finally:
        server.stop()
    fields = ("avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms")
    args.out.write_text(json.dumps({k: result[k] for k in fields}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
