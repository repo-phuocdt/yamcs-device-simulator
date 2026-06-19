#!/usr/bin/env python3
import socket
import struct
import time
import random

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 9  # SENSOR_ACCEL

# Big-endian layout:
# I   = uint32  (packet_id)
# Q   = uint64  (timestamp)
# Q   = uint64  (timestamp_sample)
# I   = uint32  (device_id)
# fff = 3 x float32 (x, y, z)
# f   = float32 (temperature)
# I   = uint32  (error_count)
# 3B  = 3 x uint8 (clip_counter[0..2])
# B   = uint8  (samples)
#
# Total = 4 + 8 + 8 + 4 + 12 + 4 + 4 + 3 + 1 = 48 bytes
PKT_STRUCT = struct.Struct(">IQQIffffI3BB")


def build_packet(packet_id: int, now_us: int, seq: int = 0) -> bytes:
    # Simulate a recent sample time
    ts_sample = now_us - random.randint(500, 2500)

    # Fake device id (stick to 32-bit range)
    device_id = 0xAABBCC00 | (random.randint(0, 255) & 0xFF)

    # Angular rates (rad/s) in a reasonable MC range
    x = random.uniform(-5.0, 5.0)
    y = random.uniform(-5.0, 5.0)
    z = random.uniform(-5.0, 5.0)

    # Temperature in deg C
    temperature = random.uniform(20.0, 55.0)

    # Error counter (bounded)
    error_count = random.randint(0, 10_000)

    # Clip counters (per axis) 0..10
    clip_x = random.randint(0, 10)
    clip_y = random.randint(0, 10)
    clip_z = random.randint(0, 10)

    # Number of raw samples aggregated in this message
    samples = random.randint(1, 8)

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        int(ts_sample),
        int(device_id),
        float(x),
        float(y),
        float(z),
        float(temperature),
        int(error_count),
        int(clip_x),
        int(clip_y),
        int(clip_z),
        int(samples),
    )
    assert len(pkt) == 48, f"len={len(pkt)} != 48"
    return pkt


def send_udp(buf: bytes, host=HOST, port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(buf, (host, port))
        print(f"Sent {len(buf)} bytes to {host}:{port} -> {buf.hex()}")


def main():
    seq = 0
    while True:
        now_us = int(time.time() * 1_000_000)
        payload = build_packet(PACKET_ID, now_us, seq)
        send_udp(payload)
        seq += 1
        time.sleep(0.5)  # 2 Hz


if __name__ == "__main__":
    main()