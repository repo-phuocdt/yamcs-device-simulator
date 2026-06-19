#!/usr/bin/env python3
"""Firetest device simulator — full TC-TM loop (parity with the original Node version).

Streams CCSDS sensor data over UDP and drives Yamcs CSV recording via the MQTT TestFlag:
  - command mode (default): idle until the operator sends START_ENGINE On/Off from the Yamcs
    Web UI. On -> publish TestFlag ON (arm) + stream UDP data; Off -> stop + TestFlag OFF (finish).
  - auto mode: self-drive TestFlag ON -> UDP burst (duration_seconds) -> TestFlag OFF; `loop` repeats.

Configured via environment variables (set by `docker run -e ...` / run_device.sh):
  YAMCS_HOST, YAMCS_PORT (UDP), MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, APID, SENSOR_IDS,
  SEND_INTERVAL_SECONDS, MODE, DURATION_SECONDS, LOOP, LOOP_GAP_SECONDS
"""
import os
import queue
import random
import signal
import socket
import sys
import threading
import time

import paho.mqtt.client as mqtt

import ccsds

TM_TOPIC = "yamcs-tm-packets"
TC_TOPIC = "yamcs-tc-packets"


def load_config():
    env = os.environ.get
    user, pw = env("MQTT_USERNAME"), env("MQTT_PASSWORD")
    if not user or not pw:
        raise SystemExit("MQTT_USERNAME and MQTT_PASSWORD are required (set via -e)")
    sensor_ids = [int(x) for x in env("SENSOR_IDS", "1,2,3,4,5,6").split(",") if x.strip()]
    return {
        "yamcs_ip": env("YAMCS_HOST", "127.0.0.1"),
        "yamcs_port": int(env("YAMCS_PORT", "40002")),
        "mqtt_port": int(env("MQTT_PORT", "1883")),
        "mqtt_username": user,
        "mqtt_password": pw,
        "apid": int(env("APID", str(ccsds.DATA_APID))),
        "sensor_ids": sensor_ids,
        "send_interval_seconds": float(env("SEND_INTERVAL_SECONDS", "0.1")),
        "mode": env("MODE", "command"),
        "duration_seconds": float(env("DURATION_SECONDS", "10")),
        "loop": env("LOOP", "false").lower() in ("1", "true", "yes", "y"),
        "loop_gap_seconds": float(env("LOOP_GAP_SECONDS", "2")),
    }


class UdpStreamer(threading.Thread):
    """Streams sensor data packets over UDP while `running` is set."""

    def __init__(self, cfg):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = threading.Event()
        self.alive = True

    def run(self):
        host, port = self.cfg["yamcs_ip"], self.cfg["yamcs_port"]
        interval = self.cfg["send_interval_seconds"]
        sent = 0
        last_log = time.perf_counter()
        last_count = 0
        send_acc = 0.0  # cumulative sendto() time since last heartbeat
        send_n = 0
        while self.alive:
            self.running.wait()
            if not self.alive:
                break
            now_ms = int(time.time() * 1000)
            for sid in self.cfg["sensor_ids"]:
                pkt = ccsds.build_data_packet(sid, round(random.uniform(10.5, 95.8), 4), self.cfg["apid"], now_ms)
                s0 = time.perf_counter()
                self.sock.sendto(pkt, (host, port))
                send_acc += time.perf_counter() - s0
                send_n += 1
                sent += 1
            # Heartbeat ~ every 2s with timing: effective rate + avg per-packet send time.
            now = time.perf_counter()
            span = now - last_log
            if span >= 2:
                rate = (sent - last_count) / span
                avg_us = (send_acc / send_n * 1e6) if send_n else 0
                print(f"[udp] streaming -> {host}:{port} | {sent} pkts | {rate:.0f} pkt/s | avg send {avg_us:.0f}µs")
                last_log, last_count, send_acc, send_n = now, sent, 0.0, 0
            time.sleep(interval)

    def start_stream(self):
        self.running.set()

    def stop_stream(self):
        self.running.clear()

    def shutdown(self):
        self.alive = False
        self.running.set()  # unblock the wait so the thread can exit


