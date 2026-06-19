# Project Roadmap

## Current state — v1.0.2

| Area | Status |
|------|--------|
| Multi-test-type dispatcher (`entrypoint.py`) | ✅ Done |
| firetest: CCSDS sensors + TestFlag/TC loop, command & auto modes | ✅ Done |
| firetest: resilient MQTT connect (retry + backoff) | ✅ Done (v1.0.1) |
| jetson: per-topic UDP publishers (run-all) | ✅ Done |
| Interactive `run_device.sh` (local + release build) | ✅ Done |
| Clean Ctrl+C shutdown | ✅ Done (v1.0.2) |
| Project documentation (`docs/`, `README.md`) | ✅ Done |

## Release history

| Version | Highlights |
|---------|-----------|
| `v1.0.0` | Initial single-file simulator (`setup_and_run.py`). |
| `v1.0.1` | Restructure into dispatcher + `firetest/` + `jetson/`; resilient MQTT connect. |
| `v1.0.2` | Clean Ctrl+C shutdown in the entrypoint. |

## Candidate next steps (unprioritized)

- **jetson selectivity** — run a subset of topics (env-driven include/exclude) instead of all.
- **firetest realism** — configurable value profiles per sensor (ramps, noise bands) beyond
  uniform random.
- **Health/heartbeat** — optional liveness output / exit codes for orchestration.
- **CI** — pipeline to build + publish the image / release on tag (currently manual via `gh`).
- **Smoke test** — a lightweight script that decodes a generated packet against the Yamcs
  preprocessor formula, to guard the CCSDS contract.
- **Config parity check** — assert simulator APIDs/packet-ids match the Yamcs MDB before run.

## Known constraints

- No automated test suite — verification is empirical.
- CCSDS layout is a cross-repo contract with `rdp-yamcs-server`; changes need both sides verified.
- Generation-time accuracy depends on device↔server clock sync (NTP).

## Unresolved questions

- Target deployment environment for releases (operator laptops over Tailscale vs. fixed edge host)?
- Should jetson gain an MQTT control loop like firetest, or stay UDP-only?
