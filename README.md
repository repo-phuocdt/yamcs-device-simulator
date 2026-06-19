# YAMCS Device Simulator

A containerized telemetry device simulator for the **ISC RDP / Firetest / HILS** platform.
It emulates edge hardware that streams telemetry into a [Yamcs](https://yamcs.org) instance,
so you can exercise the ingest → recording → upload pipeline without real hardware.

Two test types share one image, selected at runtime via the `TEST_TYPE` env var:

| `TEST_TYPE` | Emulates | Transport | Drives |
|-------------|----------|-----------|--------|
| `firetest` (default) | cRIO fire-test sensors (CCSDS single-value) | UDP (data) + MQTT (control) | Yamcs CSV recording via the MQTT `TestFlag`; receives `START_ENGINE` TC |
| `jetson` | Jetson / PX4 / ROS2 topic publishers | UDP | One UDP publisher per topic, all at once |

## How it works

```
                          docker run -e TEST_TYPE=...
                                     │
                              entrypoint.py
                   ┌─────────────────┴─────────────────┐
            TEST_TYPE=firetest                   TEST_TYPE=jetson
                   │                                   │
        firetest/firetest_run_all.py        jetson/jetson_run_all.py
         │ UDP  CCSDS sensor data ─────▶ :40002 (UDP TM)   │ UDP  per-topic
         │ MQTT TestFlag (arm/finish) ─▶ :1883  (broker)   │      PX4/ROS2 packets ─▶ :40002
         └ MQTT START_ENGINE TC      ◀─ :1883              └  (BATTERY_STATUS, SENSOR_GPS, ...)
                                     │
                                  Yamcs instance (firetest)
```

- **firetest** runs a full TC–TM loop. In `command` mode it idles until the operator sends
  `START_ENGINE On/Off` from the Yamcs Web UI; `On` publishes `TestFlag` ON (arms CSV recording)
  and streams CCSDS sensor data over UDP, `Off` stops and publishes `TestFlag` OFF. In `auto`
  mode it self-drives the ON → burst → OFF cycle (optionally looping).
- **jetson** launches every `jetson/<TOPIC>.py` publisher at once, each streaming its own
  PX4/ROS2 packet over UDP.
- Packet generation time is encoded in the CCSDS secondary header with millisecond precision
  (`coarse` = Unix epoch seconds, `fine` = millisecond remainder), matching the Yamcs preprocessor.

## Requirements

- Docker
- Git, curl (for release-based deployment)
- A reachable Yamcs instance (UDP TM port `40002`; for firetest also MQTT broker `1883`)

## Quick start

```bash
./run_device.sh
```

The script is interactive — press ENTER to accept the default shown in brackets:

1. **Test type** — `firetest` or `jetson`
2. **Yamcs Server IP** — where to send telemetry
3. **UDP port** — destination for TM data (default `40002`)
4. **Release tag** — blank = latest GitHub release, `local` = build from this folder
5. **firetest only**: stream interval, CCSDS APID, MQTT port/username/password, mode
   (`command` / `auto`)

It then builds the Docker image and runs the container. Press **Ctrl+C** to stop.

### Local build (development)

To build from the working tree instead of fetching a release, answer `local` at the release-tag
prompt (or `export LOCAL=1`). In `local` mode the firetest MQTT password is auto-detected from a
running `yamcs-firetest` container if left blank.

### Run manually with Docker

```bash
docker build -t yamcs-device-sim:local .

# firetest (command mode)
docker run --rm \
  -e TEST_TYPE=firetest \
  -e YAMCS_HOST=10.254.5.153 -e YAMCS_PORT=40002 \
  -e MQTT_PORT=1883 -e MQTT_USERNAME=test -e MQTT_PASSWORD=*** \
  -e APID=101 -e MODE=command \
  yamcs-device-sim:local

# jetson
docker run --rm \
  -e TEST_TYPE=jetson \
  -e YAMCS_HOST=10.254.5.153 -e YAMCS_PORT=40002 \
  yamcs-device-sim:local
```

## Configuration (environment variables)

| Variable | Applies to | Default | Description |
|----------|-----------|---------|-------------|
| `TEST_TYPE` | both | `firetest` | `firetest` or `jetson` |
| `YAMCS_HOST` | both | `127.0.0.1` | Target Yamcs host (IP/hostname) |
| `YAMCS_PORT` | both | `40002` | UDP TM destination port |
| `MQTT_PORT` | firetest | `1883` | Yamcs MQTT broker port |
| `MQTT_USERNAME` | firetest | — (required) | MQTT username |
| `MQTT_PASSWORD` | firetest | — (required) | MQTT password (never baked into the image) |
| `APID` | firetest | `101` | CCSDS APID for sensor data (from the MDB) |
| `SENSOR_IDS` | firetest | `1,2,3,4,5,6` | Sensor packet IDs to stream |
| `SEND_INTERVAL_SECONDS` | firetest | `0.1` | UDP stream interval |
| `MODE` | firetest | `command` | `command` (TC-driven) or `auto` (self-drive) |
| `DURATION_SECONDS` | firetest | `10` | `auto` mode burst length |
| `LOOP` | firetest | `false` | `auto` mode: repeat continuously |
| `LOOP_GAP_SECONDS` | firetest | `2` | Gap between `auto` loops |

> Secrets are passed at runtime only — the image stays secret-free. The runtime `config.json`
> (if generated) holds the MQTT password and is git-ignored.

## Project layout

```
.
├── entrypoint.py              # dispatcher: picks firetest|jetson by TEST_TYPE
├── run_device.sh             # interactive build & run (local or GitHub release)
├── Dockerfile                # packages both test types (python:3.11-alpine + paho-mqtt)
├── firetest/
│   ├── firetest_run_all.py   # TC–TM loop, MQTT TestFlag/TC, UDP sensor stream
│   └── ccsds.py              # CCSDS codec (matches the Yamcs MDB + preprocessor)
└── jetson/
    ├── jetson_run_all.py     # launches every topic publisher at once
    └── <TOPIC>.py            # one UDP publisher per PX4/ROS2 topic
```

## Deployment

`run_device.sh` deploys by **GitHub release tag**: leave the tag blank to fetch the latest
release, or specify one (e.g. `v1.0.2`). The script clones the tagged source, builds the image,
and runs the container. See the
[Releases page](https://github.com/repo-phuocdt/yamcs-device-simulator/releases) for versions.

## Troubleshooting

- **`TimeoutError` / cannot reach broker** — the firetest MQTT connect retries with backoff and
  then reports a clear error. Verify `YAMCS_HOST`/`MQTT_PORT` are correct and the broker is
  running and reachable from inside the container.
- **Generation time looks off vs. reception time** — the device clock must be roughly synced
  with the Yamcs server clock (e.g. via NTP); the small reception-time delta is normal network
  latency, not a bug.
