#!/usr/bin/env python3
import socket
import struct
import time
import random
import math

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 12  # DISTANCE_SENSOR

# Layout (BIG-ENDIAN):
# uint32  packet_id                 (4)
# uint64  timestamp                 (8)
# uint32  device_id                 (4)
# float32 min_distance              (4)
# float32 max_distance              (4)
# float32 current_distance          (4)
# float32 variance                  (4)
# int8    signal_quality            (1)
# uint8   type                      (1)
# pad[2]                            (2)  <-- explicit padding added here
# float32 h_fov                     (4)
# float32 v_fov                     (4)
# float32 q[4]                      (16)
# uint8   orientation               (1)
# pad[3]                            (3)  <-- explicit padding
# TOTAL = 64 bytes (512 bits)
PKT_STRUCT = struct.Struct(
    ">IQIffffbBxxff4fBxxx"
)
assert PKT_STRUCT.size == 64, PKT_STRUCT.size


def random_unit_quaternion():
    """Return a random unit quaternion (w,x,y,z)."""
    # Shoemake method
    u1 = random.random()
    u2 = random.random() * 2.0 * math.pi
    u3 = random.random() * 2.0 * math.pi
    s1 = math.sqrt(1 - u1)
    s2 = math.sqrt(u1)
    w = s2 * math.cos(u2)
    x = s1 * math.sin(u3)
    y = s1 * math.cos(u3)
    z = s2 * math.sin(u2)
    return (w, x, y, z)


def build_packet(packet_id: int, now_us: int) -> bytes:
    # Distances in meters
    min_d = round(random.uniform(0.2, 0.5), 2)
    max_d = round(random.uniform(5.0, 15.0), 1)
    cur_d = round(random.uniform(min_d, max_d), 2)

    # Small variance (m^2)
    variance = round(random.uniform(0.0001, 0.02), 5)

    # Signal quality (-1 unknown, else 0..100)
    if random.random() < 0.05:
        sig_q = -1
    else:
        sig_q = random.randint(0, 100)

    # Type (MAV_DISTANCE_SENSOR_*): 0..3
    sensor_type = random.choice([0, 1, 2, 3])

    # Field of view (rad)
    h_fov = round(random.uniform(0.2, 1.2), 3)
    v_fov = round(random.uniform(0.2, 1.2), 3)

    # Orientation quaternion (w,x,y,z)
    qw, qx, qy, qz = random_unit_quaternion()

    # Orientation enum (e.g. 0..7)
    orientation = random.randint(0, 7)

    device_id = 0x44495354  # 'DIST'

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        int(device_id) & 0xFFFFFFFF,
        float(min_d), float(max_d), float(cur_d), float(variance),
        int(sig_q),
        int(sensor_type),
        # two pad bytes automatically added by 'xx'
        float(h_fov), float(v_fov),
        float(qw), float(qx), float(qy), float(qz),
        int(orientation) & 0xFF,
        # 'xxx' pads 3 zero bytes automatically
    )
    assert len(pkt) == 64
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