#!/bin/bash

echo "=========================================================="
echo "    YAMCS DEVICE RUNNER - DEPLOY BY GIT RELEASE (.SH)     "
echo "=========================================================="

# 1. USER CONFIGURATION (CHANGE YOUR GITHUB REPO HERE)
# FORMAT: https://github.com/USER_NAME/REPO_NAME.git
GIT_REPO_URL="https://github.com/repo-phuocdt/yamcs-device-simulator.git"

# Extract Owner and Repo name from URL for GitHub API usage
REPO_API_PATH=$(echo "$GIT_REPO_URL" | sed -E 's/https:\/\/github.com\///' | sed 's/\.git//')

# 2. DEFAULT CONFIGURATION VARIABLES
DEFAULT_TEST_TYPE="firetest"       # firetest (CCSDS single-value sensors) | jetson (PX4/ROS2 topics)
DEFAULT_SERVER_IP="10.254.5.153"   # Your Mac Yamcs Server IP
DEFAULT_SERVER_PORT=40002          # Destination UDP port
DEFAULT_APID=101                   # Application Process ID from MDB (firetest only)
DEFAULT_INTERVAL=0.5               # Telemetry stream interval, seconds (firetest only)
DEFAULT_MQTT_PORT=1883             # Yamcs Mosquitto port (firetest TestFlag/TC)
DEFAULT_MQTT_USER="test"           # Mosquitto username (firetest only)
DEFAULT_MODE="command"             # firetest mode: command (wait for TC) | auto (self-drive)
DEFAULT_DURATION=10                # auto-mode burst length, seconds
DEFAULT_LOOP="false"               # auto-mode repeat

# 3. INTERACTIVE USER INPUTS (PROMPTS)
echo "📝 Please configure your device environment (Press ENTER to use default value):"

# Prompt for Test Type
echo "🔹 Select test type:"
echo "     1) firetest  - CCSDS single-value sensors (rdp-firetest-poc / rdp-yamcs-server)"
echo "     2) jetson    - PX4/ROS2 topic publishers, all topics at once (rdp-yamcs-jetson)"
read -p "   Enter choice [1=firetest]: " USER_TYPE
case "$USER_TYPE" in
  2|jetson) TEST_TYPE="jetson" ;;
  *)        TEST_TYPE="firetest" ;;
esac

# Prompt for Yamcs Server IP
read -p "🔹 Enter Yamcs Server IP [$DEFAULT_SERVER_IP]: " USER_IP
SERVER_IP="${USER_IP:-$DEFAULT_SERVER_IP}"

# Prompt for UDP Port
read -p "🔹 Enter Destination UDP Port [$DEFAULT_SERVER_PORT]: " USER_PORT
SERVER_PORT="${USER_PORT:-$DEFAULT_SERVER_PORT}"

# Prompt for Release Tag (blank=latest release, or 'local' to build from this folder)
read -p "🔹 Enter GitHub Release Tag [blank='latest', 'local'=build from this folder]: " USER_TAG
RELEASE_TAG="$USER_TAG"

# firetest-only parameters (jetson publishers carry their own packet-id and rate).
# firetest drives Yamcs CSV recording via the MQTT TestFlag + receives START_ENGINE TC,
# so it also needs the Mosquitto port + credentials.
if [ "$TEST_TYPE" = "firetest" ]; then
  read -p "🔹 Enter Stream Interval in seconds [$DEFAULT_INTERVAL]: " USER_INTERVAL
  INTERVAL="${USER_INTERVAL:-$DEFAULT_INTERVAL}"
  read -p "🔹 Enter CCSDS APID [$DEFAULT_APID]: " USER_APID
  APID="${USER_APID:-$DEFAULT_APID}"
  read -p "🔹 Enter Yamcs MQTT Port [$DEFAULT_MQTT_PORT]: " USER_MQTT_PORT
  MQTT_PORT="${USER_MQTT_PORT:-$DEFAULT_MQTT_PORT}"
  read -p "🔹 Enter MQTT Username [$DEFAULT_MQTT_USER]: " USER_MQTT_USER
  MQTT_USER="${USER_MQTT_USER:-$DEFAULT_MQTT_USER}"
  # Password: use env MQTT_PASS if preset; in 'local' mode auto-read from the yamcs-firetest
  # container when left blank; otherwise prompt.
  if [ -n "${MQTT_PASS:-}" ]; then
    echo "🔹 MQTT Password: (from \$MQTT_PASS env)"
  else
    read -s -p "🔹 Enter MQTT Password (blank = auto-detect in local mode): " USER_MQTT_PASS
    echo
    MQTT_PASS="$USER_MQTT_PASS"
  fi
  if [ -z "$MQTT_PASS" ] && [ "$RELEASE_TAG" = "local" ] && command -v docker >/dev/null 2>&1; then
    MQTT_PASS=$(docker inspect yamcs-firetest --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null | sed -n 's/^MQTT_PASSWORD=//p')
    [ -n "$MQTT_PASS" ] && echo "🔹 MQTT Password: auto-detected from yamcs-firetest container"
  fi
  if [ -z "$MQTT_PASS" ]; then
    echo "❌ Error: firetest needs an MQTT password (set it at the prompt, or export MQTT_PASS=...)."
    exit 1
  fi
  echo "🔹 Select firetest mode:"
  echo "     1) command - wait for operator START_ENGINE On/Off (TC-driven)"
  echo "     2) auto    - self-drive TestFlag ON -> data -> OFF"
  read -p "   Enter choice [1=command]: " USER_MODE
  case "$USER_MODE" in
    2|auto) MODE="auto" ;;
    *)      MODE="command" ;;
  esac
  if [ "$MODE" = "auto" ]; then
    read -p "🔹 Auto burst duration seconds [$DEFAULT_DURATION]: " USER_DURATION
    DURATION="${USER_DURATION:-$DEFAULT_DURATION}"
    read -p "🔹 Loop continuously? (true/false) [$DEFAULT_LOOP]: " USER_LOOP
    case "${USER_LOOP:-$DEFAULT_LOOP}" in
      true|yes|1|y)  LOOP="true" ;;
      *)             LOOP="false" ;;
    esac
  else
    DURATION="$DEFAULT_DURATION"; LOOP="$DEFAULT_LOOP"
  fi
