#!/usr/bin/env python3
import socket
import struct
import time
import random

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 26  # SENSOR_MAG

# Big-endian layout (total 40 bytes):
# I   = uint32  (packet_id)
# Q   = uint64  (timestamp)
# Q   = uint64  (timestamp_sample)
# I   = uint32  (device_id)
# f   = float32 (x)
# f   = float32 (y)
# f   = float32 (z)
# f   = float32 (temperature)
# I   = uint32  (error_count)
PKT_STRUCT = struct.Struct(">IQQIffffI")


def build_packet(packet_id: int, now_us: int) -> bytes:
    # Simulate a recent sample time
    ts_sample = now_us - random.randint(500, 2500)

    # 32-bit device id
    device_id = 0xB4A00000 | (random.randint(0, 0xFFFF) & 0xFFFF)

    # Magnetic field components in Gauss
    x = random.uniform(-0.5, 0.5)
    y = random.uniform(-0.5, 0.5)
    z = random.uniform(-0.5, 0.5)

    # Temperature in deg C
    temperature = random.uniform(15.0, 35.0)

    # Error counter (bounded)
    error_count = random.randint(0, 10000)

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
    )
    assert len(pkt) == 44, f"len={len(pkt)} != 44"
    return pkt


def send_udp(buf: bytes, host=HOST, port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(buf, (host, port))
        print(f"Sent {len(buf)} bytes to {host}:{port} -> {buf.hex()}")


def main():
    while True:
        now_us = int(time.time() * 1_000_000)
        payload = build_packet(PACKET_ID, now_us)
        send_udp(payload)
        time.sleep(0.5)  # 2 Hz


if __name__ == "__main__":
    main()