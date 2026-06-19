#!/usr/bin/env python3
import socket, struct, time, random, math

import os
HOST = os.environ.get("YAMCS_HOST", "127.0.0.1")
PORT = int(os.environ.get("YAMCS_PORT", "40002"))
PACKET_ID = 13  # VEHICLE_ATTITUDE

# >  = big-endian
# I  = uint32
# Q  = uint64
# 8f = 8 x float32  (q[4] + delta_q_reset[4])
# B  = uint8
# 3x = 3 padding bytes (24 bit)
PKT_STRUCT = struct.Struct(">IQQ8fB3x")

def rand_unit_quaternion():
    u1, u2, u3 = random.random(), random.random(), random.random()
    sq1, sq2 = math.sqrt(1 - u1), math.sqrt(u1)
    t1, t2 = 2*math.pi*u2, 2*math.pi*u3
    w = math.cos(t2) * sq2
    x = math.sin(t1) * sq1
    y = math.cos(t1) * sq1
    z = math.sin(t2) * sq2
    return (float(w), float(x), float(y), float(z))

def small_delta_quat(max_deg=2.0):
    ax, ay, az = (random.uniform(-1, 1) for _ in range(3))
    n = (ax*ax + ay*ay + az*az) ** 0.5 or 1.0
    ax, ay, az = ax/n, ay/n, az/n
    ang = math.radians(random.uniform(-max_deg, max_deg))
    h = 0.5 * ang
    w, s = math.cos(h), math.sin(h)
    return (float(w), float(ax*s), float(ay*s), float(az*s))

def build_packet(packet_id: int, now_us: int) -> bytes:
    ts_sample = now_us - 5_000
    q  = rand_unit_quaternion()
    dq = small_delta_quat(2.0)
    cnt = random.randint(0, 255)

    pkt = PKT_STRUCT.pack(
        int(packet_id),
        int(now_us),
        int(ts_sample),
        q[0], q[1], q[2], q[3],
        dq[0], dq[1], dq[2], dq[3],
        int(cnt),
    )
    assert len(pkt) == 56, f"len={len(pkt)} != 56"
    return pkt

def send_udp(buf: bytes, host=HOST, port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(buf, (host, port))
        print(f"Sent {len(buf)} bytes: {buf.hex()}")

def main():
    while True:
        now_us = int(time.time() * 1_000_000)
        send_udp(build_packet(PACKET_ID, now_us))
        time.sleep(1)

if __name__ == "__main__":
    main()