else
  INTERVAL="$DEFAULT_INTERVAL"; APID="$DEFAULT_APID"
  MQTT_PORT="$DEFAULT_MQTT_PORT"; MQTT_USER="$DEFAULT_MQTT_USER"; MQTT_PASS=""
  MODE="$DEFAULT_MODE"; DURATION="$DEFAULT_DURATION"; LOOP="$DEFAULT_LOOP"
fi

echo "----------------------------------------------------------"

DIR_NAME="yamcs-device-release-tmp"
CONTAINER_NAME="yamcs-device-$(date +%s)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Local mode: build from this folder instead of cloning a GitHub release (for dev/testing
# before a release exists). Triggered by tag 'local' or env LOCAL=1.
LOCAL_MODE=""
if [ "$RELEASE_TAG" = "local" ] || [ "${LOCAL:-}" = "1" ]; then
  LOCAL_MODE=1
fi

# 4. PREREQUISITES ENVIRONMENT CHECK
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker engine is not installed on this machine!"
    echo "👉 Please install Docker before running this script."
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo "❌ Error: Git client is not installed on this machine!"
    echo "👉 Please install Git (e.g., sudo apt install git)."
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo "❌ Error: Curl utility is not installed on this machine!"
    echo "👉 Please install Curl (e.g., sudo apt install curl)."
    exit 1
fi

# 5/6. RESOLVE SOURCE: local folder (dev/test) OR clone a GitHub release (client install)
if [ -n "$LOCAL_MODE" ]; then
    echo "🧪 LOCAL mode: building from this folder ($SCRIPT_DIR) — skipping GitHub clone."
    BUILD_DIR="$SCRIPT_DIR"
    IMAGE_TAG="local"
else
    # Auto-detect latest release tag if not provided
    if [ -z "$RELEASE_TAG" ]; then
        echo "🔍 No Release Tag specified. Fetching the latest release from GitHub API..."
        LATEST_TAG=$(curl -s "https://api.github.com/repos/${REPO_API_PATH}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"tag_name": "([^"]+)".*/\1/')
        if [ -z "$LATEST_TAG" ]; then
            echo "⚠️  Warning: Failed to fetch latest release tag via GitHub API."
            echo "👉 Trying to fallback to 'main' branch..."
            RELEASE_TAG="main"
        else
            RELEASE_TAG="$LATEST_TAG"
            echo "🎯 Latest release found: [ $RELEASE_TAG ]"
        fi
    else
        echo "🎯 Targeted specific release tag: [ $RELEASE_TAG ]"
    fi

    echo "🔄 Fetching release version [ $RELEASE_TAG ] from GitHub..."
    rm -rf "$DIR_NAME"
    if ! git clone --branch "$RELEASE_TAG" --depth 1 "$GIT_REPO_URL" "$DIR_NAME" 2>/dev/null; then
        echo "❌ Error: Release Tag '$RELEASE_TAG' not found on remote GitHub repository!"
        echo "👉 Ensure you have created and published this specific tag in your GitHub Release panel."
        exit 1
    fi
    BUILD_DIR="$DIR_NAME"
    IMAGE_TAG="$RELEASE_TAG"
fi

cd "$BUILD_DIR" || exit

echo "✅ Test type: $TEST_TYPE | Target -> $SERVER_IP (UDP $SERVER_PORT / MQTT $MQTT_PORT) | firetest mode=$MODE"

# 8. CONTAINERIZE WORKLOAD (DOCKER BUILD)
echo "📦 Building Docker image yamcs-device-sim:$IMAGE_TAG ..."
docker build -t "yamcs-device-sim:$IMAGE_TAG" .

# 9. INSTANTIATE WORKLOAD CONTAINER (DOCKER RUN)
# Config is passed via env vars (no file/mount, no secret baked into the image).
echo "🚀 Emulator started inside container [ $CONTAINER_NAME ] (Ctrl+C to stop)"
docker run --rm --name "$CONTAINER_NAME" \
  -e TEST_TYPE="$TEST_TYPE" \
  -e YAMCS_HOST="$SERVER_IP" \
  -e YAMCS_PORT="$SERVER_PORT" \
  -e MQTT_PORT="$MQTT_PORT" \
  -e MQTT_USERNAME="$MQTT_USER" \
  -e MQTT_PASSWORD="$MQTT_PASS" \
  -e APID="$APID" \
  -e SEND_INTERVAL_SECONDS="$INTERVAL" \
  -e MODE="$MODE" \
  -e DURATION_SECONDS="$DURATION" \
  -e LOOP="$LOOP" \
  "yamcs-device-sim:$IMAGE_TAG"

# 10. POST-RUN CLEANUP
if [ -z "$LOCAL_MODE" ]; then
    cd ..
    rm -rf "$DIR_NAME"
    echo "✨ Temporary release workspace wiped. Workspace cleaned."
else
    echo "✨ Local run finished (source folder left intact)."
fi