# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Containerized **telemetry device simulator** for the ISC RDP / Firetest / HILS platform. It stands
in for real edge hardware and streams telemetry into a Yamcs instance (`rdp-yamcs-server`). Pure
Python 3.11 packaged in Docker; the only third-party dependency is `paho-mqtt==1.6.1`. There is
**no automated test suite** — verification is empirical (run the container against a Yamcs, or
decode a generated packet with the preprocessor's formula).

Deeper docs live in `docs/` (architecture, deployment, code standards, roadmap) and `README.md`.

## Commands

```bash
# Interactive build + run (prompts for test type, IP, ports, mode; 'local' tag = build this folder)
./run_device.sh

# Manual local build + run
docker build -t yamcs-device-sim:local .
docker run --rm -e TEST_TYPE=firetest -e YAMCS_HOST=host.docker.internal \
  -e MQTT_PORT=1883 -e MQTT_USERNAME=test -e MQTT_PASSWORD=*** -e APID=101 -e MODE=command \
  yamcs-device-sim:local
docker run --rm -e TEST_TYPE=jetson -e YAMCS_HOST=10.254.5.153 yamcs-device-sim:local

# Syntax check (closest thing to a "build" for the Python)
python3 -m py_compile entrypoint.py firetest/*.py jetson/*.py

# Quick contract check: decode a generated packet the way the Yamcs preprocessor does
python3 - <<'PY'
import sys; sys.path.insert(0,'firetest'); import ccsds, struct
p = ccsds.build_testflag_packet(1)
print('gen epoch_ms =', struct.unpack('>I',p[6:10])[0]*1000 + (p[10]*256+p[11]))
PY
```

Stop a running container with **Ctrl+C** (handled gracefully; see entrypoint note below).

## Architecture (the big picture)

`entrypoint.py` is PID 1 and a **dispatcher**: it reads `TEST_TYPE` and runs one of two
independent simulators as a child process:

- **firetest** (`firetest/firetest_run_all.py`) — a full TC–TM control loop:
  - `UdpStreamer` (thread) streams CCSDS sensor data over **UDP :40002**.
  - MQTT client (broker **:1883**) publishes the `TestFlag` (arm/finish) on `yamcs-tm-packets`
    and subscribes to `START_ENGINE` TCs on `yamcs-tc-packets`.
  - `Controller` ties them together: `TestFlag=1` + stream on, `TestFlag=0` + stop off.
  - `command` mode waits for operator TCs; `auto` mode self-drives ON→burst→OFF (optionally loops).
- **jetson** (`jetson/jetson_run_all.py`) — launches **every** `jetson/<TOPIC>.py` publisher as its
  own process; each streams one PX4/ROS2-shaped UDP packet. No MQTT, no control loop.

All runtime config is via **environment variables** (no config file needed); `load_config()` in
firetest centralizes them. Full table in `docs/deployment-guide.md`.

## Things you must know before editing

- **The CCSDS packet layout in `firetest/ccsds.py` is a cross-repo contract.** It must stay byte-
  for-byte in sync with the Yamcs preprocessors in `../rdp-yamcs-server`
  (`SimulatorCcsds{MQTT,UDP}PacketPreprocessor.java`). Key detail: generation time =
  `coarse` (Unix epoch **seconds**, bytes 6–9) + `fine` (**milliseconds** 0–999, bytes 10–11),
  decoded as `coarse*1000 + fine`. Changing the layout here breaks ingest there — verify both sides.

- **TC handling is deliberately decoupled from the paho network thread.** `on_message` only
  enqueues; a separate `tc_worker` thread publishes the QoS2 `TestFlag` and waits for its ack.
  Doing that wait inside `on_message` deadlocks (the network loop that must process the ack is
  blocked). Don't "simplify" this back into the callback.

- **MQTT connect retries with backoff** (`firetest_run_all.py`). UDP is connectionless so an
  unreachable target never raises — only the MQTT TCP connect surfaces reachability problems. A
  cold Tailscale peer link can exceed paho's 5s connect timeout on the first attempt; the retry
  warms it. Keep failures reporting a clear message + clean exit, not a raw traceback.

- **`entrypoint.py` runs the child via `Popen` + `wait` and swallows `KeyboardInterrupt`** so Ctrl+C
  shuts the child down gracefully without dumping a parent traceback. Don't revert to
  `subprocess.call`.

- **Generation-time accuracy depends on device↔Yamcs clock sync (NTP).** A negative/large
  reception-time delta is clock skew between machines, not a code bug.

## Conventions

- Runtime modules use `snake_case`; jetson topic files use `UPPER_SNAKE_CASE.py` matching their
  PX4/ROS2 topic names (keep this — it mirrors the source topics and stays greppable).
- The image is **secret-free**: the MQTT password is passed at runtime only; `config.json` is
  git-ignored.
- Deploy by **GitHub release tag** (`vMAJOR.MINOR.PATCH`); `run_device.sh` with a blank tag fetches
  the latest release. Conventional commits, no AI references.

## Wider context

This repo is the edge/telemetry node of a multi-repo platform. The workspace- and sub-workspace-
level `CLAUDE.md` files (`../../CLAUDE.md`, `../CLAUDE.md`) describe how it relates to
`rdp-yamcs-server`, `rdp-firetest-api`, and `rdp-firetest-fe`.
