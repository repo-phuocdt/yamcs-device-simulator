#!/usr/bin/env python3
"""Container entrypoint: dispatch to the chosen test type, configured entirely via env vars.

  TEST_TYPE = "firetest" -> firetest/firetest_run_all.py  (CCSDS sensors + TestFlag/TC)
            = "jetson"   -> jetson/jetson_run_all.py       (all PX4/ROS2 topic publishers)

All other settings (YAMCS_HOST, YAMCS_PORT, MQTT_*, MODE, ...) are read from the environment
by the target script. No config file is needed — pass values with `docker run -e ...`.
"""
import os
import subprocess
import sys


def main():
    test_type = os.environ.get("TEST_TYPE", "firetest")
    if test_type == "firetest":
        target = "firetest/firetest_run_all.py"
    elif test_type == "jetson":
        target = "jetson/jetson_run_all.py"
    else:
        print(f"Unknown TEST_TYPE '{test_type}' (expected 'firetest' or 'jetson')", file=sys.stderr)
        sys.exit(2)

    print(f"▶️  TEST_TYPE = {test_type} -> {target}")
    sys.exit(subprocess.call([sys.executable, target]))


if __name__ == "__main__":
    main()
