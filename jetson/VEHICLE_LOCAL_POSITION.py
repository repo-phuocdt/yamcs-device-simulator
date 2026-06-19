#!/usr/bin/env python3
import socket
import struct
import time
import random
import math

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 18  # VEHICLE_LOCAL_POSITION

# Big-endian packet layout with required paddings:
# uint32  packet_id
# uint64  timestamp
# uint64  timestamp_sample
#
# uint8   xy_valid
# uint8   z_valid
# uint8   v_xy_valid
# uint8   v_z_valid
#
# float32 x
# float32 y
# float32 z
#
# float32 delta_xy[2]
# uint8   xy_reset_counter + pad[3]
#
# float32 delta_z
# uint8   z_reset_counter + pad[3]
#
# float32 vx
# float32 vy
# float32 vz
# float32 z_deriv
#
# float32 delta_vxy[2]
# uint8   vxy_reset_counter + pad[3]
#
# float32 delta_vz
# uint8   vz_reset_counter + pad[3]
#
# float32 ax, ay, az
#
# float32 heading
# float32 delta_heading
# uint8   heading_reset_counter
# uint8   heading_good_for_control
# pad[2]
#
# uint8   xy_global
# uint8   z_global
# uint64  ref_timestamp
# float64 ref_lat
# float64 ref_lon
# float32 ref_alt
#
# float32 dist_bottom
# uint8   dist_bottom_valid
# uint8   dist_bottom_sensor_bitfield + pad[2]
# float32 eph
# float32 epv
# float32 evh
# float32 evv
#
# uint8   dead_reckoning + pad[3]
#
# float32 vxy_max
# float32 vz_max
# float32 hagl_min
# float32 hagl_max
#
# NOTE: All booleans are encoded as 1-byte (0/1) unsigned values.
PKT_STRUCT = struct.Struct(
    ">"
    "I"       # packet_id
    "QQ"      # timestamp, timestamp_sample
    "4B"      # xy_valid, z_valid, v_xy_valid, v_z_valid
    "3f"      # x, y, z
    "2f"      # delta_xy[2]
    "Bxxx"    # xy_reset_counter + pad[3]
    "f"       # delta_z
    "Bxxx"    # z_reset_counter + pad[3]
    "4f"      # vx, vy, vz, z_deriv
    "2f"      # delta_vxy[2]
    "Bxxx"    # vxy_reset_counter + pad[3]
    "f"       # delta_vz
    "Bxxx"    # vz_reset_counter + pad[3]
    "3f"      # ax, ay, az
    "f"       # heading
    "f"       # delta_heading
    "BBBB"    # heading_reset_counter, heading_good_for_control, xy_global, z_global
    "Q"       # ref_timestamp
    "2d"      # ref_lat, ref_lon
    "f"       # ref_alt
    "f"       # dist_bottom
    "B"       # dist_bottom_valid
    "Bxx"     # dist_bottom_sensor_bitfield + pad[2]
    "f"       # eph
    "3f"      # epv, evh, evv
    "Bxxx"    # dead_reckoning + pad[3]
    "4f"      # vxy_max, vz_max, hagl_min, hagl_max
)

