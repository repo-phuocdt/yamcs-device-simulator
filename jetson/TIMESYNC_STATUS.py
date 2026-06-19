#!/usr/bin/env python3
import socket, struct, time, random

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 25  # TIMESYNC_STATUS

# Cấu trúc gói (BIG-ENDIAN):
# I    : uint32  packet_id
# Q    : uint64  timestamp
# B    : uint8   source_protocol
# 7x   : padding 56 bit (7 bytes)
# Q    : uint64  remote_timestamp
# q    : int64   observed_offset
# q    : int64   estimated_offset
# I    : uint32  round_trip_time
PKT_STRUCT = struct.Struct(">IQB7xQqqI")
EXPECTED_LEN = 48  # bytes

def build_packet(packet_id: int, now_us: int) -> bytes:
    # Chọn source_protocol: 0=UNKNOWN, 1=MAVLINK, 2=DDS (ví dụ)
    source_protocol = random.choice([0, 1, 2])

    # Giả lập remote_timestamp lệch một chút so với local
    remote_timestamp = now_us + random.randint(-50_000, 50_000)  # ±50 ms

    # Giả lập offset đo được và offset ước lượng (âm/dương, đơn vị microseconds)
    observed_offset = random.randint(-200_000, 200_000)   # ±200 ms
    # Làm mượt hơn một chút cho estimated_offset
    estimated_offset = int(observed_offset * random.uniform(0.5, 0.9))

    # Giả lập round-trip time (us)
    rtt_us = random.randint(500, 50_000)  # 0.5 ms .. 50 ms

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        int(source_protocol),
        int(remote_timestamp),
        int(observed_offset),
        int(estimated_offset),
        int(rtt_us),
    )
    assert len(pkt) == EXPECTED_LEN, f"len={len(pkt)} != {EXPECTED_LEN}"
    return pkt

def send_udp(buf: bytes, host=HOST, port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(buf, (host, port))
        print(f"Sent {len(buf)} bytes: {buf.hex()}")

def main():
    while True:
        now_us = int(time.time() * 1_000_000)
        payload = build_packet(PACKET_ID, now_us)
        send_udp(payload)
        time.sleep(1)

if __name__ == "__main__":
    main()