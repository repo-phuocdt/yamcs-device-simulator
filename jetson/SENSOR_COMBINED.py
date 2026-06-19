#!/usr/bin/env python3
import socket
import struct
import time
import random

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 15  # SENSOR_COMBINED

# Big-endian packet layout (total 52 bytes):
# uint32  packet_id
# uint64  timestamp (us)
# float32 gyro_rad[3]
# uint32  gyro_integral_dt (us)
# int32   accelerometer_timestamp_relative (us)
# float32 accelerometer_m_s2[3]
# uint32  accelerometer_integral_dt (us)
# uint8   accelerometer_clipping
# uint8   gyro_clipping
# uint8   accel_calibration_count
# uint8   gyro_calibration_count
PKT_STRUCT = struct.Struct(
    ">"
    "I"     # packet_id
    "Q"     # timestamp
    "3f"    # gyro_rad[3]
    "I"     # gyro_integral_dt
    "i"     # accelerometer_timestamp_relative
    "3f"    # accelerometer_m_s2[3]
    "I"     # accelerometer_integral_dt
    "BBBB"  # accelerometer_clipping, gyro_clipping, accel_calibration_count, gyro_calibration_count
)

def build_packet(packet_id: int, now_us: int) -> bytes:
    # Gyro rad/s (FRD)
    gx = random.uniform(-2.0, 2.0)
    gy = random.uniform(-2.0, 2.0)
    gz = random.uniform(-2.0, 2.0)
    gyro_integral_dt = random.randint(500, 5000)  # us (0.5–5 ms)

    # Accelerometer time relation: accel timestamp = now_us + rel
    accelerometer_timestamp_relative = random.randint(-5000, 0)  # us (arrived before now)

    # Accel m/s^2
    ax = random.uniform(-1.5, 1.5)
    ay = random.uniform(-1.5, 1.5)
    az = random.uniform(8.5, 10.5)  # include gravity-ish
    accelerometer_integral_dt = random.randint(500, 5000)  # us

    # Bitfields / counters
    accelerometer_clipping = 0
    gyro_clipping = 0
    accel_calibration_count = random.randint(0, 10)
    gyro_calibration_count = random.randint(0, 10)

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        float(gx), float(gy), float(gz),
        int(gyro_integral_dt),
        int(accelerometer_timestamp_relative),
        float(ax), float(ay), float(az),
        int(accelerometer_integral_dt),
        int(accelerometer_clipping) & 0xFF,
        int(gyro_clipping) & 0xFF,
        int(accel_calibration_count) & 0xFF,
        int(gyro_calibration_count) & 0xFF,
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