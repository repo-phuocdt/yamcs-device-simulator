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
PACKET_ID = 31 # VEHICLE_TRAJECTORY_WAYPOINT_DESIRED

# ============================
# Container: VEHICLE_TRAJECTORY_WAYPOINT_DESIRED
# Layout:
#   uint32  packet_id                      (4B)
#   uint64  timestamp_us                   (8B)
#   uint8   type                           (1B)   # MAV_TRAJECTORY_REPRESENTATION enum
#   TrajectoryWaypoint[5] waypoints (5 x 56B = 280B)
# Total packet: 4 + 8 + 1 + 3 + 280 = 296 bytes
# ============================

# ---- TrajectoryWaypoint struct (448 bit = 56 bytes) ----
# Fields:
#   uint64   timestamp
#   float32[3] position
#   float32[3] velocity
#   float32[3] acceleration
#   float32   yaw
#   float32   yaw_speed
#   uint8     point_valid           # boolean as 0/1
#   uint8     type
#   + 24-bit padding to reach 56 bytes
WP_STRUCT = struct.Struct(
    ">"          # big-endian
    "Q"          # timestamp (uint64)
    + "fff"      # position x,y,z
    + "fff"      # velocity x,y,z
    + "fff"      # acceleration x,y,z
    + "f"        # yaw
    + "f"        # yaw_speed
    + "B"        # point_valid (uint8)
    + "B"        # type (uint8)
    + "2x"       # 16-bit padding
)

# Header: packet_id (u32), timestamp_us (u64), type (u8)
HDR_STRUCT = struct.Struct(">IQB3x")  # + 24-bit padding to align to 8 bytes

def rand_float(a, b):
    return random.uniform(a, b)

def make_waypoint(now_us: int, idx: int) -> bytes:
    """
    Create one TrajectoryWaypoint (56 bytes).
    Varies values a bit by index for easy visual checks.
    """
    timestamp = (now_us + idx * 20_000) & 0xFFFFFFFFFFFFFFFF  # spaced by 20 ms

    # Position in meters (x,y,z)
    px = rand_float(-50, 50)
    py = rand_float(-50, 50)
    pz = rand_float(-20, 5)

    # Velocity m/s
    vx = rand_float(-5, 5)
    vy = rand_float(-5, 5)
    vz = rand_float(-3, 3)

    # Acceleration m/s^2
    ax = rand_float(-2, 2)
    ay = rand_float(-2, 2)
    az = rand_float(-2, 2)

    # Yaw and yaw rate
    yaw = rand_float(-math.pi, math.pi)
    yaw_speed = rand_float(-1.0, 1.0)

    point_valid = 1 if random.random() > 0.1 else 0
    wp_type = idx  # 0..4 for demo

    return WP_STRUCT.pack(
        int(timestamp),
        float(px), float(py), float(pz),
        float(vx), float(vy), float(vz),
        float(ax), float(ay), float(az),
        float(yaw),
        float(yaw_speed),
        int(point_valid) & 0xFF,
        int(wp_type) & 0xFF
    )

def build_packet(packet_id: int, now_us: int, traj_type: int = 0) -> bytes:
    """
    Build VEHICLE_TRAJECTORY_WAYPOINT_DESIRED packet (296 bytes).
    """
    header = HDR_STRUCT.pack(
        int(packet_id) & 0xFFFFFFFF,
        int(now_us) & 0xFFFFFFFFFFFFFFFF,
        int(traj_type) & 0xFF
    )

    wps = b"".join(make_waypoint(now_us, i) for i in range(5))
    pkt = header + wps
    return pkt

def send_udp(buf: bytes, host=HOST, port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(buf, (host, port))
        print(f"Sent {len(buf)} bytes to {host}:{port}")

def main():
    try:
        while True:
            now_us = int(time.time() * 1_000_000)
            pkt = build_packet(PACKET_ID, now_us, traj_type=0)  # 0 == MAV_TRAJECTORY_REPRESENTATION_WAYPOINTS
            # Sanity check size
            assert len(pkt) == 296, f"Unexpected packet size: {len(pkt)}"
            send_udp(pkt)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Stopped.")

if __name__ == "__main__":
    main()