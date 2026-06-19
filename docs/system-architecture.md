# System Architecture

## Component overview

```
                       docker run -e TEST_TYPE=... -e YAMCS_HOST=... ...
                                          │
                                   entrypoint.py  (PID 1, dispatcher)
                        ┌─────────────────┴──────────────────┐
                 TEST_TYPE=firetest                    TEST_TYPE=jetson
                        │                                    │
            firetest/firetest_run_all.py          jetson/jetson_run_all.py
                        │                                    │
      ┌─────────────────┼───────────────┐         launches every jetson/<TOPIC>.py
      │                 │               │          as a child process (one per topic)
  UdpStreamer      MQTT client     Controller             │
  (UDP TM data)   (TestFlag/TC)   (arm/finish)            │ UDP per-topic PX4/ROS2 packets
      │                 │               │                  │
      ▼                 ▼               ▼                  ▼
  :40002 (UDP)     :1883 (MQTT broker)               :40002 (UDP)
      └──────────────────┬───────────────────────────────┘
                         ▼
                 Yamcs instance "firetest"  (rdp-yamcs-server)
              UDP/MQTT preprocessors → params → CSV recording
```

## firetest data flow (TC–TM loop)

1. **Connect** — MQTT client connects to the broker (`:1883`) with retry + backoff; subscribes to
   `yamcs-tc-packets`.
2. **Arm** — On `START_ENGINE On` TC (or `auto` mode tick), `Controller.set_on()`:
   - publishes `TestFlag=1` (QoS2, waits for broker ack) on `yamcs-tm-packets`,
   - starts `UdpStreamer`, which sends one CCSDS data packet per sensor each interval to `:40002`.
3. **Finish** — On `START_ENGINE Off` (or burst end), `Controller.set_off()` stops the stream and
   publishes `TestFlag=0`.
4. Yamcs records the armed window as a CSV "sequence".

Threading: the paho network thread only **enqueues** received TCs; a dedicated `tc_worker` thread
processes them. This avoids a deadlock where publishing/awaiting a QoS2 ack from inside
`on_message` would block the very loop that must process that ack.

## CCSDS packet contract (firetest)

20-byte big-endian TM packet — **must match the Yamcs preprocessor in `rdp-yamcs-server`**
(`SimulatorCcsds{MQTT,UDP}PacketPreprocessor.java`):

| Bytes | Field | Notes |
|-------|-------|-------|
| 0–1 | apid word | version(3) \| type(1) \| sec-hdr-flag(1)=1 \| apid(11) |
| 2–3 | seq word | seqFlags(2)=3 \| seqCount(14) |
| 4–5 | packet length | 13 (0x000D) |
| 6–9 | coarse time | Unix epoch **seconds** (uint32) |
| 10–11 | fine time | **milliseconds** remainder 0–999 (uint16) |
| 12–15 | packet-id | int32 (1 = TestFlag; 1..10 = sensor data) |
| 16–19 | payload | float32 value (data) **or** byte 16 = flag (TestFlag) |

**Generation time** = `coarse*1000 + fine` → `TimeEncoding.fromUnixMillisec(...)` on the server,
giving millisecond precision. APIDs: data `101`, TestFlag `401`, TC `400`.

TC (received on `yamcs-tc-packets`): `[8-byte START_ENGINE command][4-byte seqCount]`; byte 7 =
on/off, apid 400, packet-id 1. No CRC trailer (checksum check disabled in the preprocessor).

## jetson data flow

`jetson_run_all.py` discovers every `jetson/<TOPIC>.py` sibling and launches each as its own
process. Each publisher streams its own PX4/ROS2-shaped UDP packet (its own `PACKET_ID` and byte
layout) to `YAMCS_HOST:YAMCS_PORT`. No MQTT / control loop — pure UDP fan-out. Ctrl+C terminates
all publishers.

## Ports

| Port | Proto | Purpose |
|------|-------|---------|
| 40002 | UDP | Telemetry (TM) data — both test types |
| 1883 | TCP | MQTT broker — firetest TestFlag/TC only |
| 8090 | TCP | Yamcs web UI (server side, not opened by the simulator) |

## Network notes

- The container reaches the Yamcs host via `YAMCS_HOST` (LAN IP, `host.docker.internal`, or a
  Tailscale `100.x` peer). A cold Tailscale peer link can exceed the MQTT connect timeout on the
  first attempt — handled by the connect-retry logic.
- UDP is connectionless: an unreachable target does **not** raise; only the MQTT TCP connect
  surfaces reachability problems.
- Generation-time accuracy depends on the device clock being synced (NTP) with the Yamcs server.