class Controller:
    """Ties TestFlag (MQTT) + UDP streaming together; idempotent On/Off."""

    def __init__(self, client, streamer):
        self.client = client
        self.streamer = streamer
        self.emitting = False
        self.lock = threading.Lock()
        self._on_time = None  # perf_counter when the current sequence armed

    def _publish_testflag(self, flag):
        if not self.client.is_connected():
            print(f"[ctrl] WARNING: not connected — TestFlag {flag} may be lost")
        t0 = time.perf_counter()
        info = self.client.publish(TM_TOPIC, ccsds.build_testflag_packet(flag), qos=2)
        # Block until the broker acks (QoS2 handshake) so a TestFlag is never dropped by an
        # immediately-following disconnect (e.g. shutdown right after publishing OFF).
        info.wait_for_publish(timeout=3)
        dt = (time.perf_counter() - t0) * 1000
        print(f"[mqtt] TestFlag={flag} sent → broker ack in {dt:.1f} ms")

    def set_on(self):
        with self.lock:
            if self.emitting:
                return
            self._publish_testflag(1)
            self.streamer.start_stream()
            self.emitting = True
            self._on_time = time.perf_counter()
            print("[ctrl] ON — TestFlag armed, emitting data")

    def set_off(self):
        with self.lock:
            if not self.emitting:
                return
            self.streamer.stop_stream()
            self._publish_testflag(0)
            self.emitting = False
            active = (time.perf_counter() - self._on_time) if self._on_time else 0
            print(f"[ctrl] OFF — data stopped, TestFlag finished (sequence active {active:.2f}s)")

    def on_tc(self, payload):
        t0 = time.perf_counter()
        d = ccsds.decode_tc(payload)
        if d["on_off"] is None:
            print("[ctrl] undecodable TC, ignoring")
            return
        print(f"[ctrl] TC received: {'On' if d['on_off'] else 'Off'} (apid={d['apid']}, valid={d['valid']})")
        self.set_on() if d["on_off"] else self.set_off()
        dt = (time.perf_counter() - t0) * 1000
        print(f"[ctrl] TC handled in {dt:.1f} ms (receive → TestFlag sent)")


def main():
    cfg = load_config()
    print(f"[firetest] mode={cfg['mode']} apid={cfg['apid']} sensors={cfg['sensor_ids']} "
          f"-> UDP {cfg['yamcs_ip']}:{cfg['yamcs_port']} / MQTT {cfg['yamcs_ip']}:{cfg['mqtt_port']}")

    streamer = UdpStreamer(cfg)
    streamer.start()

    client = mqtt.Client()
    client.username_pw_set(cfg["mqtt_username"], cfg["mqtt_password"])
    controller = Controller(client, streamer)
    connected = threading.Event()

    rc_msg = {
        1: "unacceptable protocol version",
        2: "identifier rejected",
        3: "broker unavailable",
        4: "bad username or password",
        5: "not authorized (check MQTT username/password)",
    }

    def on_connect(c, _u, _f, rc):
        if rc != 0:
            print(f"[mqtt] CONNECTION REFUSED rc={rc}: {rc_msg.get(rc, 'unknown')}")
            return
        print("[mqtt] connected")
        c.subscribe(TC_TOPIC, qos=2)
        print(f"[mqtt] subscribed {TC_TOPIC}")
        connected.set()

    # TC handling runs on a dedicated worker thread, NOT the paho network thread: publishing a
    # QoS2 TestFlag and waiting for its ack from inside on_message would block the very loop that
    # must process that ack (deadlock until timeout). The callback only enqueues.
    tc_queue = queue.Queue()

    def on_message(_c, _u, msg):
        if msg.topic == TC_TOPIC:
            tc_queue.put(msg.payload)

    def tc_worker():
        while True:
            payload = tc_queue.get()
            controller.on_tc(payload)

    threading.Thread(target=tc_worker, daemon=True).start()

    client.on_connect = on_connect
    client.on_message = on_message

    # TCP-connect with retry. paho's connect() is synchronous with a short (5s) socket timeout,
    # so a single slow/failed handshake (wrong IP, broker down, or a cold Tailscale peer link
    # still doing NAT traversal) would raise a raw traceback and kill the process before the
    # friendly CONNACK handling below ever runs. Retrying both warms a cold link and turns an
    # unreachable broker into a clear message instead of a crash.
    host, port = cfg["yamcs_ip"], cfg["mqtt_port"]
    attempts, retry_delay = 5, 3
    for attempt in range(1, attempts + 1):
        try:
            client.connect(host, port, keepalive=30)
            break
        except OSError as e:
            print(f"[mqtt] connect attempt {attempt}/{attempts} to {host}:{port} failed: "
                  f"{type(e).__name__}: {e}", file=sys.stderr)
            if attempt < attempts:
                time.sleep(retry_delay)
    else:
        print(f"[mqtt] cannot reach broker at {host}:{port} after {attempts} attempts — "
              f"check the IP/port is correct and the broker is running and reachable.",
              file=sys.stderr)
        streamer.shutdown()
        sys.exit(1)
    client.loop_start()

    stopping = threading.Event()

    def shutdown(*_):
        if stopping.is_set():
            return
        stopping.set()
        print("\n[firetest] shutting down...")
        controller.set_off()
        streamer.shutdown()
        client.loop_stop()
        client.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Wait for the broker connection before publishing anything (a TestFlag published while
    # disconnected would be lost and the sequence would never arm).
    if not connected.wait(timeout=15):
        print("[mqtt] connection timed out", file=sys.stderr)
        streamer.shutdown()
        client.loop_stop()
        sys.exit(1)

    if cfg["mode"] == "auto":
        while True:
            controller.set_on()
            time.sleep(cfg["duration_seconds"])
            controller.set_off()
            if not cfg["loop"]:
                break
            time.sleep(cfg["loop_gap_seconds"])
        shutdown()
    else:
        print(f"[firetest] command mode — waiting for START_ENGINE On/Off on {TC_TOPIC}")
        stopping.wait()


if __name__ == "__main__":
    main()
