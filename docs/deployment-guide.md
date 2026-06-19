# Deployment Guide

## Prerequisites

- Docker
- Git, curl (for release-based deployment)
- A reachable Yamcs instance: UDP TM port `40002`; for firetest also MQTT broker `1883`

## Option A — Interactive (`run_device.sh`)

```bash
./run_device.sh
```

Prompts (ENTER accepts the bracketed default):

1. **Test type** — `firetest` or `jetson`
2. **Yamcs Server IP** — telemetry target
3. **UDP port** — TM destination (default `40002`)
4. **Release tag** — blank = latest GitHub release · `local` = build from this folder
5. **firetest only** — stream interval, APID, MQTT port/user/password, mode (`command`/`auto`),
   and (auto) burst duration + loop

The script builds the image and runs the container. **Ctrl+C** stops it.

### Local build (development)

Answer `local` at the release-tag prompt (or `export LOCAL=1`) to build from the working tree.
In `local` mode, if the firetest MQTT password is left blank it is auto-detected from a running
`yamcs-firetest` container.

## Option B — Manual Docker

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

## Environment variables

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
| `SEND_INTERVAL_SECONDS` | firetest | `0.1` | UDP stream interval (seconds) |
| `MODE` | firetest | `command` | `command` (TC-driven) or `auto` (self-drive) |
| `DURATION_SECONDS` | firetest | `10` | `auto` burst length |
| `LOOP` | firetest | `false` | `auto`: repeat continuously |
| `LOOP_GAP_SECONDS` | firetest | `2` | gap between `auto` loops |

## Releases

Deployment is by **GitHub release tag**. The current scheme: `vMAJOR.MINOR.PATCH`
(e.g. `v1.0.2`). Leave the tag blank in `run_device.sh` to fetch the latest release.

Releases: https://github.com/repo-phuocdt/yamcs-device-simulator/releases

To cut a release: commit to `main`, create an annotated tag, push it, and publish a GitHub
release (e.g. via `gh release create vX.Y.Z --latest`).

## Security

- Broker credentials are passed **at runtime only**; the image stays secret-free.
- The runtime `config.json` (if generated) holds the MQTT password and is **git-ignored**.

## Troubleshooting

| Symptom | Likely cause / action |
|---------|----------------------|
| `TimeoutError` / `cannot reach broker` | Wrong `YAMCS_HOST`/`MQTT_PORT`, broker down, or cold Tailscale link. Connect retries with backoff then reports clearly; verify reachability from inside the container. |
| firetest exits "MQTT_USERNAME and MQTT_PASSWORD are required" | Provide both via `-e` / the prompt. |
| Generation time ≈ reception time but offset looks wrong | Device clock not synced with Yamcs server — fix via NTP. The small +N ms reception delta is normal latency. |
| Ctrl+C prints a traceback | Fixed in v1.0.2 — update to the latest release. |
