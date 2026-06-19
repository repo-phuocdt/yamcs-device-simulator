#!/usr/bin/env python3
import socket, struct, time, random

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 24  # VEHICLE_CONTROL_MODE

# Big-endian layout:
# I   : uint32  packet_id
# Q   : uint64  timestamp
# 13B : 13 x uint8 flags (bools encoded as 0/1)
# 3x  : 3 bytes padding (24 bits) at the end
PKT_STRUCT = struct.Struct(">IQ13B3x")
EXPECTED_LEN = 28  # bytes

def build_packet(packet_id: int, now_us: int) -> bytes:
    # Generate example flag values (toggle randomly each send)
    flags = [
        random.randint(0, 1),  # flag_armed
        random.randint(0, 1),  # flag_multicopter_position_control_enabled
        random.randint(0, 1),  # flag_control_manual_enabled
        random.randint(0, 1),  # flag_control_auto_enabled
        random.randint(0, 1),  # flag_control_offboard_enabled
        random.randint(0, 1),  # flag_control_rates_enabled
        random.randint(0, 1),  # flag_control_attitude_enabled
        random.randint(0, 1),  # flag_control_acceleration_enabled
        random.randint(0, 1),  # flag_control_velocity_enabled
        random.randint(0, 1),  # flag_control_position_enabled
        random.randint(0, 1),  # flag_control_altitude_enabled
        random.randint(0, 1),  # flag_control_climb_rate_enabled
        random.randint(0, 1),  # flag_control_termination_enabled
    ]

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        *flags,
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