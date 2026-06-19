#!/usr/bin/env python3
import socket
import struct
import time
import random

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 19  # VEHICLE_IMU

# Packet layout (big-endian, no implicit padding by struct):
# uint32  packet_id
# uint64  timestamp
# uint64  timestamp_sample
# uint32  accel_device_id
# uint32  gyro_device_id
# float32[3] delta_angle
# float32[3] delta_velocity
# uint16  delta_angle_dt
# uint16  delta_velocity_dt
# uint8   delta_angle_clipping
# uint8   delta_velocity_clipping
# uint8   accel_calibration_count
# uint8   gyro_calibration_count
#
# Total size = 60 bytes
PKT_STRUCT = struct.Struct(
    ">I"     # packet_id
    "QQ"     # timestamp, timestamp_sample
    "II"     # accel_device_id, gyro_device_id
    "3f"     # delta_angle[3]
    "3f"     # delta_velocity[3]
    "H"      # delta_angle_dt (us)
    "H"      # delta_velocity_dt (us)
    "B"      # delta_angle_clipping (bitfield)
    "B"      # delta_velocity_clipping (bitfield)
    "B"      # accel_calibration_count
    "B"      # gyro_calibration_count
)
assert PKT_STRUCT.size == 60, PKT_STRUCT.size


def build_packet(packet_id: int, now_us: int) -> bytes:
    # Sample timestamp within last 2 ms
    ts_sample = now_us - random.randint(500, 2_000)

    # Fake device ids (PX4 style: bus/type encoded). Keep stable-ish ranges
    accel_device_id = 0xACC00010 + random.randint(0, 0xFF)
    gyro_device_id = 0x20000000 + random.randint(0, 0xFF)  # ensure 32-bit, unique-ish ID

    # Small deltas over integration window
    delta_angle = (
        random.uniform(-0.02, 0.02),
        random.uniform(-0.02, 0.02),
        random.uniform(-0.02, 0.02),
    )
    delta_velocity = (
        random.uniform(-0.2, 0.2),
        random.uniform(-0.2, 0.2),
        random.uniform(-0.2, 0.2),
    )

    # Integration periods (microseconds)
    da_dt = random.randint(2000, 5000)
    dv_dt = random.randint(2000, 5000)

    # Bitfields: CLIPPING_X=1, CLIPPING_Y=2, CLIPPING_Z=4
    def rand_clip():
        mask = 0
        if random.random() < 0.02: mask |= 1
        if random.random() < 0.02: mask |= 2
        if random.random() < 0.02: mask |= 4
        return mask

    da_clip = rand_clip()
    dv_clip = rand_clip()

    # Calibration counters (wrap at 255)
    acc_cal_cnt = random.randint(0, 20)
    gyr_cal_cnt = random.randint(0, 20)

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        int(ts_sample),
        int(accel_device_id) & 0xFFFFFFFF,
        int(gyro_device_id)  & 0xFFFFFFFF,
        float(delta_angle[0]), float(delta_angle[1]), float(delta_angle[2]),
        float(delta_velocity[0]), float(delta_velocity[1]), float(delta_velocity[2]),
        int(da_dt) & 0xFFFF,
        int(dv_dt) & 0xFFFF,
        int(da_clip) & 0xFF,
        int(dv_clip) & 0xFF,
        int(acc_cal_cnt) & 0xFF,
        int(gyr_cal_cnt) & 0xFF,
    )
    assert len(pkt) == 60, f"len={len(pkt)} != 60"
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