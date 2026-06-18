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
DEFAULT_SERVER_IP="10.254.5.153"   # Your Mac Yamcs Server IP
DEFAULT_SERVER_PORT=40002          # Destination UDP port
DEFAULT_APID=101                   # Application Process ID from MDB
DEFAULT_INTERVAL=0.5               # Telemetry stream interval (seconds)

# 3. INTERACTIVE USER INPUTS (PROMPTS)
echo "📝 Please configure your device environment (Press ENTER to use default value):"

# Prompt for Yamcs Server IP
read -p "🔹 Enter Yamcs Server IP [$DEFAULT_SERVER_IP]: " USER_IP
SERVER_IP="${USER_IP:-$DEFAULT_SERVER_IP}"

# Prompt for UDP Port
read -p "🔹 Enter Destination UDP Port [$DEFAULT_SERVER_PORT]: " USER_PORT
SERVER_PORT="${USER_PORT:-$DEFAULT_SERVER_PORT}"

# Prompt for Release Tag (Leave blank for latest)
read -p "🔹 Enter GitHub Release Tag [Leave blank for 'latest']: " USER_TAG
RELEASE_TAG="$USER_TAG"

# Prompt for Telemetry Stream Interval
read -p "🔹 Enter Stream Interval in seconds [$DEFAULT_INTERVAL]: " USER_INTERVAL
INTERVAL="${USER_INTERVAL:-$DEFAULT_INTERVAL}"

# Prompt for APID
read -p "🔹 Enter CCSDS APID [$DEFAULT_APID]: " USER_APID
APID="${USER_APID:-$DEFAULT_APID}"

echo "----------------------------------------------------------"

DIR_NAME="yamcs-device-release-tmp"
CONTAINER_NAME="yamcs-device-$(date +%s)"

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

# 5. AUTO DETECT LATEST RELEASE TAG IF NOT PROVIDED
if [ -z "$RELEASE_TAG" ]; then
    echo "🔍 No Release Tag specified. Fetching the latest release from GitHub API..."

    # Query GitHub API to get the latest release tag name without needing jq installed
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

# 6. CLONE TARGET RELEASE FROM GITHUB
echo "🔄 Fetching release version [ $RELEASE_TAG ] from GitHub..."
rm -rf "$DIR_NAME"

# Pull only the single specified tag branch to minimize bandwidth
if ! git clone --branch "$RELEASE_TAG" --depth 1 "$GIT_REPO_URL" "$DIR_NAME" 2>/dev/null; then
    echo "❌ Error: Release Tag '$RELEASE_TAG' not found on remote GitHub repository!"
    echo "👉 Ensure you have created and published this specific tag in your GitHub Release panel."
    exit 1
fi

cd "$DIR_NAME" || exit

# 7. GENERATE ENVIRONMENT SPECIFIC LOCAL CONFIG FILE
cat <<EOF > config.json
{
    "yamcs_ip": "$SERVER_IP",
    "yamcs_port": $SERVER_PORT,
    "apid": $APID,
    "send_interval_seconds": $INTERVAL
}
EOF
echo "✅ Configuration targeted to -> $SERVER_IP:$SERVER_PORT (Interval: ${INTERVAL}s, APID: ${APID})"

# 8. CONTAINERIZE WORKLOAD (DOCKER BUILD)
echo "📦 Building local Docker Image for version $RELEASE_TAG..."
docker build -t "yamcs-device-sim:$RELEASE_TAG" .

# 9. INSTANTIATE WORKLOAD CONTAINER (DOCKER RUN)
echo "🚀 Emulator started successfully inside Container [ $CONTAINER_NAME ]!"
echo "--- (Press Ctrl+C to terminate execution and wipe workspace) ---"
docker run --rm --name "$CONTAINER_NAME" "yamcs-device-sim:$RELEASE_TAG"

# 10. AUTOMATED POST-RUN WORKSPACE CLEANUP
cd ..
rm -rf "$DIR_NAME"
echo "✨ Local temporary directory wiped. Workspace cleaned."