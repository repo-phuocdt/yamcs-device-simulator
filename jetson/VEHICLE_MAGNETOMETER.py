#!/usr/bin/env python3
import socket
import struct
import time
import random

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 23  # VEHICLE_MAGNETOMETER

# Layout (BIG-ENDIAN):
# uint32  packet_id                (4)
# uint64  timestamp                (8)
# uint64  timestamp_sample         (8)
# uint32  device_id                (4)
# float32[3] magnetometer_ga       (12)
# uint8   calibration_count        (1)
# pad[3]                           (3)  <-- explicit padding
# TOTAL = 40 bytes (320 bits)
PKT_STRUCT = struct.Struct(">IQQI3fBxxx")
assert PKT_STRUCT.size == 40, PKT_STRUCT.size


def build_packet(packet_id: int, now_us: int) -> bytes:
    ts_sample = now_us - random.randint(500, 2_000)

    # 32-bit device id (ví dụ: 'MAG\x10' -> 0x4D414710)
    device_id = 0x4D414710

    # Từ trường (Gauss) trong khung FRD; biên độ cỡ trái đất ~0.25..0.65 G
    mx = random.uniform(-0.8, 0.8)
    my = random.uniform(-0.8, 0.8)
    mz = random.uniform(-0.8, 0.8)

    calib_cnt = random.randint(0, 20)

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        int(ts_sample),
        int(device_id) & 0xFFFFFFFF,
        float(mx), float(my), float(mz),
        int(calib_cnt) & 0xFF,
        # 'xxx' pads 3 zero bytes automatically
    )
    assert len(pkt) == 40
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