#!/usr/bin/env python3
import socket
import struct
import time
import random

"""
COLLISION_CONSTRAINTS packet sender (BIG-ENDIAN), no separate header.

Layout (bytes), matching MDB:
  uint32  packet_id            (4)
  uint64  timestamp_us         (8)
  float32[2] original_setpoint (8)  # vx, vy (m/s)
  float32[2] adapted_setpoint  (8)  # vx, vy (m/s)

Total = 4 + 8 + 8 + 8 = 28 bytes (224 bits)
"""

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 30 # COLLISION_CONSTRAINTS
# Big-endian packet struct
PKT_STRUCT = struct.Struct(">IQffff")  # I(4) Q(8) 4×f(16) = 28 bytes

def build_packet(packet_id: int, now_us: int) -> bytes:
    # Tạo original_setpoint ngẫu nhiên trong khoảng [-3, 3] m/s
    orig_vx = round(random.uniform(-3.0, 3.0), 2)
    orig_vy = round(random.uniform(-3.0, 3.0), 2)

    def clamp(v, lo, hi): 
        return lo if v < lo else hi if v > hi else v
    adap_vx = clamp(orig_vx, -1.5, 1.5)
    adap_vy = clamp(orig_vy, -1.5, 1.5)

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        float(orig_vx), float(orig_vy),
        float(adap_vx), float(adap_vy),
    )
    assert len(pkt) == 28, f"Packed length {len(pkt)} != 28 bytes"
    return pkt

def send_udp(buf: bytes, host: str = HOST, port: int = PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(buf, (host, port))
        print(f"Sent {len(buf)} bytes to {host}:{port}")
    finally:
        sock.close()

def main():
    while True:
        now_us = int(time.time() * 1_000_000)
        pkt = build_packet(PACKET_ID, now_us)
        print(f"HEX (packet_id={PACKET_ID}): {pkt.hex()}")
        send_udp(pkt)
        time.sleep(1)

if __name__ == "__main__":
    main()