#!/usr/bin/env python3
import socket
import struct
import time
import random
import math

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 14  # SENSOR_GPS

# Big-endian layout with explicit paddings (total 148 bytes):
# I    packet_id
# Q    timestamp
# Q    timestamp_sample
# I    device_id
# i    lat (1e-7 deg)
# i    lon (1e-7 deg)
# i    alt (mm)
# i    alt_ellipsoid (mm)
# f    s_variance_m_s
# f    c_variance_rad
# B    fix_type
# 3x   padding (fix_type + 24 bits)
# f    eph
# f    epv
# f    hdop
# f    vdop
# i    noise_per_ms
# H    automatic_gain_control
# B    jamming_state
# x    padding (jamming_state + 8 bits)
# i    jamming_indicator
# B    spoofing_state
# 3x   padding (spoofing_state + 24 bits)
# f    vel_m_s
# f    vel_n_m_s
# f    vel_e_m_s
# f    vel_d_m_s
# f    cog_rad
# B    vel_ned_valid
# 3x   padding (vel_ned_valid + 24 bits)
# i    timestamp_time_relative
# 4x   padding (+32 bits)
# Q    time_utc_usec
# B    satellites_used
# 3x   padding (+24 bits)
# f    heading
# f    heading_offset
# f    heading_accuracy
# f    rtcm_injection_rate
# B    selected_rtcm_instance
# 3x   padding (+24 bits)
PKT_STRUCT = struct.Struct(
    ">IQQIiiiiffB3xffffiHBx"  # ... up to jamming_state + pad
    "i"                       # <-- jamming_indicator (MISSING before)
    "B3x"                     # spoofing_state + pad
    "fffff"                   # vel_m_s..cog_rad
    "B3x"                     # vel_ned_valid + pad
    "i4x"                     # timestamp_time_relative + 32b pad
    "Q"                       # time_utc_usec
    "B3x"                     # satellites_used + pad
    "ffff"                    # heading, heading_offset, heading_accuracy, rtcm_injection_rate
    "B3x"                     # selected_rtcm_instance + pad
)

def deg_to_1e7(x_deg: float) -> int:
    return int(round(x_deg * 1e7))

def meters_to_mm(m: float) -> int:
    return int(round(m * 1000.0))

def build_packet(packet_id: int, now_us: int) -> bytes:
    # Sample times
    ts_sample = now_us - random.randint(1000, 10_000)

    # Device ID (32-bit)
    device_id = 0x47505300 | random.randint(0, 0xFF)  # "GPS\0" + rand byte

    # Position: random around Hanoi for example
    lat_deg = 21.0278 + random.uniform(-0.001, 0.001)
    lon_deg = 105.8342 + random.uniform(-0.001, 0.001)
    alt_m   = 10.0 + random.uniform(-2.0, 2.0)
    alt_ell_m = alt_m + random.uniform(-1.0, 1.0)

    lat_e7 = deg_to_1e7(lat_deg)
    lon_e7 = deg_to_1e7(lon_deg)
    alt_mm = meters_to_mm(alt_m)
    alt_ell_mm = meters_to_mm(alt_ell_m)

    # Variances and DOP
    s_variance_m_s = random.uniform(0.05, 0.5)
    c_variance_rad = random.uniform(0.005, 0.05)
    fix_type = random.choice([3, 4, 5, 6])  # prefer >= 3
    eph = random.uniform(0.3, 2.0)
    epv = random.uniform(0.5, 3.0)
    hdop = random.uniform(0.5, 2.0)
    vdop = random.uniform(0.8, 3.0)

    # Noise and jamming/spoofing
    noise_per_ms = random.randint(0, 300)
    agc = random.randint(0, 65535)              # uint16
    jamming_state = random.choice([0, 1, 2, 3]) # 0..3
    jamming_indicator = random.randint(0, 1000)
    spoofing_state = random.choice([0, 1, 2, 3])

    # Velocities and COG
    vel_m_s  = abs(random.gauss(5.0, 2.0))
    vel_n    = random.uniform(-3.0, 3.0)
    vel_e    = random.uniform(-3.0, 3.0)
    vel_d    = random.uniform(-1.0, 1.0)
    cog_rad  = random.uniform(-math.pi, math.pi)
    vel_ned_valid = 1

    # Time refs
    # timestamp_time_relative: signed microseconds relative to now_us
    timestamp_time_relative = -random.randint(0, 50_000)
    time_utc_usec = max(0, int(time.time() * 1_000_000))

    # Satellites / heading
    satellites_used = random.randint(10, 20)
    heading = random.uniform(-math.pi, math.pi)
    heading_offset = random.uniform(-0.05, 0.05)
    heading_accuracy = random.uniform(0.01, 0.2)

    # RTCM
    rtcm_injection_rate = random.uniform(0.0, 5.0)
    selected_rtcm_instance = random.randint(0, 3)

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        int(ts_sample),
        int(device_id),
        int(lat_e7),
        int(lon_e7),
        int(alt_mm),
        int(alt_ell_mm),
        float(s_variance_m_s),
        float(c_variance_rad),
        int(fix_type),
        float(eph),
        float(epv),
        float(hdop),
        float(vdop),
        int(noise_per_ms),
        int(agc),
        int(jamming_state),
        int(jamming_indicator),
        int(spoofing_state),
        float(vel_m_s),
        float(vel_n),
        float(vel_e),
        float(vel_d),
        float(cog_rad),
        int(vel_ned_valid),
        int(timestamp_time_relative),
        int(time_utc_usec),
        int(satellites_used),
        float(heading),
        float(heading_offset),
        float(heading_accuracy),
        float(rtcm_injection_rate),
        int(selected_rtcm_instance),
    )
    assert len(pkt) == 148, f"len={len(pkt)} != 148"
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