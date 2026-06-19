# Code Standards

## Language & runtime

- Python 3.11 (runs on `python:3.11-alpine`). Standard library only, except `paho-mqtt==1.6.1`.
- Shell: POSIX-ish Bash for `run_device.sh`.

## Naming

- Runtime Python modules: `snake_case` (`firetest_run_all.py`, `jetson_run_all.py`, `ccsds.py`).
- jetson topic publishers: `UPPER_SNAKE_CASE.py` matching their PX4/ROS2 topic names
  (`SENSOR_GPS.py`, `VEHICLE_STATUS.py`). This mirrors the source topics and keeps them greppable.
- Env vars: `UPPER_SNAKE_CASE` (`YAMCS_HOST`, `MQTT_PASSWORD`).

## Configuration

- All runtime config comes from **environment variables** — no config file is required and none is
  baked into the image. `load_config()` centralizes reads and applies defaults.
- **Never** hardcode secrets. The MQTT password is supplied at runtime; `config.json` is git-ignored.

## Comments & docstrings

- Every module has a docstring describing its responsibility and, where relevant, the **packet
  contract** (byte layout, APIDs) and the **why** behind non-obvious choices.
- Comments explain *why*, not *what* — e.g. why TC handling is decoupled from the paho network
  thread (QoS2 ack deadlock), why MQTT connect retries (cold link / unreachable broker).
- Do not reference plan/phase/finding labels in code comments — keep them self-contained.

## Error handling & robustness

- Fail fast with a clear message on missing required config (`SystemExit`).
- Network operations that can hang or fail (MQTT connect) must **retry with backoff** and then
  report a clear, actionable error instead of crashing with a raw traceback.
- Handle `SIGINT`/`SIGTERM` for graceful shutdown; the parent process must not dump a
  `KeyboardInterrupt` traceback on Ctrl+C.

## Concurrency

- Use threads for concurrent I/O in firetest; keep blocking work (QoS2 ack waits) off the paho
  network thread via a queue + worker thread.
- Guard shared on/off state with a lock; make on/off transitions idempotent.

## The CCSDS contract is sacred

- The packet byte layout and time encoding in `ccsds.py` **must stay in sync** with the Yamcs
  preprocessor in `rdp-yamcs-server`. Any change here is a cross-repo contract change — verify the
  decoder side before merging.

## Modularization

- Keep files focused. firetest logic is split into `firetest_run_all.py` (orchestration) and
  `ccsds.py` (codec). jetson keeps one file per topic.

## Commits & releases

- Conventional commits (`feat:`, `fix:`, ...). No AI references in messages.
- Releases use `vMAJOR.MINOR.PATCH` annotated tags + GitHub releases.
- Do not commit secrets or the runtime `config.json`.

## Verification

- No automated test suite. Verify changes empirically: build the image and run it against a Yamcs
  instance (or decode a generated packet with the same formula the Yamcs preprocessor uses).
