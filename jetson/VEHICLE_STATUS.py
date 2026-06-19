#!/usr/bin/env python3
import socket
import struct
import time
import random

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 29  # VEHICLE_STATUS

# Big-endian layout
# I   = uint32  (packet_id)
# Q   = uint64  (timestamp)
# Q   = uint64  (armed_time)
# Q   = uint64  (takeoff_time)
# B   = uint8   (arming_state)
# B   = uint8   (latest_arming_reason)
# B   = uint8   (latest_disarming_reason)
# 5x  = 40-bit padding after latest_disarming_reason
# Q   = uint64  (nav_state_timestamp)
# B   = uint8   (nav_state_user_intention)
# B   = uint8   (nav_state)
# H   = uint16  (failure_detector_status)
# B   = uint8   (hil_state)
# B   = uint8   (vehicle_type)
# then a sequence of uint8 fields (booleans or small enums):
#   failsafe,
#   failsafe_and_user_took_over,
#   gcs_connection_lost,
#   gcs_connection_lost_counter,
#   high_latency_data_link_lost,
#   is_vtol,
#   is_vtol_tailsitter,
#   in_transition_mode,
#   in_transition_to_fw,
#   system_type,
#   system_id,
#   component_id,
#   safety_button_available,
#   safety_off,
#   power_input_valid,
#   usb_connected,
#   open_drone_id_system_present,
#   open_drone_id_system_healthy,
#   parachute_system_present,
#   parachute_system_healthy,
#   avoidance_system_required,
#   avoidance_system_valid,
#   rc_calibration_in_progress,
#   calibration_enabled,
#   pre_flight_checks_pass

PKT_STRUCT = struct.Struct(
    ">IQQQ"       # packet_id, timestamp, armed_time, takeoff_time
    "BBB"         # arming_state, latest_arming_reason, latest_disarming_reason
    "5x"          # 40-bit padding
    "Q"           # nav_state_timestamp
    "BBH"         # nav_state_user_intention, nav_state, failure_detector_status
    "BB"          # hil_state, vehicle_type
    + "B" * 25    # 25 trailing uint8 fields (see list above)
    + "x"         # 1 byte of padding at end
)


def _b(p=0.5):
    """Return 1 with prob p else 0."""
    return 1 if random.random() < p else 0


def build_packet(packet_id: int, now_us: int) -> bytes:
    # Times
    armed_time = now_us - random.randint(5_000_000, 50_000_000)  # 5–50s ago
    takeoff_time = now_us - random.randint(1_000_000, 40_000_000)
    nav_state_ts = now_us - random.randint(100_000, 5_000_000)

    # Small enums
    arming_state = random.randint(0, 6)
    latest_arming_reason = random.randint(0, 13)
    latest_disarming_reason = random.randint(0, 13)

    nav_state_user_intention = random.randint(0, 23)
    nav_state = random.randint(0, 23)
    failure_detector_status = random.randint(0, 0xFFFF)
    hil_state = random.randint(0, 1)
    vehicle_type = random.randint(0, 4)

    # Booleans / small counters
    failsafe = _b(0.1)
    failsafe_and_user_took_over = _b(0.05)

    gcs_connection_lost = _b(0.05)
    gcs_connection_lost_counter = random.randint(0, 10)
    high_latency_data_link_lost = _b(0.05)

    is_vtol = _b(0.3)
    is_vtol_tailsitter = _b(0.1)
    in_transition_mode = _b(0.1)
    in_transition_to_fw = _b(0.05)

    system_type = random.randint(0, 31)
    system_id = random.randint(1, 255)
    component_id = random.randint(1, 255)

    safety_button_available = _b(0.7)
    safety_off = _b(0.8)

    power_input_valid = _b(0.95)
    usb_connected = _b(0.2)

    open_drone_id_system_present = _b(0.2)
    open_drone_id_system_healthy = _b(0.95)

    parachute_system_present = _b(0.05)
    parachute_system_healthy = _b(0.98)

    avoidance_system_required = _b(0.1)
    avoidance_system_valid = _b(0.95)

    rc_calibration_in_progress = _b(0.02)
    calibration_enabled = _b(0.1)

    pre_flight_checks_pass = _b(0.9)

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        int(armed_time),
        int(takeoff_time),
        int(arming_state),
        int(latest_arming_reason),
        int(latest_disarming_reason),
        int(nav_state_ts),
        int(nav_state_user_intention),
        int(nav_state),
        int(failure_detector_status),
        int(hil_state),
        int(vehicle_type),
        int(failsafe),
        int(failsafe_and_user_took_over),
        int(gcs_connection_lost),
        int(gcs_connection_lost_counter),
        int(high_latency_data_link_lost),
        int(is_vtol),
        int(is_vtol_tailsitter),
        int(in_transition_mode),
        int(in_transition_to_fw),
        int(system_type),
        int(system_id),
        int(component_id),
        int(safety_button_available),
        int(safety_off),
        int(power_input_valid),
        int(usb_connected),
        int(open_drone_id_system_present),
        int(open_drone_id_system_healthy),
        int(parachute_system_present),
        int(parachute_system_healthy),
        int(avoidance_system_required),
        int(avoidance_system_valid),
        int(rc_calibration_in_progress),
        int(calibration_enabled),
        int(pre_flight_checks_pass)
    )

    # Optional sanity print
    # print(f"Packet size: {len(pkt)} bytes")
    return pkt


def send_udp(buf: bytes, host=HOST, port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(buf, (host, port))
        print(f"Sent {len(buf)} bytes to {host}:{port} -> {buf.hex()}")


def main():
    while True:
        now_us = int(time.time() * 1_000_000)
        payload = build_packet(PACKET_ID, now_us)
        # Ensure deterministic big-endian length
        print(f"VEHICLE_STATUS bytes: {len(payload)}")
        send_udp(payload)
        time.sleep(0.5)


if __name__ == "__main__":
    main()