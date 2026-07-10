# #!/bin/bash
# set -e

# # =========================================================================
# # 🔄 WORKSPACE INITIALIZATION & DEPENDENCY SYNC
# # =========================================================================
# cd /workspaces/cloud-extracter

# echo "📋 Phase 1: Validating system package core dependencies..."
# sudo apt-get update

# # Install native BitTorrent core bindings if missing
# if ! python3 -c "import sys; sys.path.append('/usr/lib/python3/dist-packages'); import libtorrent" &> /dev/null; then
#     echo "📥 Installing python3-libtorrent system architecture..."
#     sudo apt-get install -y python3-libtorrent
# fi

# # Install Ngrok CLI framework if missing
# if ! command -v ngrok &> /dev/null; then
#     echo "📥 Installing Ngrok proxy agent cli..."
#     curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
#     echo "deb https://ngrok-agent.s3.amazonaws.com bookworm main" | sudo tee /etc/apt/sources.list.d/ngrok.list
#     sudo apt-get update && sudo apt-get install -y ngrok
# fi

# echo "🔑 Phase 2: Updating Ngrok account token authorization handshake..."
# ngrok config add-authtoken 3GIOravQQQVRlLEnE1UITst171V_3LJw19nNDkcv7WdLDMev

# echo "📦 Phase 3: Synchronizing python environment libraries..."
# python3 -m pip install --no-cache-dir fastapi uvicorn requests python-multipart

# echo "🧼 Phase 4: Purging historical network processing workers..."
# pkill -f uvicorn || true
# pkill -f ngrok || true
# sleep 2

# echo "🚀 Phase 5: Launching API Engine layer on port 5000..."
# nohup python3 -m uvicorn server:app --host 0.0.0.0 --port 5000 > /tmp/server.log 2>&1 &

# echo "📡 Phase 6: Confirming server port status allocation..."
# for i in {1..30}; do
#     if ss -tulpn | grep ':5000' > /dev/null; then
#         echo "✅ SUCCESS: API Core active on port 5000."
#         break
#     fi
#     sleep 2
# done

# echo "🌐 Phase 7: Spawning Ngrok Dashboard Communication Tunnel..."
# nohup ngrok http --url=worrier-verbose-blustery.ngrok-free.dev 5000 > /tmp/ngrok.log 2>&1 &

# # =========================================================================
# # 🛡️ THE STAY-ALIVE SHIELD
# # =========================================================================
# echo "🛡️ Shield Activated: Guarding active container environment shell..."
# while true; do
#     if ! pgrep -f uvicorn > /dev/null; then
#         echo "🚨 Alert: API Server stopped processing requests. Collapsing..."
#         break
#     fi
#     sleep 60
# done

# pkill -f ngrok || true
# exit 0





#!/bin/bash
set -e

# =========================================================================
# 🔄 WORKSPACE INITIALIZATION & DEPENDENCY SYNC
# =========================================================================
# Targets the correct workspace directory configuration layout
cd /workspaces/cloud-extracter

echo "📋 Phase 1: Validating system package core dependencies..."
sudo apt-get update

# Install native BitTorrent core bindings if missing
if ! python3 -c "import sys; sys.path.append('/usr/lib/python3/dist-packages'); import libtorrent" &> /dev/null; then
    echo "📥 Installing python3-libtorrent system architecture..."
    sudo apt-get install -y python3-libtorrent
fi

# Install Ngrok CLI framework if missing
if ! command -v ngrok &> /dev/null; then
    echo "📥 Installing Ngrok proxy agent cli..."
    curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
    echo "deb https://ngrok-agent.s3.amazonaws.com bookworm main" | sudo tee /etc/apt/sources.list.d/ngrok.list
    sudo apt-get update && sudo apt-get install -y ngrok
fi

# Install high-speed cloud rclone extraction binaries if missing
if ! command -v rclone &> /dev/null; then
    echo "📥 Installing high-speed rclone pipeline engine..."
    curl https://rclone.org/install.sh | sudo bash
fi

echo "🔑 Phase 2: Updating Ngrok account token authorization handshake..."
ngrok config add-authtoken 3GIOravQQQVRlLEnE1UITst171V_3LJw19nNDkcv7WdLDMev

echo "📦 Phase 3: Synchronizing python environment libraries..."
python3 -m pip install --no-cache-dir fastapi uvicorn requests python-multipart

echo "🧼 Phase 4: Purging historical network processing workers..."
pkill -f uvicorn || true
pkill -f ngrok || true
sleep 2

echo "🚀 Phase 5: Launching API Engine layer on port 5000..."
nohup python3 -m uvicorn server:app --host 0.0.0.0 --port 5000 > /tmp/server.log 2>&1 &

echo "📡 Phase 6: Confirming server port status allocation..."
for i in {1..30}; do
    if ss -tulpn | grep ':5000' > /dev/null; then
        echo "✅ SUCCESS: API Core active on port 5000."
        break
    fi
    sleep 2
done

echo "🌐 Phase 7: Spawning Ngrok Dashboard Communication Tunnel..."
nohup ngrok http --url=worrier-verbose-blustery.ngrok-free.dev 5000 > /tmp/ngrok.log 2>&1 &

# =========================================================================
# 🛡️ THE STAY-ALIVE SHIELD: KEEPS INSTANCE ALIVE DURING EXTRACTS
# =========================================================================
echo "🛡️ Shield Activated: Guarding active container environment shell..."
while true; do
    # Check if uvicorn is still running (Python script shuts down after upload completes)
    if ! pgrep -f uvicorn > /dev/null; then
        echo "🚨 Alert: API Server stopped processing requests. Collapsing lock loop..."
        break
    fi
    
    echo "Keep-Alive Heartbeat: Transfer processing via /tmp partition..."
    sleep 60
done

# =========================================================================
# 🛑 AUTOMATED CLOSING SEQUENCE & DIAGNOSTIC LOGGING
# =========================================================================
echo "----- Last 50 lines of server.log (Checking Uvicorn exit status) -----"
tail -n 50 /tmp/server.log || true

echo "Upload complete! Python server detached. Sending termination signals..."
pkill -f ngrok || true

echo "Closing connection cleanly. Handing control back to GitHub Actions..."
exit 0