#!/usr/bin/env python3
"""Jetson test mode: launch every topic publisher in jetson/ at once.

Each jetson/<TOPIC>.py streams its own PX4/ROS2 packet over UDP to YAMCS_HOST:YAMCS_PORT
(read from the environment, set by entrypoint.py from config.json). Mirrors the jetson
repo's "run all publishers" testing style. Ctrl+C stops every publisher.
"""
import os
import signal
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SELF = Path(__file__).resolve().name


def main():
    # Topic publishers live alongside this launcher; exclude the launcher itself.
    scripts = sorted(p for p in HERE.glob("*.py") if p.name != SELF)
    if not scripts:
        print(f"No jetson publishers found in {HERE}", file=sys.stderr)
        sys.exit(1)

    host = os.environ.get("YAMCS_HOST", "127.0.0.1")
    port = os.environ.get("YAMCS_PORT", "40002")
    print(f"🚀 [Jetson] Launching {len(scripts)} topic publishers -> {host}:{port}")

    procs = []
    for s in scripts:
        p = subprocess.Popen([sys.executable, str(s)], env=os.environ.copy())
        procs.append((s.stem, p))
        print(f"   [start] {s.stem} (pid {p.pid})")

    def shutdown(*_):
        print("\n🛑 Stopping all jetson publishers...")
        for _, p in procs:
            p.terminate()
        for _, p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # If any publisher dies, surface it but keep the rest running.
    while True:
        for name, p in procs:
            ret = p.poll()
            if ret is not None:
                print(f"⚠️  publisher {name} exited (code {ret})")
        try:
            signal.pause()
        except AttributeError:
            # signal.pause() is unavailable on some platforms; fall back to wait.
            for _, p in procs:
                p.wait()
            break


if __name__ == "__main__":
    main()
