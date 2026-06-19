#!/usr/bin/env python3
import socket
import struct
import time
import random
import math

# ============================
# UDP target
# ============================
import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 27  # POSITION_SETPOINT_TRIPLET

# ============================
# Container: POSITION_SETPOINT_TRIPLET
# Layout:
#   uint32 packet_id
#   uint64 timestamp_us
#   PositionSetpoint previous (88B)
#   PositionSetpoint current  (88B)
#   PositionSetpoint next     (88B)
# Total packet: 4 + 8 + 3*88 = 276 bytes
# ============================

# ---- PositionSetpoint struct (704 bit = 88 bytes) ----
# Fields & paddings as specified. Total size = 88 bytes (no trailing pad).
POS_SP_STRUCT = struct.Struct(
    ">"      # big-endian
    "Q"      # timestamp (uint64)
    "B"      # valid (uint8)
    "B"      # type  (uint8)
    "2x"     # type: +16-bit padding
    "fff"    # vx, vy, vz (float32)
    "dd"     # lat, lon (float64)
    "f"      # alt (float32)
    "f"      # yaw (float32)
    "B"      # yaw_valid (uint8)
    "3x"     # yaw_valid: +24-bit padding
    "f"      # yawspeed (float32)
    "B"      # yawspeed_valid (uint8)
    "3x"     # yawspeed_valid: +24-bit padding
    "f"      # loiter_radius (float32)
    "B"      # loiter_direction_counter_clockwise (uint8)
    "3x"     # loiter_dir: +24-bit padding
    "f"      # acceptance_radius (float32)
    "f"      # cruising_speed (float32)
    "B"      # gliding_enabled (uint8)
    "3x"     # gliding_enabled: +24-bit padding
    "f"      # cruising_throttle (float32)
    "B"      # disable_weather_vane (uint8)
    "3x"     # disable_weather_vane: +24-bit padding
) 

HDR_STRUCT = struct.Struct(">IQ")  # packet_id (u32), timestamp_us (u64)

def rand_float(a, b):
    return random.uniform(a, b)

def rand_latlon():
    # Generate a plausible lat/lon
    lat = rand_float(-60.0, 60.0)
    lon = rand_float(-150.0, 150.0)
    return lat, lon

def build_pos_sp(ts_us: int) -> bytes:
    # Random but "nice" demo data
    valid = 1
    sp_type = random.randint(0, 5)  # demo

    vx, vy, vz = (rand_float(-5, 5), rand_float(-5, 5), rand_float(-3, 3))
    lat, lon = rand_latlon()
    alt = rand_float(0, 2000)

    # yaw in [-pi, pi)
    yaw = rand_float(-math.pi, math.pi)
    yaw_valid = 1

    yawspeed = rand_float(-1.0, 1.0)
    yawspeed_valid = 1

    loiter_radius = rand_float(5.0, 80.0)
    loiter_ccw = random.randint(0, 1)

    acceptance_radius = rand_float(0.5, 5.0)
    cruising_speed = rand_float(5.0, 20.0)
    gliding_enabled = random.randint(0, 1)

    cruising_throttle = rand_float(0.0, 1.0)
    disable_weather_vane = random.randint(0, 1)

    return POS_SP_STRUCT.pack(
        int(ts_us) & 0xFFFFFFFFFFFFFFFF,
        int(valid) & 0xFF,
        int(sp_type) & 0xFF,
        float(vx), float(vy), float(vz),
        float(lat), float(lon),
        float(alt),
        float(yaw),
        int(yaw_valid) & 0xFF,
        float(yawspeed),
        int(yawspeed_valid) & 0xFF,
        float(loiter_radius),
        int(loiter_ccw) & 0xFF,
        float(acceptance_radius),
        float(cruising_speed),
        int(gliding_enabled) & 0xFF,
        float(cruising_throttle),
        int(disable_weather_vane) & 0xFF,
    )

def build_packet(packet_id: int, now_us: int) -> bytes:
    prev_sp = build_pos_sp(now_us - 100_000)  # 0.1s before
    curr_sp = build_pos_sp(now_us)
    next_sp = build_pos_sp(now_us + 100_000)  # 0.1s after

    header = HDR_STRUCT.pack(int(packet_id) & 0xFFFFFFFF, int(now_us) & 0xFFFFFFFFFFFFFFFF)
    return header + prev_sp + curr_sp + next_sp  # 276 bytes total

def send_udp(buf: bytes, host=HOST, port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(buf, (host, port))
        print(f"Sent {len(buf)} bytes to {host}:{port}")

def main():
    try:
        while True:
            now_us = int(time.time() * 1_000_000)
            pkt = build_packet(PACKET_ID, now_us)
            # Sanity check sizes
            assert len(pkt) == 276, f"Unexpected packet size: {len(pkt)}"
            send_udp(pkt)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Stopped.")

if __name__ == "__main__":
    main()