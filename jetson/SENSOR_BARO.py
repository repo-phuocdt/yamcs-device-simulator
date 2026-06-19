#!/usr/bin/env python3
import socket
import struct
import time
import random

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 21  # SENSOR_BARO

# Big-endian layout (total 36 bytes):
# I   = uint32  (packet_id)
# Q   = uint64  (timestamp)
# Q   = uint64  (timestamp_sample)
# I   = uint32  (device_id)
# f   = float32 (pressure)
# f   = float32 (temperature)
# I   = uint32  (error_count)
PKT_STRUCT = struct.Struct(">IQQIffI")


def build_packet(packet_id: int, now_us: int) -> bytes:
    # Simulate a recent sample time
    ts_sample = now_us - random.randint(500, 2500)

    # 32-bit device id
    device_id = 0xB4A00000 | (random.randint(0, 0xFFFF) & 0xFFFF)

    # Pressure in Pascals (around sea-level with some noise)
    pressure = random.uniform(98000.0, 103000.0)

    # Temperature in deg C
    temperature = random.uniform(15.0, 35.0)

    # Error counter (bounded)
    error_count = random.randint(0, 10000)

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        int(ts_sample),
        int(device_id),
        float(pressure),
        float(temperature),
        int(error_count),
    )
    assert len(pkt) == 36, f"len={len(pkt)} != 36"
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