#!/usr/bin/env python3
import socket
import struct
import time
import random
import math

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 22  # BATTERY_STATUS

# Packet Structure (BIG-ENDIAN):
# uint32  packet_id
# uint64  timestamp
# uint8   connected                 + pad[3]
# float32 voltage_v
# float32 voltage_filtered_v
# float32 current_a
# float32 current_filtered_a
# float32 current_average_a
# float32 discharged_mah
# float32 remaining
# float32 scale
# float32 time_remaining_s
# float32 temperature
# uint8   cell_count
# uint8   source
# uint8   priority                  + pad[1]
# uint16  capacity
# uint16  cycle_count
# uint16  average_time_to_empty
# uint16  serial_number
# uint16  manufacture_date
# uint16  state_of_health
# uint16  max_error
# uint8   id                        + pad[1]
# uint16  interface_error           + pad[2]
# float32 voltage_cell_v[14]
# float32 max_cell_voltage_delta
# uint8   is_powering_off
# uint8   is_required
# uint16  faults
# uint32  custom_faults
# uint8   warning
# uint8   mode                      + pad[2]
# float32 average_power
# float32 available_energy
# float32 full_charge_capacity_wh
# float32 remaining_capacity_wh
# float32 design_capacity
# uint16  average_time_to_full
# uint16  over_discharge_count
# float32 nominal_voltage
#
# Tổng kích thước: 180 bytes
PKT_STRUCT = struct.Struct(
    ">"
    "IQ"          # packet_id, timestamp
    "Bxxx"        # connected + pad[3]
    "10f"         # 10 float32: voltage_v .. temperature
    "BBBx"        # cell_count, source, priority + pad
    "7H"          # capacity .. max_error
    "Bx"          # id + pad
    "Hxx"         # interface_error + pad[2]
    "14f"         # voltage_cell_v[14]
    "f"           # max_cell_voltage_delta
    "BB"          # is_powering_off, is_required
    "H"           # faults
    "I"           # custom_faults
    "B"           # warning
    "Bxx"         # mode + pad[2]
    "5f"          # average_power .. design_capacity
    "H"           # average_time_to_full
    "H"           # over_discharge_count
    "f"           # nominal_voltage
)

def build_packet(packet_id: int, now_us: int) -> bytes:
    connected = 1 if random.random() > 0.05 else 0

    voltage_v = round(random.uniform(10.0, 25.2), 2)
    voltage_filtered_v = voltage_v + round(random.uniform(-0.2, 0.2), 2)

    current_a = round(random.uniform(0.0, 30.0), 2)
    current_filtered_a = max(0.0, current_a + round(random.uniform(-0.5, 0.5), 2))
    current_average_a = round((current_a + current_filtered_a) / 2.0, 2)

    discharged_mah = round(random.uniform(0.0, 8000.0), 1)
    remaining = round(random.uniform(0.0, 1.0), 3)
    scale = round(random.uniform(1.0, 1.2), 3)
    time_remaining_s = round(random.uniform(60.0, 3600.0), 1)
    temperature = round(random.uniform(20.0, 55.0), 2)

    cell_count = random.choice([4, 6, 8, 12, 14])
    source = random.choice([0, 1, 2])  # POWER_MODULE, EXTERNAL, ESCS
    priority = random.randint(0, 3)

    capacity = random.randint(3000, 20000)          # mAh
    cycle_count = random.randint(0, 1000)
    average_time_to_empty = random.randint(5, 120)  # minutes
    serial_number = random.randint(1, 65000)
    # encode manufacture_date: Day + Month*32 + (Year-1980)*512
    day = random.randint(1, 28)
    month = random.randint(1, 12)
    year = random.randint(2020, 2025)
    manufacture_date = (day & 31) + ((month & 15) << 5) + ((max(0, year - 1980) & 127) << 9)

    state_of_health = random.randint(70, 100)
    max_error = random.randint(1, 10)
    battery_id = random.randint(1, 4)
    interface_error = random.randint(0, 100)

    # 14 cell voltages (nếu cell_count < 14 thì fill 0 ở cuối)
    cells = [round(random.uniform(3.6, 4.2), 3) for _ in range(cell_count)]
    if len(cells) < 14:
        cells += [0.0] * (14 - len(cells))
    voltage_cell_v = cells[:14]
    max_cell_voltage_delta = round(max(voltage_cell_v) - min([v for v in voltage_cell_v if v > 0] or [0]), 4)

    is_powering_off = 1 if random.random() < 0.02 else 0
    is_required = 1 if random.random() < 0.9 else 0
    faults = random.getrandbits(16)
    custom_faults = random.getrandbits(32)
    warning = random.choice([0, 1, 2, 3, 4])  # NONE..FAILED
    mode = random.choice([0, 1, 2])           # UNKNOWN/AUTO_DISCHARGING/HOT_SWAP

    average_power = round(current_average_a * voltage_v, 2)
    available_energy = round(voltage_v * current_a * 0.95, 2)
    full_charge_capacity_wh = round(random.uniform(50.0, 300.0), 2)
    remaining_capacity_wh = round(full_charge_capacity_wh * remaining, 2)
    design_capacity = round(random.uniform(60.0, 320.0), 2)
    average_time_to_full = random.randint(10, 240)
    over_discharge_count = random.randint(0, 20)
    nominal_voltage = round(random.choice([14.8, 22.2, 25.9, 44.4]), 1)

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        int(connected),
        float(voltage_v), float(voltage_filtered_v), float(current_a), float(current_filtered_a),
        float(current_average_a), float(discharged_mah), float(remaining), float(scale),
        float(time_remaining_s), float(temperature),
        int(cell_count), int(source), int(priority),
        int(capacity), int(cycle_count), int(average_time_to_empty),
        int(serial_number), int(manufacture_date), int(state_of_health), int(max_error),
        int(battery_id),
        int(interface_error),
        *map(float, voltage_cell_v),
        float(max_cell_voltage_delta),
        int(is_powering_off), int(is_required),
        int(faults), int(custom_faults),
        int(warning), int(mode),
        float(average_power), float(available_energy), float(full_charge_capacity_wh),
        float(remaining_capacity_wh), float(design_capacity),
        int(average_time_to_full), int(over_discharge_count),
        float(nominal_voltage),
    )
    # print("PKT SIZE:", len(pkt))
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