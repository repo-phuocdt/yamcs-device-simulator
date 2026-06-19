#!/usr/bin/env python3
import socket
import struct
import time
import random
import math

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 10  # INPUT_RC

# Packet layout (big-endian, no implicit padding by struct):
# uint32  packet_id
# uint64  timestamp
# uint64  timestamp_last_signal
# uint8   channel_count
# padding 24 bits (3 bytes)
# int32   rssi
# uint8   rc_failsafe
# uint8   rc_lost
# uint16  rc_lost_frame_count
# uint16  rc_total_frame_count
# uint16  rc_ppm_frame_length
# uint8   input_source
# padding 8 bits (1 byte)
# uint16[18] values
# int8    link_quality
# padding 8 bits (1 byte)
# float32 rssi_dbm
#
# Total size = 80 bytes
PKT_STRUCT = struct.Struct(
    ">I"     # packet_id
    "QQ"     # timestamp, timestamp_last_signal
    "B"      # channel_count
    "3x"     # padding 3 bytes
    "i"      # rssi
    "B"      # rc_failsafe (0/1)
    "B"      # rc_lost (0/1)
    "H"      # rc_lost_frame_count
    "H"      # rc_total_frame_count
    "H"      # rc_ppm_frame_length
    "B"      # input_source
    "x"      # padding 1 byte after input_source
    "18H"    # values[18]
    "b"      # link_quality (-1 or 0..100)
    "x"      # padding 1 byte after link_quality
    "f"      # rssi_dbm
)
assert PKT_STRUCT.size == 80, PKT_STRUCT.size


def build_packet(packet_id: int, now_us: int) -> bytes:
    # Simulate signal seen slightly earlier
    ts_last = now_us - random.randint(1_000, 50_000)

    # Channel count 0..18
    ch_count = random.randint(6, 18)

    # RSSI: -1 undefined, else 0..100
    rssi = random.choice([-1, random.randint(0, 100)])

    # Flags
    rc_failsafe = random.choice([0, 0, 0, 1])  # rarely 1
    rc_lost = 0 if rc_failsafe == 0 else 1

    # Frame counters & PPM length (for PPM systems; keep reasonable demo numbers)
    lost_frames = random.randint(0, 50) if rc_lost else random.randint(0, 5)
    total_frames = lost_frames + random.randint(100, 500)
    ppm_len = random.choice([0, 22500, 23000])  # 0 => non-PPM

    # input_source (mirror PX4 enum, pick a plausible value)
    input_source = random.choice([1, 4, 6, 14])  # PPM, SBUS, MAVLINK, CRSF

    # RC channel values (microseconds). Fill up to 18 with zeros if unused.
    values = []
    for i in range(18):
        if i < ch_count:
            if i == 2:
                # throttle-ish channel for demo (1000..2000)
                values.append(random.randint(1000, 2000))
            else:
                # other channels center around 1500 +/- 400
                values.append(max(1000, min(2000, 1500 + random.randint(-400, 400))))
        else:
            values.append(0)

    # Link quality: -1 invalid or 0..100
    link_quality = random.choice([-1, random.randint(0, 100)])

    # RSSI in dBm (typical -100..-30)
    rssi_dbm = random.uniform(-98.0, -35.0)

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        int(ts_last),
        int(ch_count),
        int(rssi),
        int(rc_failsafe),
        int(rc_lost),
        int(lost_frames) & 0xFFFF,
        int(total_frames) & 0xFFFF,
        int(ppm_len) & 0xFFFF,
        int(input_source) & 0xFF,
        *[int(v) & 0xFFFF for v in values],
        int(link_quality),
        float(rssi_dbm),
    )
    assert len(pkt) == 80, f"len={len(pkt)} != 80"
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