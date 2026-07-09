# #!/bin/bash
# set -e

# # =========================================================================
# # 🔄 WORKSPACE SYNCHRONIZATION
# # =========================================================================
# cd /workspaces/cloud-extracter

# echo "🧼 Sanitizing previous background workers..."
# pkill -f uvicorn || true
# pkill -f ngrok || true
# sleep 2

# echo "🚀 Launching high-performance FastAPI server layer..."
# nohup python3 -m uvicorn server:app --host 0.0.0.0 --port 5000 > /tmp/server.log 2>&1 &

# echo "📡 Verification: Waiting for port 5000 socket binding..."
# for i in {1..30}; do
#     if ss -tulpn | grep ':5000' > /dev/null; then
#         echo "✅ SUCCESS: API Engine port 5000 is open and listening!"
#         break
#     fi
#     sleep 2
# done

# echo "🌐 Injecting secure external public Ngrok network tunnel..."
# nohup ngrok http --url=pristine-gizzard-dipped.ngrok-free.dev 5000 > /tmp/ngrok.log 2>&1 &

# # =========================================================================
# # 🛡️ SHIELD LOCKED UNTIL LOCAL SYNC CALL DROPS IN
# # =========================================================================
# echo "🛡️ Shield Activated: Locking execution shell open for local data streaming..."
# while true; do
#     if ! pgrep -f uvicorn > /dev/null; then
#         echo "🚨 Alert: API Server stopped processing requests. Breaking stay-alive shield..."
#         break
#     fi
    
#     echo "⏱️ Heartbeat Check: Direct cloud staging pipe actively serving connections..."
#     sleep 60
# done

# # =========================================================================
# # 🛑 AUTOMATED CLOSING SEQUENCE
# # =========================================================================
# echo "📥 Session Finished: Sync finalized perfectly. Collapsing cloud network..."
# pkill -f ngrok || true

# echo "🧼 Displaying last 20 lines of server log output for validation:"
# tail -n 20 /tmp/server.log || true

# echo "🔌 Disconnecting tunnel cleanly. Handing terminal control back to GitHub Actions..."
# exit 0

#!/bin/bash
set -e

# =========================================================================
# 🔄 WORKSPACE SYNCHRONIZATION
# =========================================================================
cd /workspaces/cloud-extracter

echo "📦 Syncing environment dependencies... Installing FastAPI and Uvicorn..."
python3 -m pip install --no-cache-dir fastapi uvicorn requests

echo "🧼 Sanitizing previous background workers..."
pkill -f uvicorn || true
pkill -f ngrok || true
sleep 2

echo "🚀 Launching high-performance FastAPI server layer..."
nohup python3 -m uvicorn server:app --host 0.0.0.0 --port 5000 > /tmp/server.log 2>&1 &

echo "📡 Verification: Waiting for port 5000 socket binding..."
for i in {1..30}; do
    if ss -tulpn | grep ':5000' > /dev/null; then
        echo "✅ SUCCESS: API Engine port 5000 is open and listening!"
        break
    fi
    sleep 2
done

echo "🌐 Injecting secure external public Ngrok network tunnel..."
nohup ngrok http --url=pristine-gizzard-dipped.ngrok-free.dev 5000 > /tmp/ngrok.log 2>&1 &

# =========================================================================
# 🛡️ SHIELD LOCKED UNTIL LOCAL SYNC CALL DROPS IN
# =========================================================================
echo "🛡️ Shield Activated: Locking execution shell open for local data streaming..."
while true; do
    if ! pgrep -f uvicorn > /dev/null; then
        echo "🚨 Alert: API Server stopped processing requests. Breaking stay-alive shield..."
        break
    fi
    
    echo "⏱️ Heartbeat Check: Direct cloud staging pipe actively serving connections..."
    sleep 60
done

# =========================================================================
# 🛑 AUTOMATED CLOSING SEQUENCE
# =========================================================================
echo "📥 Session Finished: Sync finalized perfectly. Collapsing cloud network..."
pkill -f ngrok || true

echo "🧼 Displaying last 20 lines of server log output for validation:"
tail -n 20 /tmp/server.log || true

echo "🔌 Disconnecting tunnel cleanly. Handing terminal control back to GitHub Actions..."
exit 0