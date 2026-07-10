import sys
sys.path.append('/usr/lib/python3/dist-packages')

import os
import time
import shutil
import subprocess
import re
from fastapi import FastAPI, BackgroundTasks, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import libtorrent as lt

app = FastAPI()

# 1. Broad global CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. FORCE CUSTOM INJECTION MIDDLEWARE FOR NGROK AND CORS BYPASS
@app.middleware("http")
async def add_custom_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        response = JSONResponse(content="OK")
    else:
        response = await call_next(request)
        
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

# Global tracking flags
is_pipeline_active = False

engine_status = {
    "status": "Sleeping",
    "name": "None",
    "progress": "0.00",
    "speed": "0.00",
    "peers": 0,
    "disk_free": "0.00",
    "upload_progress": "0",
    "upload_speed": "0 B/s",
    "upload_eta": "-"
}

def download_and_push_worker(magnet_link: str):
    global engine_status, is_pipeline_active
    rclone_errors = []
    
    try:
        engine_status["status"] = "Connecting to Swarm Network..."
        
        ses = lt.session()
        ses.listen_on(6881, 6891)
        
        local_path = '/tmp/downloads'
        os.makedirs(local_path, exist_ok=True)
        
        params = {'save_path': local_path, 'storage_mode': lt.storage_mode_t.storage_mode_sparse}
        handle = lt.add_magnet_uri(ses, magnet_link, params)
        
        while not handle.has_metadata():
            time.sleep(1)
            
        handle.set_flags(lt.torrent_flags.sequential_download)
        torrent_info = handle.get_torrent_info()
        torrent_name = torrent_info.name()
        engine_status["name"] = torrent_name
        engine_status["status"] = "Downloading on Cloud Instance..."
        
        while not handle.status().is_seeding:
            s = handle.status()
            engine_status["speed"] = f"{s.download_rate / (1024 * 1024):.2f}"
            engine_status["progress"] = f"{s.progress * 100:.2f}"
            engine_status["peers"] = s.num_peers
            
            _, _, free = shutil.disk_usage(local_path)
            engine_status["disk_free"] = f"{free / (1024**3):.2f}"
            time.sleep(2)
            
        engine_status["status"] = "Cloud download done! Transferring to Google Drive..."
        engine_status["speed"] = "0.00"
        engine_status["progress"] = "100.00"
        
        # Safely release the file lock so Rclone can read/copy it cleanly
        ses.remove_torrent(handle)
        time.sleep(2)
        
        source_dir = os.path.join(local_path, torrent_name)
        
        # Handle Single File vs Folder routing configurations for Google Drive
        if os.path.isfile(source_dir):
            dest_dir = "gdrive:CodespaceDownloads"
        else:
            dest_dir = f"gdrive:CodespaceDownloads/{torrent_name}"
        
        resolved_config_path = os.path.expanduser("~/.config/rclone/rclone.conf")
        
        rclone_cmd = [
            "rclone", "copy", source_dir, dest_dir, 
            "--config", resolved_config_path,
            "--transfers", "4", 
            "--multi-thread-streams", "8", 
            "--stats", "1s", 
            "-v",
            "--use-mmap"
        ]
        
        process = subprocess.Popen(
            rclone_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            bufsize=1
        )
        
        # Core Regex patterns
        progress_regex = re.compile(r"(\d{1,3})%")
        speed_regex = re.compile(r"(\d+(?:\.\d+)?\s*[a-zA-Z ]+/s)", re.IGNORECASE)
        eta_global_regex = re.compile(r"ETA\s+(\S+)", re.IGNORECASE)

        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
                
            if line:
                cleaned_line = line.strip()
                print(f"RCLONE OUT: {cleaned_line}", flush=True)
                
                if "ERROR" in cleaned_line or "Failed to" in cleaned_line:
                    rclone_errors.append(cleaned_line)
                
                # 🔥 FIXED: Only parse metrics if the line is the true global transfer summary line
                if "transferred:" in cleaned_line.lower() and "/s" in cleaned_line.lower():
                    prog_match = progress_regex.search(cleaned_line)
                    if prog_match:
                        engine_status["upload_progress"] = prog_match.group(1)
                    
                    speed_match = speed_regex.search(cleaned_line)
                    if speed_match:
                        engine_status["upload_speed"] = speed_match.group(1) 
                    
                    eta_match = eta_global_regex.search(cleaned_line)
                    if eta_match:
                        engine_status["upload_eta"] = eta_match.group(1)

        process.wait()
        exit_code = process.returncode
        
    except Exception as e:
        print(f"Subprocess wrapper failed: {str(e)}")
        exit_code = -1
        rclone_errors.append(str(e))
        
    # ⚡ SHUTDOWN AND CACHE FLUSH PATH
    if exit_code == 0:
        engine_status["status"] = "Success! Content securely saved in Google Drive."
        engine_status["upload_progress"] = "100"
        engine_status["upload_speed"] = "0 B/s"
        engine_status["upload_eta"] = "0s"
        
        print(f"🧹 Flushing storage from temporary cloud partition: {source_dir}")
        try:
            if os.path.isdir(source_dir):
                shutil.rmtree(source_dir)
            elif os.path.isfile(source_dir):
                os.remove(source_dir)
        except Exception as cleanup_error:
            print(f"⚠️ Cache flush warning: {str(cleanup_error)}")

        print("Upload finished perfectly. Handing control back to shell...")
        time.sleep(10)
        is_pipeline_active = False
        os.system("pkill -f uvicorn")
        return
    else:
        error_context = rclone_errors[-1] if rclone_errors else "Subprocess runtime fault."
        engine_status["status"] = f"❌ Upload Error: {error_context}"
        is_pipeline_active = False
        print(f"Upload failed: {error_context}. Keeping instance online for log troubleshooting.")

@app.post("/api/v1/enqueue")
def enqueue_link(background_tasks: BackgroundTasks, magnet_link: str = Form(...)):
    global is_pipeline_active
    if is_pipeline_active:
        return {"status": "ignored", "message": "Pipeline busy."}
        
    is_pipeline_active = True
    background_tasks.add_task(download_and_push_worker, magnet_link)
    return {"message": "Pipeline triggered successfully on cloud worker."}

@app.get("/api/v1/status")
def get_engine_status():
    return engine_status

@app.post("/api/v1/shutdown")
def kill_instance_server():
    def target_shutdown():
        time.sleep(2)
        os.system("pkill -f uvicorn")
    import threading
    threading.Thread(target=target_shutdown).start()
    return {"status": "Success"}