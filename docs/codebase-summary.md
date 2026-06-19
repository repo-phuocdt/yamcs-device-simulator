# Codebase Summary

Small Python simulator packaged as a Docker image. Entry is `entrypoint.py`, which dispatches to
one of two test types. No build step — pure Python (`python:3.11-alpine` + `paho-mqtt`).

## Entry points & key files

| File | Role |
|------|------|
| `entrypoint.py` | Container PID 1. Reads `TEST_TYPE`, runs `firetest/firetest_run_all.py` or `jetson/jetson_run_all.py` as a child; waits and exits cleanly on Ctrl+C. |
| `run_device.sh` | Interactive launcher. Prompts for config, builds the image (from this folder in `local` mode, or from a cloned GitHub release tag), then `docker run` with all env vars. |
| `Dockerfile` | Installs `paho-mqtt==1.6.1`, copies `entrypoint.py` + `firetest/` + `jetson/`. No secrets baked in. |

### firetest/

| File | Role |
|------|------|
| `firetest_run_all.py` | Full TC–TM loop. `load_config()` reads env; `UdpStreamer` (thread) streams CCSDS sensor data; `Controller` ties `TestFlag` (MQTT) + UDP on/off; MQTT connect retries with backoff; `tc_worker` thread processes received TCs off the paho network thread. |
| `ccsds.py` | CCSDS codec. `build_data_packet()`, `build_testflag_packet()`, `decode_tc()`, `_header()`. Encodes generation time as coarse(epoch s) + fine(ms). APIDs: data 101, TestFlag 401, TC 400. |

### jetson/

| File | Role |
|------|------|
| `jetson_run_all.py` | Launches every `jetson/<TOPIC>.py` sibling as a child process; surfaces crashes; Ctrl+C stops all. |
| `<TOPIC>.py` (24 files) | One UDP publisher per PX4/ROS2 topic (e.g. `SENSOR_GPS.py`, `BATTERY_STATUS.py`, `VEHICLE_STATUS.py`). Each defines its own `PACKET_ID` + big-endian struct layout and streams to `YAMCS_HOST:YAMCS_PORT`. |

## Configuration surface

All runtime config is via environment variables (no config file required). See `deployment-guide.md`
for the full table. Required for firetest: `MQTT_USERNAME`, `MQTT_PASSWORD`.

## Concurrency model

- **firetest**: main thread + `UdpStreamer` thread + paho network thread + `tc_worker` thread.
  TC handling is decoupled from the paho thread to avoid QoS2 ack deadlock.
- **jetson**: launcher process + one child process per topic publisher.

## Conventions

- Python: `snake_case` for the runtime scripts (`firetest_run_all.py`, `ccsds.py`); jetson topic
  files use `UPPER_SNAKE_CASE` matching their PX4/ROS2 topic names.
- Module docstrings explain the packet contract and the *why* behind threading/timing choices.

## What's NOT here

- No automated test suite (verification is empirical — run the container against a Yamcs).
- No Yamcs config / MDB (that lives in `rdp-yamcs-server`).
- No CI pipeline file in-repo; deployment is by GitHub release tag.
