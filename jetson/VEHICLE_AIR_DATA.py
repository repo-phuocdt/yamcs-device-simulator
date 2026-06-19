#!/usr/bin/env python3
import socket
import struct
import time
import random

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 16  # VEHICLE_AIR_DATA

# Big-endian layout:
# I  = uint32  (packet_id)
# Q  = uint64  (timestamp)
# Q  = uint64  (timestamp_sample)
# I  = uint32  (baro_device_id)
# f  = float32 (baro_alt_meter)
# f  = float32 (baro_temp_celcius)
# f  = float32 (baro_pressure_pa)
# f  = float32 (rho)
# B  = uint8   (calibration_count)
# 3x = 24-bit padding to align nicely
PKT_STRUCT = struct.Struct(">IQQIffffB3x")


def build_packet(packet_id: int, now_us: int) -> bytes:
    # Simulate a realistic sample time a bit in the past
    ts_sample = now_us - random.randint(500, 5000)

    # Example device id(s)
    baro_device_id = 0xB4A01234 & 0xFFFFFFFF  # masked to 32-bit

    # Generate plausible air data
    baro_alt_meter     = random.uniform(0.0, 1500.0)       # meters AMSL
    baro_temp_celcius  = random.uniform(10.0, 35.0)        # deg C
    baro_pressure_pa   = random.uniform(95000.0, 103000.0) # Pa
    rho                = random.uniform(1.0, 1.3)          # kg/m^3

    calibration_count  = random.randint(0, 255)

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        int(ts_sample),
        int(baro_device_id),
        float(baro_alt_meter),
        float(baro_temp_celcius),
        float(baro_pressure_pa),
        float(rho),
        int(calibration_count),
    )
    return pkt


def send_udp(buf: bytes, host=HOST, port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(buf, (host, port))
        print(f"Sent {len(buf)} bytes to {host}:{port} -> {buf.hex()}")


def main():
    while True:
        now_us = int(time.time() * 1_000_000)
        payload = build_packet(PACKET_ID, now_us)
        print(f"VEHICLE_AIR_DATA bytes: {len(payload)}")
        send_udp(payload)
        time.sleep(0.5)


if __name__ == "__main__":
    main()