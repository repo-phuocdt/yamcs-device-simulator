#!/usr/bin/env python3
import socket
import struct
import time
import random

# ============================
# UDP target
# ============================
import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 11  # FAILSAFE_FLAGS

# ============================
# Packet definition (BIG-ENDIAN)
# Container: FAILSAFE_FLAGS
# Layout (total 89 bytes):
#   uint32 packet_id
#   uint64 timestamp_us
#   uint32 mode_req_angular_velocity
#   uint32 mode_req_attitude
#   uint32 mode_req_local_alt
#   uint32 mode_req_local_position
#   uint32 mode_req_local_position_relaxed
#   uint32 mode_req_global_position
#   uint32 mode_req_mission
#   uint32 mode_req_offboard_signal
#   uint32 mode_req_home_position
#   uint32 mode_req_wind_and_flight_time_compliance
#   uint32 mode_req_prevent_arming
#   uint32 mode_req_manual_control
#   uint32 mode_req_other
#   bool   angular_velocity_invalid
#   bool   attitude_invalid
#   bool   local_altitude_invalid
#   bool   local_position_invalid
#   bool   local_position_invalid_relaxed
#   bool   local_velocity_invalid
#   bool   global_position_invalid
#   bool   auto_mission_missing
#   bool   offboard_control_signal_lost
#   bool   home_position_invalid
#   bool   manual_control_signal_lost
#   bool   gcs_connection_lost
#   uint8  battery_warning
#   bool   battery_low_remaining_time
#   bool   battery_unhealthy
#   bool   primary_geofence_breached
#   bool   mission_failure
#   bool   vtol_fixed_wing_system_failure
#   bool   wind_limit_exceeded
#   bool   flight_time_limit_exceeded
#   bool   local_position_accuracy_low
#   bool   fd_critical_failure
#   bool   fd_esc_arming_failure
#   bool   fd_imbalanced_prop
#   bool   fd_motor_failure
#
# In MDB, booleans are mapped to uint8 (0 or 1).
# ============================

PKT_STRUCT = struct.Struct(
    ">"         # big-endian
    "I"         # packet_id
    "Q"         # timestamp_us
    "13I"       # 13x mode_req_* (uint32)
    "10B"       # 10x mode requirement booleans
    "2B"        # 2x control link booleans
    "B"         # battery_warning (uint8)
    "2B"        # 2x battery booleans
    "6B"        # 6x other booleans
    "4B"        # 4x failure detector booleans
    "3x"        # padding to align to 4 bytes (total size 89 -> 92 bytes)
)

def build_packet(packet_id: int, now_us: int) -> bytes:
    # Mode requirements (uint32). Use 0/1 flags for simplicity.
    mode_reqs = [
        random.randint(0, 1),  # mode_req_angular_velocity
        random.randint(0, 1),  # mode_req_attitude
        random.randint(0, 1),  # mode_req_local_alt
        random.randint(0, 1),  # mode_req_local_position
        random.randint(0, 1),  # mode_req_local_position_relaxed
        random.randint(0, 1),  # mode_req_global_position
        random.randint(0, 1),  # mode_req_mission
        random.randint(0, 1),  # mode_req_offboard_signal
        random.randint(0, 1),  # mode_req_home_position
        random.randint(0, 1),  # mode_req_wind_and_flight_time_compliance
        random.randint(0, 1),  # mode_req_prevent_arming
        random.randint(0, 1),  # mode_req_manual_control
        random.randint(0, 1),  # mode_req_other
    ]

    # 10 mode requirement booleans
    mode_req_flags = [random.randint(0, 1) for _ in range(10)]

    # 2 control link booleans
    control_links = [random.randint(0, 1) for _ in range(2)]

    # Battery section
    battery_warning = random.randint(0, 4)  # e.g. 0..4
    battery_flags = [random.randint(0, 1), random.randint(0, 1)]  # low_remaining_time, unhealthy

    # Other flags (6)
    other_flags = [random.randint(0, 1) for _ in range(6)]

    # Failure detector flags (4)
    fd_flags = [random.randint(0, 1) for _ in range(4)]

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        *[int(x) & 0xFFFFFFFF for x in mode_reqs],
        *[int(x) & 0xFF for x in mode_req_flags],
        *[int(x) & 0xFF for x in control_links],
        int(battery_warning) & 0xFF,
        *[int(x) & 0xFF for x in battery_flags],
        *[int(x) & 0xFF for x in other_flags],
        *[int(x) & 0xFF for x in fd_flags],
    )
    return pkt

def send_udp(buf: bytes, host=HOST, port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(buf, (host, port))
        print(f"Sent {len(buf)} bytes to {host}:{port}")

def main():
    try:
        while True:
            now_us = int(time.time() * 1_000_000)
            payload = build_packet(PACKET_ID, now_us)
            send_udp(payload)
            time.sleep(0.5)  # 2 Hz
    except KeyboardInterrupt:
        print("Stopped.")

if __name__ == "__main__":
    main()