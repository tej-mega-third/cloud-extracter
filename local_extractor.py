import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# =========================================================================
# 🔥 LOCAL CONFIGURATION ZONE
# =========================================================================
BACKEND_URL = "https://pristine-gizzard-dipped.ngrok-free.dev"
LOCAL_OUTPUT_DIR = r"C:\CodespaceDownloads"  
MAX_DOWNLOAD_WORKERS = 8                    
# =========================================================================

def check_cloud_status():
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/status", headers={"ngrok-skip-browser-warning": "true"}, timeout=5)
        if response.ok:
            return response.json()
    except Exception:
        pass
    return None

def download_file_shard(base_url, file_info):
    rel_path = file_info["rel_path"]
    total_size = file_info["size"]
    
    local_file_path = os.path.join(LOCAL_OUTPUT_DIR, rel_path)
    os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
    
    encoded_rel_path = requests.utils.quote(rel_path)
    download_url = f"{base_url.rstrip('/')}/{encoded_rel_path.lstrip('/')}"
    
    print(f"📥 Thread spawning for: {os.path.basename(rel_path)} ({total_size / (1024*1024):.2f} MB)")
    
    try:
        with requests.get(download_url, headers={"ngrok-skip-browser-warning": "true"}, stream=True, timeout=15) as r:
            r.raise_for_status()
            with open(local_file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception as e:
        print(f"❌ Error downloading file block {rel_path}: {e}")
        return False

def trigger_cloud_collapse():
    print("\n🔌 Ingestion complete! Launching cloud power-down handshake...")
    try:
        res = requests.post(f"{BACKEND_URL}/api/v1/shutdown", headers={"ngrok-skip-browser-warning": "true"}, timeout=5)
        if res.ok:
            print("💤 SUCCESS: Cloud instance uvicorn stack killed. Billing stopped.")
        else:
            print("⚠️ Shutdown endpoint returned status error. Check GitHub console.")
    except Exception as e:
        print(f"💤 Link broken as expected. Cloud node is now powering off.")

def main():
    print("🛰️ Intelligent Local Extraction Engine Initialized.")
    print(f"Checking state on proxy endpoint: {BACKEND_URL}")
    os.makedirs(LOCAL_OUTPUT_DIR, exist_ok=True)
    
    while True:
        status = check_cloud_status()
        if not status:
            print("⏳ Tunnel synchronization offline... Retrying in 10s...")
        else:
            stage = status.get("status", "Unknown")
            progress = status.get("progress", "0.00")
            print(f"🛰️ Cloud State: [{stage}] - Progress: {progress}%")
            
            if status.get("ready_for_local_sync"):
                print("\n🚀 ALERT: Cloud staging is finalized! Mapping manifest tree...")
                break
                
        time.sleep(10)
        
    try:
        manifest_res = requests.get(f"{BACKEND_URL}/api/v1/directory", headers={"ngrok-skip-browser-warning": "true"})
        manifest_res.raise_for_status()
        manifest_data = manifest_res.json()
    except Exception as e:
        print(f"❌ Fatal Error: Failed to extract file structural layout map from API: {e}")
        return

    target_name = manifest_data.get("target_name", "Extracted_Dataset")
    files_to_download = manifest_data.get("files", [])
    download_base_url = f"{BACKEND_URL.rstrip('/')}{manifest_data.get('download_prefix', '/files/')}"
    total_files = len(files_to_download)
    
    print(f"📋 Manifest verified! Target: {target_name}")
    print(f"📦 Total payload contains {total_files} file shards. Spinning up parallel pipeline...")
    
    start_time = time.time()
    success_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS) as executor:
        futures = {executor.submit(download_file_shard, download_base_url, f_info): f_info for f_info in files_to_download}
        
        for idx, future in enumerate(as_completed(futures), 1):
            f_info = futures[future]
            if future.result():
                success_count += 1
                print(f"✅ Sync Progress: [{idx}/{total_files}] files saved.")
            else:
                print(f"❌ Sync Failure on file: {f_info['rel_path']}")

    end_time = time.time()
    print(f"\n🎉 Multi-threaded download execution finalized in {int(end_time - start_time)} seconds.")
    print(f"📊 Result status: Saved {success_count} out of {total_files} elements inside {LOCAL_OUTPUT_DIR}.")
    
    trigger_cloud_collapse()

if __name__ == "__main__":
    main()