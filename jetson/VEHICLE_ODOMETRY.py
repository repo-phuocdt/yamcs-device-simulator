#!/usr/bin/env python3
import socket
import struct
import time
import random
import math

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 17  # VEHICLE_ODOMETRY

# Total = 120 bytes (960 bits) with padding:
# - +3 pad bytes after pose_frame
# - +3 pad bytes after velocity_frame
# - +2 pad bytes at the end to round up to 120 bytes
PKT_STRUCT = struct.Struct(
    ">IQQ"      # packet_id, timestamp, timestamp_sample
    "B3x"       # pose_frame + 3 bytes padding
    "fff"       # position[3]
    "ffff"      # q[4]
    "B3x"       # velocity_frame + 3 bytes padding
    "fff"       # velocity[3]
    "fff"       # angular_velocity[3]
    "fff"       # position_variance[3]
    "fff"       # orientation_variance[3]
    "fff"       # velocity_variance[3]
    "B"         # reset_counter
    "b"         # quality (int8)
    "2x"        # 2 bytes padding at end -> 120 bytes total
)
assert PKT_STRUCT.size == 120, PKT_STRUCT.size


def build_packet(packet_id: int, now_us: int, seq: int = 0) -> bytes:
    # Simulate a recent sample time
    ts_sample = now_us - random.randint(500, 2500)

    # Pose frame: 0=UNKNOWN, 1=NED, 2=FRD
    pose_frame = random.choice((0, 1, 2))

    # Position in meters (local NED). Keep in a small cube around origin.
    px, py, pz = (random.uniform(-50.0, 50.0),
                  random.uniform(-50.0, 50.0),
                  random.uniform(-20.0, 0.0))

    # Quaternion q (w, x, y, z), normalized
    # Generate a small random yaw-only quaternion for simplicity
    yaw = random.uniform(-math.pi, math.pi)
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    qw, qx, qy, qz = cy, 0.0, 0.0, sy

    # Velocity frame: 0=UNKNOWN, 1=NED, 2=FRD, 3=BODY_FRD
    velocity_frame = random.choice((1, 3))

    # Linear velocity (m/s)
    vx, vy, vz = (random.uniform(-5.0, 5.0),
                  random.uniform(-5.0, 5.0),
                  random.uniform(-3.0, 3.0))

    # Angular velocity (rad/s)
    wx, wy, wz = (random.uniform(-2.0, 2.0),
                  random.uniform(-2.0, 2.0),
                  random.uniform(-2.0, 2.0))

    # Variances (sigma^2), keep positive small numbers
    pvx, pvy, pvz = (random.uniform(0.001, 0.5),
                     random.uniform(0.001, 0.5),
                     random.uniform(0.001, 0.5))
    ovx, ovy, ovz = (random.uniform(1e-4, 1e-2),
                     random.uniform(1e-4, 1e-2),
                     random.uniform(1e-4, 1e-2))
    vvx, vvy, vvz = (random.uniform(1e-4, 1e-2),
                     random.uniform(1e-4, 1e-2),
                     random.uniform(1e-4, 1e-2))

    # Counters / quality
    reset_counter = random.randint(0, 255)
    quality = random.randint(-1, 100)  # -1 unknown, else 0..100

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        int(ts_sample),
        int(pose_frame),
        float(px), float(py), float(pz),
        float(qw), float(qx), float(qy), float(qz),
        int(velocity_frame),
        float(vx), float(vy), float(vz),
        float(wx), float(wy), float(wz),
        float(pvx), float(pvy), float(pvz),
        float(ovx), float(ovy), float(ovz),
        float(vvx), float(vvy), float(vvz),
        int(reset_counter),
        int(quality),
    )
    assert len(pkt) == 120, f"len={len(pkt)} != 120"
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