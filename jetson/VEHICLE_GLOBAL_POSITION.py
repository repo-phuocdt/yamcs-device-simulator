#!/usr/bin/env python3
import socket
import struct
import time
import random

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 20  # VEHICLE_GLOBAL_POSITION

# Big-endian layout:
# I   : uint32   packet_id
# Q   : uint64   timestamp (us)
# Q   : uint64   timestamp_sample (us)
# d d : float64  lat, lon (deg)
# f f : float32  alt, alt_ellipsoid (m)
# f   : float32  delta_alt (m)
# B B : uint8    lat_lon_reset_counter, alt_reset_counter
# 2x  : 16-bit padding (as requested) after alt_reset_counter
# f f f : float32 eph, epv, terrain_alt (m)
# B B : uint8    terrain_alt_valid, dead_reckoning
#
# Total size: 68 bytes
PKT_STRUCT = struct.Struct(">IQQddfffBB2xfffBB2x")

def build_packet(packet_id: int, now_us: int) -> bytes:
    # Simulate a plausible position near an arbitrary reference
    # Latitude [-90, 90], Longitude [-180, 180]
    lat = random.uniform(-90.0, 90.0)
    lon = random.uniform(-180.0, 180.0)

    # Altitudes (meters)
    alt = random.uniform(0.0, 2000.0)
    alt_ellipsoid = alt + random.uniform(-50.0, 50.0)

    # Delta altitude small change
    delta_alt = random.uniform(-1.0, 1.0)

    # Counters (uint8)
    lat_lon_reset_counter = random.randint(0, 255)
    alt_reset_counter = random.randint(0, 255)

    # Errors (meters)
    eph = random.uniform(0.1, 5.0)
    epv = random.uniform(0.1, 8.0)

    # Terrain alt (m)
    terrain_alt = random.uniform(-50.0, 1500.0)

    # Flags (uint8 0/1)
    terrain_alt_valid = random.randint(0, 1)
    dead_reckoning = random.randint(0, 1)

    ts_sample = now_us - 10_000  # 10 ms earlier

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        int(ts_sample),
        float(lat),
        float(lon),
        float(alt),
        float(alt_ellipsoid),
        float(delta_alt),
        int(lat_lon_reset_counter),
        int(alt_reset_counter),
        float(eph),
        float(epv),
        float(terrain_alt),
        int(terrain_alt_valid),
        int(dead_reckoning),
    )

    assert len(pkt) == 68, f"Unexpected packet size: {len(pkt)}"
    return pkt

def send_udp(buf: bytes, host=HOST, port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(buf, (host, port))
        print(f"Sent {len(buf)} bytes: {buf.hex()}")

def main():
    try:
        while True:
            now_us = int(time.time() * 1_000_000)
            payload = build_packet(PACKET_ID, now_us)
            send_udp(payload, HOST, PORT)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("Stopped.")

if __name__ == "__main__":
    main()