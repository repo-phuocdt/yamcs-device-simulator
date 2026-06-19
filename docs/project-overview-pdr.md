# Project Overview — PDR

## What this is

**YAMCS Device Simulator** — a containerized telemetry device simulator for the
**ISC (Innovative Space Carrier) RDP / Firetest / HILS** platform. It emulates edge hardware
that streams telemetry into a [Yamcs](https://yamcs.org) instance, letting the team exercise the
ingest → recording → upload pipeline without physical hardware.

It sits at the **edge / telemetry** tier of the RDP platform, standing in for the real devices
that feed the `rdp-yamcs-server` Yamcs instance.

## Goals

- Provide a single, reusable Docker image that can emulate **two device families**:
  - **firetest** — cRIO fire-test sensors (CCSDS single-value packets) with a full TC–TM control loop.
  - **jetson** — Jetson / PX4 / ROS2 topic publishers.
- Make device runs **repeatable and parameterized** entirely through environment variables.
- Keep the image **secret-free** — broker credentials are supplied only at runtime.
- Ship via **GitHub release tags** so operators can run a known version with one script.

## Non-goals

- Not a production telemetry source — it generates randomized/synthetic values.
- Does not run or configure Yamcs itself (that is `rdp-yamcs-server`).
- Does not talk to the Firetest cloud API directly (that path lives in the Yamcs server).

## Users

- **RDP engineers** validating Yamcs ingest, CSV recording, and the `TestFlag`/`START_ENGINE`
  control loop locally or against a teammate's Yamcs over Tailscale.
- **QA / integration** reproducing telemetry scenarios for the firetest and jetson pipelines.

## Scope (current)

| Capability | Status |
|------------|--------|
| firetest CCSDS sensor streaming (UDP) | ✅ |
| firetest MQTT `TestFlag` arm/finish + `START_ENGINE` TC | ✅ |
| firetest `command` and `auto` modes | ✅ |
| firetest MQTT connect retry with backoff | ✅ |
| jetson per-topic UDP publishers (run-all) | ✅ |
| Interactive `run_device.sh` (local + release build) | ✅ |
| Clean Ctrl+C shutdown | ✅ |

## Relationship to the RDP platform

```
this repo (device sim)  ──UDP TM / MQTT──▶  rdp-yamcs-server (Yamcs instance "firetest")
                                                   │ CSV sequence + _meta.json
                                                   ▼
                                            rdp-firetest-api (hub) ──▶ batch analytics
```

The simulator's CCSDS packet layout and time encoding are a **contract** with the Yamcs server's
preprocessor — see `system-architecture.md`.