def build_packet(packet_id: int, now_us: int) -> bytes:
    # Validity flags (random realistic toggles)
    xy_valid = 1
    z_valid = 1
    v_xy_valid = 1
    v_z_valid = 1

    # Local NED position (m)
    x = round(random.uniform(-50.0, 50.0), 3)
    y = round(random.uniform(-50.0, 50.0), 3)
    z = round(random.uniform(-5.0, -0.5), 3)  # down positive

    # Reset deltas
    delta_xy = (round(random.uniform(-0.05, 0.05), 4),
                round(random.uniform(-0.05, 0.05), 4))
    xy_reset_counter = random.randint(0, 200)

    delta_z = round(random.uniform(-0.05, 0.05), 4)
    z_reset_counter = random.randint(0, 200)

    # Velocities (m/s)
    vx = round(random.uniform(-5.0, 5.0), 3)
    vy = round(random.uniform(-5.0, 5.0), 3)
    vz = round(random.uniform(-2.0, 2.0), 3)
    z_deriv = vz  # often equal to vz

    # Velocity reset deltas
    delta_vxy = (round(random.uniform(-0.1, 0.1), 4),
                 round(random.uniform(-0.1, 0.1), 4))
    vxy_reset_counter = random.randint(0, 200)

    delta_vz = round(random.uniform(-0.1, 0.1), 4)
    vz_reset_counter = random.randint(0, 200)

    # Accelerations (m/s^2)
    ax = round(random.uniform(-2.0, 2.0), 3)
    ay = round(random.uniform(-2.0, 2.0), 3)
    az = round(random.uniform(-2.0, 2.0), 3)

    # Heading (rad) and delta
    heading = round(random.uniform(-math.pi, math.pi), 5)
    delta_heading = round(random.uniform(-0.01, 0.01), 6)
    heading_reset_counter = random.randint(0, 50)
    heading_good_for_control = 1 if random.random() > 0.05 else 0

    # Global reference present?
    xy_global = 1
    z_global = 1
    ref_timestamp = now_us - random.randint(100_000, 2_000_000)
    # Random lat/lon near HCMC to look realistic
    ref_lat = 10.77 + random.uniform(-0.01, 0.01)
    ref_lon = 106.69 + random.uniform(-0.01, 0.01)
    ref_alt = round(random.uniform(0.0, 50.0), 2)

    # Bottom distance and quality
    dist_bottom = round(abs(z) + random.uniform(-0.2, 0.2), 3)
    dist_bottom_valid = 1
    dist_bottom_sensor_bitfield = random.choice([1, 2, 3])  # RANGE, FLOW, both

    # Estimator covariance-ish
    eph = round(random.uniform(0.01, 0.5), 3)
    epv = round(random.uniform(0.01, 0.7), 3)
    evh = round(random.uniform(0.01, 0.5), 3)
    evv = round(random.uniform(0.01, 0.7), 3)

    # Dead-reckoning flag (with padding later)
    dead_reckoning = 0 if random.random() > 0.2 else 1

    # Limits
    vxy_max = 10.0
    vz_max = 3.0
    hagl_min = 1.0
    hagl_max = 120.0

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        int(now_us - random.randint(0, 20_000)),  # timestamp_sample slightly earlier
        int(xy_valid), int(z_valid), int(v_xy_valid), int(v_z_valid),
        float(x), float(y), float(z),
        float(delta_xy[0]), float(delta_xy[1]),
        int(xy_reset_counter),
        float(delta_z),
        int(z_reset_counter),
        float(vx), float(vy), float(vz), float(z_deriv),
        float(delta_vxy[0]), float(delta_vxy[1]),
        int(vxy_reset_counter),
        float(delta_vz),
        int(vz_reset_counter),
        float(ax), float(ay), float(az),
        float(heading),
        float(delta_heading),
        int(heading_reset_counter), int(heading_good_for_control),
        int(xy_global), int(z_global),
        int(ref_timestamp),
        float(ref_lat), float(ref_lon),
        float(ref_alt),
        float(dist_bottom),
        int(dist_bottom_valid),
        int(dist_bottom_sensor_bitfield),
        float(eph),
        float(epv), float(evh), float(evv),
        int(dead_reckoning),
        float(vxy_max), float(vz_max), float(hagl_min), float(hagl_max),
    )
    return pkt

def send_udp(buf: bytes, host=HOST, port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(buf, (host, port))
        print(f"Sent {len(buf)} bytes to {host}:{port}")

def main():
    while True:
        now_us = int(time.time() * 1_000_000)
        payload = build_packet(PACKET_ID, now_us)
        send_udp(payload)
        time.sleep(0.5)  # 2 Hz

if __name__ == "__main__":
    main()