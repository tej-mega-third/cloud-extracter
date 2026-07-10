# import sys
# sys.path.append('/usr/lib/python3/dist-packages')

# import os
# import time
# import shutil
# import subprocess
# import re
# from fastapi import FastAPI, BackgroundTasks, Form, Request
# from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
# import libtorrent as lt

# app = FastAPI()

# # 1. Broad global CORS settings
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # 2. FORCE CUSTOM INJECTION MIDDLEWARE FOR NGROK AND CORS BYPASS
# @app.middleware("http")
# async def add_custom_headers(request: Request, call_next):
#     if request.method == "OPTIONS":
#         response = JSONResponse(content="OK")
#     else:
#         response = await call_next(request)
        
#     response.headers["Access-Control-Allow-Origin"] = "*"
#     response.headers["Access-Control-Allow-Methods"] = "*"
#     response.headers["Access-Control-Allow-Headers"] = "*"
#     response.headers["ngrok-skip-browser-warning"] = "true"
#     return response

# # Global tracking flags
# is_pipeline_active = False

# engine_status = {
#     "status": "Sleeping",
#     "name": "None",
#     "progress": "0.00",
#     "speed": "0.00",
#     "peers": 0,
#     "disk_free": "0.00",
#     "upload_progress": "0",
#     "upload_speed": "0 B/s",
#     "upload_eta": "-"
# }

# def download_and_push_worker(magnet_link: str):
#     global engine_status, is_pipeline_active
#     rclone_errors = []
    
#     try:
#         engine_status["status"] = "Connecting to Swarm Network..."
        
#         ses = lt.session()
#         ses.listen_on(6881, 6891)
        
#         local_path = '/tmp/downloads'
#         os.makedirs(local_path, exist_ok=True)
        
#         params = {'save_path': local_path, 'storage_mode': lt.storage_mode_t.storage_mode_sparse}
#         handle = lt.add_magnet_uri(ses, magnet_link, params)
        
#         while not handle.has_metadata():
#             time.sleep(1)
            
#         handle.set_flags(lt.torrent_flags.sequential_download)
#         torrent_info = handle.get_torrent_info()
#         torrent_name = torrent_info.name()
#         engine_status["name"] = torrent_name
#         engine_status["status"] = "Downloading on Cloud Instance..."
        
#         while not handle.status().is_seeding:
#             s = handle.status()
#             engine_status["speed"] = f"{s.download_rate / (1024 * 1024):.2f}"
#             engine_status["progress"] = f"{s.progress * 100:.2f}"
#             engine_status["peers"] = s.num_peers
            
#             _, _, free = shutil.disk_usage(local_path)
#             engine_status["disk_free"] = f"{free / (1024**3):.2f}"
#             time.sleep(2)
            
#         engine_status["status"] = "Cloud download done! Transferring to Google Drive..."
#         engine_status["speed"] = "0.00"
#         engine_status["progress"] = "100.00"
        
#         # Safely release the file lock so Rclone can read/copy it cleanly
#         ses.remove_torrent(handle)
#         time.sleep(2)
        
#         source_dir = os.path.join(local_path, torrent_name)
        
#         # Handle Single File vs Folder routing configurations for Google Drive
#         if os.path.isfile(source_dir):
#             dest_dir = "gdrive:CodespaceDownloads"
#         else:
#             dest_dir = f"gdrive:CodespaceDownloads/{torrent_name}"
        
#         resolved_config_path = os.path.expanduser("~/.config/rclone/rclone.conf")
        
#         rclone_cmd = [
#             "rclone", "copy", source_dir, dest_dir, 
#             "--config", resolved_config_path,
#             "--transfers", "4", 
#             "--multi-thread-streams", "8", 
#             "--stats", "1s", 
#             "-v",
#             "--use-mmap"
#         ]
        
#         process = subprocess.Popen(
#             rclone_cmd, 
#             stdout=subprocess.PIPE, 
#             stderr=subprocess.STDOUT, 
#             text=True, 
#             bufsize=1
#         )
        
#         # Core Regex patterns
#         progress_regex = re.compile(r"(\d{1,3})%")
#         speed_regex = re.compile(r"(\d+(?:\.\d+)?\s*[a-zA-Z ]+/s)", re.IGNORECASE)
#         eta_global_regex = re.compile(r"ETA\s+(\S+)", re.IGNORECASE)

#         while True:
#             line = process.stdout.readline()
#             if not line and process.poll() is not None:
#                 break
                
#             if line:
#                 cleaned_line = line.strip()
#                 print(f"RCLONE OUT: {cleaned_line}", flush=True)
                
#                 if "ERROR" in cleaned_line or "Failed to" in cleaned_line:
#                     rclone_errors.append(cleaned_line)
                
#                 # 🔥 FIXED: Only parse metrics if the line is the true global transfer summary line
#                 if "transferred:" in cleaned_line.lower() and "/s" in cleaned_line.lower():
#                     prog_match = progress_regex.search(cleaned_line)
#                     if prog_match:
#                         engine_status["upload_progress"] = prog_match.group(1)
                    
#                     speed_match = speed_regex.search(cleaned_line)
#                     if speed_match:
#                         engine_status["upload_speed"] = speed_match.group(1) 
                    
#                     eta_match = eta_global_regex.search(cleaned_line)
#                     if eta_match:
#                         engine_status["upload_eta"] = eta_match.group(1)

#         process.wait()
#         exit_code = process.returncode
        
#     except Exception as e:
#         print(f"Subprocess wrapper failed: {str(e)}")
#         exit_code = -1
#         rclone_errors.append(str(e))
        
#     # ⚡ SHUTDOWN AND CACHE FLUSH PATH
#     if exit_code == 0:
#         engine_status["status"] = "Success! Content securely saved in Google Drive."
#         engine_status["upload_progress"] = "100"
#         engine_status["upload_speed"] = "0 B/s"
#         engine_status["upload_eta"] = "0s"
        
#         print(f"🧹 Flushing storage from temporary cloud partition: {source_dir}")
#         try:
#             if os.path.isdir(source_dir):
#                 shutil.rmtree(source_dir)
#             elif os.path.isfile(source_dir):
#                 os.remove(source_dir)
#         except Exception as cleanup_error:
#             print(f"⚠️ Cache flush warning: {str(cleanup_error)}")

#         print("Upload finished perfectly. Handing control back to shell...")
#         time.sleep(10)
#         is_pipeline_active = False
#         os.system("pkill -f uvicorn")
#         return
#     else:
#         error_context = rclone_errors[-1] if rclone_errors else "Subprocess runtime fault."
#         engine_status["status"] = f"❌ Upload Error: {error_context}"
#         is_pipeline_active = False
#         print(f"Upload failed: {error_context}. Keeping instance online for log troubleshooting.")

# @app.post("/api/v1/enqueue")
# def enqueue_link(background_tasks: BackgroundTasks, magnet_link: str = Form(...)):
#     global is_pipeline_active
#     if is_pipeline_active:
#         return {"status": "ignored", "message": "Pipeline busy."}
        
#     is_pipeline_active = True
#     background_tasks.add_task(download_and_push_worker, magnet_link)
#     return {"message": "Pipeline triggered successfully on cloud worker."}

# @app.get("/api/v1/status")
# def get_engine_status():
#     return engine_status

# @app.post("/api/v1/shutdown")
# def kill_instance_server():
#     def target_shutdown():
#         time.sleep(2)
#         os.system("pkill -f uvicorn")
#     import threading
#     threading.Thread(target=target_shutdown).start()
#     return {"status": "Success"}








# import sys
# sys.path.append('/usr/lib/python3/dist-packages')

# import os
# import time
# import shutil
# import subprocess
# import re
# import requests
# from fastapi import FastAPI, BackgroundTasks, Form, Request
# from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
# import libtorrent as lt

# app = FastAPI()

# # 1. Broad global CORS settings
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # 2. FORCE CUSTOM INJECTION MIDDLEWARE FOR NGROK AND CORS BYPASS
# @app.middleware("http")
# async def add_custom_headers(request: Request, call_next):
#     if request.method == "OPTIONS":
#         response = JSONResponse(content="OK")
#     else:
#         response = await call_next(request)
        
#     response.headers["Access-Control-Allow-Origin"] = "*"
#     response.headers["Access-Control-Allow-Methods"] = "*"
#     response.headers["Access-Control-Allow-Headers"] = "*"
#     response.headers["ngrok-skip-browser-warning"] = "true"
#     return response

# # Global tracking flags
# is_pipeline_active = False

# engine_status = {
#     "status": "Sleeping",
#     "name": "None",
#     "progress": "0.00",
#     "speed": "0.00",
#     "peers": 0,
#     "disk_free": "0.00",
#     "upload_progress": "0",
#     "upload_speed": "0 B/s",
#     "upload_eta": "-"
# }

# def common_rclone_upload_engine(source_dir, display_name):
#     """Shared core engine to push staged folders directly to GDrive and wipe local caches"""
#     global engine_status, is_pipeline_active
#     rclone_errors = []
    
#     engine_status["status"] = "Cloud download done! Transferring to Google Drive..."
#     engine_status["speed"] = "0.00"
#     engine_status["progress"] = "100.00"
    
#     dest_dir = f"gdrive:CodespaceDownloads/{display_name}"
#     resolved_config_path = os.path.expanduser("~/.config/rclone/rclone.conf")
    
#     rclone_cmd = [
#         "rclone", "copy", source_dir, dest_dir, 
#         "--config", resolved_config_path,
#         "--transfers", "4", 
#         "--multi-thread-streams", "8", 
#         "--stats", "1s", 
#         "-v",
#         "--use-mmap"
#     ]
    
#     process = subprocess.Popen(
#         rclone_cmd, 
#         stdout=subprocess.PIPE, 
#         stderr=subprocess.STDOUT, 
#         text=True, 
#         bufsize=1
#     )
    
#     progress_regex = re.compile(r"(\d{1,3})%")
#     speed_regex = re.compile(r"(\d+(?:\.\d+)?\s*[a-zA-Z ]+/s)", re.IGNORECASE)
#     eta_global_regex = re.compile(r"ETA\s+(\S+)", re.IGNORECASE)

#     while True:
#         line = process.stdout.readline()
#         if not line and process.poll() is not None:
#             break
            
#         if line:
#             cleaned_line = line.strip()
#             print(f"RCLONE OUT: {cleaned_line}", flush=True)
            
#             if "ERROR" in cleaned_line or "Failed to" in cleaned_line:
#                 rclone_errors.append(cleaned_line)
            
#             if "transferred:" in cleaned_line.lower() and "/s" in cleaned_line.lower():
#                 prog_match = progress_regex.search(cleaned_line)
#                 if prog_match:
#                     engine_status["upload_progress"] = prog_match.group(1)
                
#                 speed_match = speed_regex.search(cleaned_line)
#                 if speed_match:
#                     engine_status["upload_speed"] = speed_match.group(1) 
                
#                 eta_match = eta_global_regex.search(cleaned_line)
#                 if eta_match:
#                     engine_status["upload_eta"] = eta_match.group(1)

#     process.wait()
#     exit_code = process.returncode
    
#     if exit_code == 0:
#         engine_status["status"] = "Success! Content securely saved in Google Drive."
#         engine_status["upload_progress"] = "100"
#         engine_status["upload_speed"] = "0 B/s"
#         engine_status["upload_eta"] = "0s"
        
#         print(f"🧹 Flushing temporary cache partition path -> {source_dir}")
#         try:
#             if os.path.isdir(source_dir):
#                 shutil.rmtree(source_dir)
#             elif os.path.isfile(source_dir):
#                 os.remove(source_dir)
#         except Exception as cleanup_error:
#             print(f"⚠️ Cache flush warning: {str(cleanup_error)}")

#         print("Upload finished perfectly. Handing control back to shell...")
#         time.sleep(10)
#         is_pipeline_active = False
#         os.system("pkill -f uvicorn")
#     else:
#         error_context = rclone_errors[-1] if rclone_errors else "Subprocess runtime fault."
#         engine_status["status"] = f"❌ Upload Error: {error_context}"
#         is_pipeline_active = False


# def download_and_push_worker(magnet_link: str):
#     global engine_status, is_pipeline_active
#     try:
#         engine_status["status"] = "Connecting to Swarm Network..."
#         ses = lt.session()
#         ses.listen_on(6881, 6891)
        
#         local_path = '/tmp/downloads'
#         os.makedirs(local_path, exist_ok=True)
        
#         magnet_link = magnet_link.strip()
        
#         # 🔥 NEW: Automatically handle remote .torrent file URLs
#         if magnet_link.startswith("http://") or magnet_link.startswith("https://"):
#             engine_status["status"] = "Fetching remote torrent file metadata..."
#             r = requests.get(magnet_link, timeout=15)
#             r.raise_for_status()
#             torrent_path = os.path.join('/tmp', 'downloaded.torrent')
#             with open(torrent_path, 'wb') as f:
#                 f.write(r.content)
            
#             torrent_info = lt.torrent_info(torrent_path)
#             torrent_name = torrent_info.name()
            
#             add_params = {
#                 'ti': torrent_info,
#                 'save_path': local_path,
#                 'storage_mode': lt.storage_mode_t.storage_mode_sparse
#             }
#             handle = ses.add_torrent(add_params)
#         else:
#             # 🔥 NEW: Automatically parse raw 40-character hex infohashes
#             if len(magnet_link) == 40 and all(c in '0123456789abcdefABCDEF' for c in magnet_link):
#                 magnet_link = f"magnet:?xt=urn:btih:{magnet_link}"
            
#             params = {'save_path': local_path, 'storage_mode': lt.storage_mode_t.storage_mode_sparse}
#             handle = lt.add_magnet_uri(ses, magnet_link, params)
            
#             while not handle.has_metadata():
#                 time.sleep(1)
                
#             torrent_info = handle.get_torrent_info()
#             torrent_name = torrent_info.name()
            
#         handle.set_flags(lt.torrent_flags.sequential_download)
#         engine_status["name"] = torrent_name
#         engine_status["status"] = "Downloading on Cloud Instance..."
        
#         while not handle.status().is_seeding:
#             s = handle.status()
#             engine_status["speed"] = f"{s.download_rate / (1024 * 1024):.2f}"
#             engine_status["progress"] = f"{s.progress * 100:.2f}"
#             engine_status["peers"] = s.num_peers
            
#             _, _, free = shutil.disk_usage(local_path)
#             engine_status["disk_free"] = f"{free / (1024**3):.2f}"
#             time.sleep(2)
            
#         ses.remove_torrent(handle)
#         time.sleep(2)
        
#         source_dir = os.path.join(local_path, torrent_name)
#         common_rclone_upload_engine(source_dir, torrent_name)

#     except Exception as e:
#         engine_status["status"] = f"❌ Torrent Error: {str(e)}"
#         is_pipeline_active = False


# def download_huggingface_worker(repo_id: str, repo_type: str):
#     """Downloads items from Hugging Face via Rust hf-transfer acceleration"""
#     global engine_status, is_pipeline_active
#     try:
#         folder_friendly_name = repo_id.replace("/", "--")
#         engine_status["name"] = f"HF ➔ {repo_id}"
#         engine_status["status"] = "🚀 Activating Warp-Speed hf-transfer Core..."
#         engine_status["peers"] = 0
        
#         local_path = '/tmp/downloads'
#         source_dir = os.path.join(local_path, folder_friendly_name)
#         os.makedirs(source_dir, exist_ok=True)
        
#         custom_env = os.environ.copy()
#         custom_env["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
        
#         hf_cmd = [
#             "huggingface-cli", "download", repo_id,
#             "--repo-type", repo_type,
#             "--local-dir", source_dir,
#             "--local-dir-use-symlinks", "False"
#         ]
        
#         print(f"Triggering HuggingFace Engine: {hf_cmd}")
        
#         process = subprocess.Popen(
#             hf_cmd,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.STDOUT,
#             text=True,
#             bufsize=1,
#             env=custom_env
#         )
        
#         progress_regex = re.compile(r"(\d+)%")
        
#         while True:
#             line = process.stdout.readline()
#             if not line and process.poll() is not None:
#                 break
#             if line:
#                 cleaned_line = line.strip()
#                 print(f"HF OUT: {cleaned_line}", flush=True)
                
#                 prog_match = progress_regex.search(cleaned_line)
#                 if prog_match:
#                     engine_status["progress"] = f"{float(prog_match.group(1)):.2f}"
                
#                 if "downloading" in cleaned_line.lower():
#                     engine_status["status"] = f"Streaming {repo_type} files from Hugging Face..."
#                     engine_status["speed"] = "🏎️ Accelerated"
                
#                 _, _, free = shutil.disk_usage(local_path)
#                 engine_status["disk_free"] = f"{free / (1024**3):.2f}"

#         process.wait()
        
#         if process.returncode == 0:
#             common_rclone_upload_engine(source_dir, folder_friendly_name)
#         else:
#             engine_status["status"] = "❌ Hugging Face download runtime failure."
#             is_pipeline_active = False

#     except Exception as e:
#         engine_status["status"] = f"❌ HF Engine Error: {str(e)}"
#         is_pipeline_active = False


# @app.post("/api/v1/enqueue")
# def enqueue_link(background_tasks: BackgroundTasks, magnet_link: str = Form(...)):
#     global is_pipeline_active
#     if is_pipeline_active:
#         return {"status": "ignored", "message": "Pipeline busy."}
#     is_pipeline_active = True
#     background_tasks.add_task(download_and_push_worker, magnet_link)
#     return {"message": "Torrent pipeline triggered successfully."}


# @app.post("/api/v1/enqueue_hf")
# def enqueue_hf(background_tasks: BackgroundTasks, repo_id: str = Form(...)):
#     """API Gateway Endpoint to parse full HF URLs and launch extractions"""
#     global is_pipeline_active
#     if is_pipeline_active:
#         return {"status": "ignored", "message": "Pipeline busy."}
        
#     raw_input = repo_id.strip()
#     repo_type = "model"
    
#     if "huggingface.co/datasets/" in raw_input:
#         repo_type = "dataset"
#         parsed_id = raw_input.split("huggingface.co/datasets/")[1]
#     elif "huggingface.co/" in raw_input:
#         repo_type = "model"
#         parsed_id = raw_input.split("huggingface.co/")[1]
#     else:
#         parsed_id = raw_input

#     clean_repo_id = parsed_id.split("/tree/")[0].split("/blob/")[0].strip()
    
#     is_pipeline_active = True
#     background_tasks.add_task(download_huggingface_worker, clean_repo_id, repo_type)
#     return {"message": f"Hugging Face sync routine armed for {clean_repo_id} ({repo_type})!"}


# @app.get("/api/v1/status")
# def get_engine_status():
#     return engine_status

# @app.post("/api/v1/shutdown")
# def kill_instance_server():
#     def target_shutdown():
#         time.sleep(2)
#         os.system("pkill -f uvicorn")
#     import threading
#     threading.Thread(target=target_shutdown).start()
#     return {"status": "Success"}




# import sys
# sys.path.append('/usr/lib/python3/dist-packages')

# import os
# import time
# import shutil
# import subprocess
# import re
# import requests
# from fastapi import FastAPI, BackgroundTasks, Form, Request
# from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
# import libtorrent as lt

# app = FastAPI()

# # 1. Broad global CORS settings
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # 2. FORCE CUSTOM INJECTION MIDDLEWARE FOR NGROK AND CORS BYPASS
# @app.middleware("http")
# async def add_custom_headers(request: Request, call_next):
#     if request.method == "OPTIONS":
#         response = JSONResponse(content="OK")
#     else:
#         response = await call_next(request)
        
#     response.headers["Access-Control-Allow-Origin"] = "*"
#     response.headers["Access-Control-Allow-Methods"] = "*"
#     response.headers["Access-Control-Allow-Headers"] = "*"
#     response.headers["ngrok-skip-browser-warning"] = "true"
#     return response

# # Global tracking flags
# is_pipeline_active = False

# engine_status = {
#     "status": "Sleeping",
#     "name": "None",
#     "progress": "0.00",
#     "speed": "0.00",
#     "peers": 0,
#     "disk_free": "0.00",
#     "upload_progress": "0",
#     "upload_speed": "0 B/s",
#     "upload_eta": "-"
# }

# def common_rclone_upload_engine(source_dir, display_name):
#     """Shared core engine to push staged folders directly to GDrive and wipe local caches"""
#     global engine_status, is_pipeline_active
#     rclone_errors = []
    
#     engine_status["status"] = "Cloud download done! Transferring to Google Drive..."
#     engine_status["speed"] = "0.00"
#     engine_status["progress"] = "100.00"
    
#     dest_dir = f"gdrive:CodespaceDownloads/{display_name}"
#     resolved_config_path = os.path.expanduser("~/.config/rclone/rclone.conf")
    
#     rclone_cmd = [
#         "rclone", "copy", source_dir, dest_dir, 
#         "--config", resolved_config_path,
#         "--transfers", "4", 
#         "--multi-thread-streams", "8", 
#         "--stats", "1s", 
#         "-v",
#         "--use-mmap"
#     ]
    
#     process = subprocess.Popen(
#         rclone_cmd, 
#         stdout=subprocess.PIPE, 
#         stderr=subprocess.STDOUT, 
#         text=True, 
#         bufsize=1
#     )
    
#     progress_regex = re.compile(r"(\d{1,3})%")
#     speed_regex = re.compile(r"(\d+(?:\.\d+)?\s*[a-zA-Z ]+/s)", re.IGNORECASE)
#     eta_global_regex = re.compile(r"ETA\s+(\S+)", re.IGNORECASE)

#     while True:
#         line = process.stdout.readline()
#         if not line and process.poll() is not None:
#             break
            
#         if line:
#             cleaned_line = line.strip()
#             print(f"RCLONE OUT: {cleaned_line}", flush=True)
            
#             if "ERROR" in cleaned_line or "Failed to" in cleaned_line:
#                 rclone_errors.append(cleaned_line)
            
#             if "transferred:" in cleaned_line.lower() and "/s" in cleaned_line.lower():
#                 prog_match = progress_regex.search(cleaned_line)
#                 if prog_match:
#                     engine_status["upload_progress"] = prog_match.group(1)
                
#                 speed_match = speed_regex.search(cleaned_line)
#                 if speed_match:
#                     engine_status["upload_speed"] = speed_match.group(1) 
                
#                 eta_match = eta_global_regex.search(cleaned_line)
#                 if eta_match:
#                     engine_status["upload_eta"] = eta_match.group(1)

#     process.wait()
#     exit_code = process.returncode
    
#     if exit_code == 0:
#         engine_status["status"] = "Success! Content securely saved in Google Drive."
#         engine_status["upload_progress"] = "100"
#         engine_status["upload_speed"] = "0 B/s"
#         engine_status["upload_eta"] = "0s"
        
#         print(f"🧹 Flushing temporary cache partition path -> {source_dir}")
#         try:
#             if os.path.isdir(source_dir):
#                 shutil.rmtree(source_dir)
#             elif os.path.isfile(source_dir):
#                 os.remove(source_dir)
#         except Exception as cleanup_error:
#             print(f"⚠️ Cache flush warning: {str(cleanup_error)}")

#         print("Upload finished perfectly. Handing control back to shell...")
#         time.sleep(10)
#         is_pipeline_active = False
#         os.system("pkill -f uvicorn")
#     else:
#         error_context = rclone_errors[-1] if rclone_errors else "Subprocess runtime fault."
#         engine_status["status"] = f"❌ Upload Error: {error_context}"
#         is_pipeline_active = False


# def download_and_push_worker(magnet_link: str):
#     global engine_status, is_pipeline_active
#     try:
#         engine_status["status"] = "Connecting to Swarm Network..."
#         ses = lt.session()
#         ses.listen_on(6881, 6891)
        
#         local_path = '/tmp/downloads'
#         os.makedirs(local_path, exist_ok=True)
        
#         magnet_link = magnet_link.strip()
        
#         if magnet_link.startswith("http://") or magnet_link.startswith("https://"):
#             engine_status["status"] = "Fetching remote torrent file metadata..."
#             r = requests.get(magnet_link, timeout=15)
#             r.raise_for_status()
#             torrent_path = os.path.join('/tmp', 'downloaded.torrent')
#             with open(torrent_path, 'wb') as f:
#                 f.write(r.content)
            
#             torrent_info = lt.torrent_info(torrent_path)
#             torrent_name = torrent_info.name()
            
#             add_params = {
#                 'ti': torrent_info,
#                 'save_path': local_path,
#                 'storage_mode': lt.storage_mode_t.storage_mode_sparse
#             }
#             handle = ses.add_torrent(add_params)
#         else:
#             if len(magnet_link) == 40 and all(c in '0123456789abcdefABCDEF' for c in magnet_link):
#                 magnet_link = f"magnet:?xt=urn:btih:{magnet_link}"
            
#             params = {'save_path': local_path, 'storage_mode': lt.storage_mode_t.storage_mode_sparse}
#             handle = lt.add_magnet_uri(ses, magnet_link, params)
            
#             while not handle.has_metadata():
#                 time.sleep(1)
                
#             torrent_info = handle.get_torrent_info()
#             torrent_name = torrent_info.name()
            
#         handle.set_flags(lt.torrent_flags.sequential_download)
#         engine_status["name"] = torrent_name
#         engine_status["status"] = "Downloading on Cloud Instance..."
        
#         while not handle.status().is_seeding:
#             s = handle.status()
#             engine_status["speed"] = f"{s.download_rate / (1024 * 1024):.2f}"
#             engine_status["progress"] = f"{s.progress * 100:.2f}"
#             engine_status["peers"] = s.num_peers
            
#             _, _, free = shutil.disk_usage(local_path)
#             engine_status["disk_free"] = f"{free / (1024**3):.2f}"
#             time.sleep(2)
            
#         ses.remove_torrent(handle)
#         time.sleep(2)
        
#         source_dir = os.path.join(local_path, torrent_name)
#         common_rclone_upload_engine(source_dir, torrent_name)

#     except Exception as e:
#         engine_status["status"] = f"❌ Torrent Error: {str(e)}"
#         is_pipeline_active = False


# def download_huggingface_worker(repo_id: str, repo_type: str):
#     """Downloads files using a pure Python HTTP Stream Engine with corrected Hugging Face CDN routing paths"""
#     global engine_status, is_pipeline_active
#     try:
#         folder_friendly_name = repo_id.replace("/", "--")
#         engine_status["name"] = f"HF ➔ {repo_id}"
#         engine_status["status"] = "Contacting Hugging Face API Metadata Hub..."
#         engine_status["peers"] = 0
        
#         local_path = '/tmp/downloads'
#         source_dir = os.path.join(local_path, folder_friendly_name)
#         os.makedirs(source_dir, exist_ok=True)
        
#         api_url = f"https://huggingface.co/api/{repo_type}s/{repo_id}/tree/main"
#         headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
#         res = requests.get(api_url, headers=headers, timeout=15)
#         if res.status_code == 404 and repo_type == "model":
#             api_url = f"https://huggingface.co/api/datasets/{repo_id}/tree/main"
#             res = requests.get(api_url, headers=headers, timeout=15)
            
#         res.raise_for_status()
        
#         # Filter out hidden Git layout config assets
#         files_list = [
#             item["path"] for item in res.json() 
#             if item.get("type") == "file" and not os.path.basename(item["path"]).startswith('.')
#         ]
        
#         if not files_list:
#             raise Exception("No downloadable asset streams found in repository tree root.")
            
#         print(f"HF Core discovered {len(files_list)} target files to process.")
#         block_size = 1024 * 1024  # 1 MB block buffers
        
#         for idx, file_path in enumerate(files_list):
#             filename_clean = os.path.basename(file_path)
#             engine_status["status"] = f"Downloading item {idx + 1}/{len(files_list)}: {filename_clean}"
            
#             # 🔥 FIXED: Adhering strictly to Hugging Face URL Scheme constraints
#             if repo_type == "dataset" or "api/datasets" in api_url:
#                 download_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{file_path}"
#             else:
#                 download_url = f"https://huggingface.co/{repo_id}/resolve/main/{file_path}"
                
#             dest_file_path = os.path.join(source_dir, file_path)
#             os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
            
#             start_time = time.time()
            
#             with requests.get(download_url, headers=headers, stream=True, timeout=30) as r:
#                 r.raise_for_status()
#                 file_size = int(r.headers.get('content-length', 0))
                
#                 with open(dest_file_path, 'wb') as f:
#                     file_downloaded = 0
#                     for chunk in r.iter_content(block_size):
#                         if chunk:
#                             f.write(chunk)
#                             file_downloaded += len(chunk)
                            
#                             elapsed = time.time() - start_time
#                             if elapsed > 0:
#                                 engine_status["speed"] = f"{(file_downloaded / (1024**2)) / elapsed:.2f} MB/s"
                            
#                             approx_prog = ((idx / len(files_list)) * 100) + ((file_downloaded / file_size) * (100 / len(files_list))) if file_size > 0 else (idx / len(files_list)) * 100
#                             engine_status["progress"] = f"{approx_prog:.2f}"
                            
#                             _, _, free = shutil.disk_usage(local_path)
#                             engine_status["disk_free"] = f"{free / (1024**3):.2f}"

#         # Stream complete! Initialize GDrive upload handoff sequence
#         common_rclone_upload_engine(source_dir, folder_friendly_name)

#     except Exception as e:
#         engine_status["status"] = f"❌ HTTP Engine Error: {str(e)}"
#         is_pipeline_active = False


# @app.post("/api/v1/enqueue")
# def enqueue_link(background_tasks: BackgroundTasks, magnet_link: str = Form(...)):
#     global is_pipeline_active
#     if is_pipeline_active:
#         return {"status": "ignored", "message": "Pipeline busy."}
#     is_pipeline_active = True
#     background_tasks.add_task(download_and_push_worker, magnet_link)
#     return {"message": "Torrent pipeline triggered successfully."}


# @app.post("/api/v1/enqueue_hf")
# def enqueue_hf(background_tasks: BackgroundTasks, repo_id: str = Form(...)):
#     global is_pipeline_active
#     if is_pipeline_active:
#         return {"status": "ignored", "message": "Pipeline busy."}
        
#     raw_input = repo_id.strip()
#     repo_type = "model"
    
#     if "huggingface.co/datasets/" in raw_input:
#         repo_type = "dataset"
#         parsed_id = raw_input.split("huggingface.co/datasets/")[1]
#     elif "huggingface.co/" in raw_input:
#         repo_type = "model"
#         parsed_id = raw_input.split("huggingface.co/")[1]
#     else:
#         parsed_id = raw_input

#     clean_repo_id = parsed_id.split("/tree/")[0].split("/blob/")[0].strip()
    
#     is_pipeline_active = True
#     background_tasks.add_task(download_huggingface_worker, clean_repo_id, repo_type)
#     return {"message": f"Hugging Face sync routine armed for {clean_repo_id}!"}


# @app.get("/api/v1/status")
# def get_engine_status():
#     return engine_status

# @app.post("/api/v1/shutdown")
# def kill_instance_server():
#     def target_shutdown():
#         time.sleep(2)
#         os.system("pkill -f uvicorn")
#     import threading
#     threading.Thread(target=target_shutdown).start()
#     return {"status": "Success"}






# import sys
# sys.path.append('/usr/lib/python3/dist-packages')

# import os
# import time
# import shutil
# import subprocess
# import re
# import requests
# import threading
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from fastapi import FastAPI, BackgroundTasks, Form, Request
# from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
# import libtorrent as lt

# app = FastAPI()

# # 1. Broad global CORS settings
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # 2. FORCE CUSTOM INJECTION MIDDLEWARE FOR NGROK AND CORS BYPASS
# @app.middleware("http")
# async def add_custom_headers(request: Request, call_next):
#     if request.method == "OPTIONS":
#         response = JSONResponse(content="OK")
#     else:
#         response = await call_next(request)
        
#     response.headers["Access-Control-Allow-Origin"] = "*"
#     response.headers["Access-Control-Allow-Methods"] = "*"
#     response.headers["Access-Control-Allow-Headers"] = "*"
#     response.headers["ngrok-skip-browser-warning"] = "true"
#     return response

# # Global tracking flags
# is_pipeline_active = False

# engine_status = {
#     "status": "Sleeping",
#     "name": "None",
#     "progress": "0.00",
#     "speed": "0.00",
#     "peers": 0,
#     "disk_free": "0.00",
#     "upload_progress": "0",
#     "upload_speed": "0 B/s",
#     "upload_eta": "-"
# }

# def common_rclone_upload_engine(source_dir, display_name):
#     """Shared core engine to push staged folders directly to GDrive and wipe local caches"""
#     global engine_status, is_pipeline_active
#     rclone_errors = []
    
#     engine_status["status"] = "Cloud download done! Transferring to Google Drive..."
#     engine_status["speed"] = "0.00"
#     engine_status["progress"] = "100.00"
    
#     dest_dir = f"gdrive:CodespaceDownloads/{display_name}"
#     resolved_config_path = os.path.expanduser("~/.config/rclone/rclone.conf")
    
#     rclone_cmd = [
#         "rclone", "copy", source_dir, dest_dir, 
#         "--config", resolved_config_path,
#         "--transfers", "4", 
#         "--multi-thread-streams", "8", 
#         "--stats", "1s", 
#         "-v",
#         "--use-mmap"
#     ]
    
#     process = subprocess.Popen(
#         rclone_cmd, 
#         stdout=subprocess.PIPE, 
#         stderr=subprocess.STDOUT, 
#         text=True, 
#         bufsize=1
#     )
    
#     progress_regex = re.compile(r"(\d{1,3})%")
#     speed_regex = re.compile(r"(\d+(?:\.\d+)?\s*[a-zA-Z ]+/s)", re.IGNORECASE)
#     eta_global_regex = re.compile(r"ETA\s+(\S+)", re.IGNORECASE)

#     while True:
#         line = process.stdout.readline()
#         if not line and process.poll() is not None:
#             break
            
#         if line:
#             cleaned_line = line.strip()
#             print(f"RCLONE OUT: {cleaned_line}", flush=True)
            
#             if "ERROR" in cleaned_line or "Failed to" in cleaned_line:
#                 rclone_errors.append(cleaned_line)
            
#             if "transferred:" in cleaned_line.lower() and "/s" in cleaned_line.lower():
#                 prog_match = progress_regex.search(cleaned_line)
#                 if prog_match:
#                     engine_status["upload_progress"] = prog_match.group(1)
                
#                 speed_match = speed_regex.search(cleaned_line)
#                 if speed_match:
#                     engine_status["upload_speed"] = speed_match.group(1) 
                
#                 eta_match = eta_global_regex.search(cleaned_line)
#                 if eta_match:
#                     engine_status["upload_eta"] = eta_match.group(1)

#     process.wait()
#     exit_code = process.returncode
    
#     if exit_code == 0:
#         engine_status["status"] = "Success! Content securely saved in Google Drive."
#         engine_status["upload_progress"] = "100"
#         engine_status["upload_speed"] = "0 B/s"
#         engine_status["upload_eta"] = "0s"
        
#         print(f"🧹 Flushing temporary cache partition path -> {source_dir}")
#         try:
#             if os.path.isdir(source_dir):
#                 shutil.rmtree(source_dir)
#             elif os.path.isfile(source_dir):
#                 os.remove(source_dir)
#         except Exception as cleanup_error:
#             print(f"⚠️ Cache flush warning: {str(cleanup_error)}")

#         print("Upload finished perfectly. Handing control back to shell...")
#         time.sleep(10)
#         is_pipeline_active = False
#         os.system("pkill -f uvicorn")
#     else:
#         error_context = rclone_errors[-1] if rclone_errors else "Subprocess runtime fault."
#         engine_status["status"] = f"❌ Upload Error: {error_context}"
#         is_pipeline_active = False


# def download_and_push_worker(magnet_link: str):
#     global engine_status, is_pipeline_active
#     try:
#         engine_status["status"] = "Connecting to Swarm Network..."
#         ses = lt.session()
#         ses.listen_on(6881, 6891)
        
#         local_path = '/tmp/downloads'
#         os.makedirs(local_path, exist_ok=True)
#         magnet_link = magnet_link.strip()
        
#         if magnet_link.startswith("http://") or magnet_link.startswith("https://"):
#             engine_status["status"] = "Fetching remote torrent file metadata..."
#             r = requests.get(magnet_link, timeout=15)
#             r.raise_for_status()
#             torrent_path = os.path.join('/tmp', 'downloaded.torrent')
#             with open(torrent_path, 'wb') as f:
#                 f.write(r.content)
            
#             torrent_info = lt.torrent_info(torrent_path)
#             torrent_name = torrent_info.name()
            
#             add_params = {
#                 'ti': torrent_info,
#                 'save_path': local_path,
#                 'storage_mode': lt.storage_mode_t.storage_mode_sparse
#             }
#             handle = ses.add_torrent(add_params)
#         else:
#             if len(magnet_link) == 40 and all(c in '0123456789abcdefABCDEF' for c in magnet_link):
#                 magnet_link = f"magnet:?xt=urn:btih:{magnet_link}"
            
#             params = {'save_path': local_path, 'storage_mode': lt.storage_mode_t.storage_mode_sparse}
#             handle = lt.add_magnet_uri(ses, magnet_link, params)
            
#             while not handle.has_metadata():
#                 time.sleep(1)
                
#             torrent_info = handle.get_torrent_info()
#             torrent_name = torrent_info.name()
            
#         handle.set_flags(lt.torrent_flags.sequential_download)
#         engine_status["name"] = torrent_name
#         engine_status["status"] = "Downloading on Cloud Instance..."
        
#         while not handle.status().is_seeding:
#             s = handle.status()
#             engine_status["speed"] = f"{s.download_rate / (1024 * 1024):.2f}"
#             engine_status["progress"] = f"{s.progress * 100:.2f}"
#             engine_status["peers"] = s.num_peers
            
#             _, _, free = shutil.disk_usage(local_path)
#             engine_status["disk_free"] = f"{free / (1024**3):.2f}"
#             time.sleep(2)
            
#         ses.remove_torrent(handle)
#         time.sleep(2)
        
#         source_dir = os.path.join(local_path, torrent_name)
#         common_rclone_upload_engine(source_dir, torrent_name)

#     except Exception as e:
#         engine_status["status"] = f"❌ Torrent Error: {str(e)}"
#         is_pipeline_active = False


# def download_single_file_task(download_url, dest_file_path, headers, block_size, chunk_callback, file_done_callback):
#     """Thread consumer task pulling data stream blocks and forwarding sizes to the live progress callback"""
#     with requests.get(download_url, headers=headers, stream=True, timeout=30) as r:
#         r.raise_for_status()
#         with open(dest_file_path, 'wb') as f:
#             for chunk in r.iter_content(block_size):
#                 if chunk:
#                     f.write(chunk)
#                     # Trigger the thread-safe global counter instantly
#                     chunk_callback(len(chunk))
#     file_done_callback()


# def download_huggingface_worker(repo_id: str, repo_type: str):
#     """Downloads files concurrently using a safe 10-worker ThreadPool with fluid real-time metrics updates"""
#     global engine_status, is_pipeline_active
#     try:
#         folder_friendly_name = repo_id.replace("/", "--")
#         engine_status["name"] = f"HF ➔ {repo_id}"
#         engine_status["status"] = "Contacting Hugging Face API Metadata Hub..."
        
#         local_path = '/tmp/downloads'
#         source_dir = os.path.join(local_path, folder_friendly_name)
#         os.makedirs(source_dir, exist_ok=True)
        
#         api_url = f"https://huggingface.co/api/{repo_type}s/{repo_id}/tree/main"
#         headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
#         res = requests.get(api_url, headers=headers, timeout=15)
#         if res.status_code == 404 and repo_type == "model":
#             api_url = f"https://huggingface.co/api/datasets/{repo_id}/tree/main"
#             res = requests.get(api_url, headers=headers, timeout=15)
            
#         res.raise_for_status()
        
#         # Extract files metadata lists
#         raw_items = res.json()
#         files_metadata = [
#             item for item in raw_items 
#             if item.get("type") == "file" and not os.path.basename(item["path"]).startswith('.')
#         ]
        
#         if not files_metadata:
#             raise Exception("No downloadable asset streams found in repository tree root.")
            
#         total_files = len(files_metadata)
#         # Calculate the total repo size in bytes upfront for smooth progressive rendering
#         total_repo_size_bytes = sum(item.get("size", 0) for item in files_metadata)
        
#         print(f"HF Core targeting {total_files} assets. Aggregated Size: {total_repo_size_bytes / (1024**3):.2f} GB")
#         block_size = 1024 * 1024  # 1 MB blocks
        
#         # Thread-safe telemetry state variables
#         metrics_lock = threading.Lock()
#         global_bytes_downloaded = 0
#         completed_files_count = 0
#         global_start_time = time.time()
        
#         # Define smooth thread-safe tracking callbacks
#         def on_chunk_downloaded(chunk_len):
#             nonlocal global_bytes_downloaded, total_repo_size_bytes, global_start_time, completed_files_count, total_files
#             with metrics_lock:
#                 global_bytes_downloaded += chunk_len
#                 elapsed_total = time.time() - global_start_time
                
#                 if elapsed_total > 0:
#                     current_speed = (global_bytes_downloaded / (1024**2)) / elapsed_total
#                     engine_status["speed"] = f"{current_speed:.2f} MB/s"
                
#                 # Smooth progressive rendering based on total downloaded bytes vs total repository size
#                 if total_repo_size_bytes > 0:
#                     approx_prog = (global_bytes_downloaded / total_repo_size_bytes) * 100
#                     engine_status["progress"] = f"{min(approx_prog, 99.99):.2f}"
                
#                 _, _, free = shutil.disk_usage(local_path)
#                 engine_status["disk_free"] = f"{free / (1024**3):.2f}"

#         def on_file_completed():
#             nonlocal completed_files_count, total_files
#             with metrics_lock:
#                 completed_files_count += 1
#                 engine_status["status"] = f"Piping 10 streams concurrently... Staged {completed_files_count}/{total_files} files."

#         # Armed Concurrency configuration
#         MAX_CONCURRENT_DOWNLOADS = 10 
#         engine_status["status"] = f"Spawning 10 accelerated worker pipelines..."
        
#         with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as executor:
#             futures = []
            
#             for item in files_metadata:
#                 file_path = item["path"]
#                 if repo_type == "dataset" or "api/datasets" in api_url:
#                     download_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{file_path}"
#                 else:
#                     download_url = f"https://huggingface.co/{repo_id}/resolve/main/{file_path}"
                    
#                 dest_file_path = os.path.join(source_dir, file_path)
#                 os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
                
#                 # Submit tasks with integrated callbacks
#                 future = executor.submit(
#                     download_single_file_task, 
#                     download_url, dest_file_path, headers, block_size, 
#                     on_chunk_downloaded, on_file_completed
#                 )
#                 futures.append(future)
            
#             # Wait for all threads in the executor pool block to complete
#             for future in as_completed(futures):
#                 try:
#                     future.result()
#                 except Exception as task_error:
#                     print(f"⚠️ Worker pipe reported tracking exception inside execution thread: {task_error}")

#         # Everything downloaded cleanly. Hand control block over to rclone copy engines
#         common_rclone_upload_engine(source_dir, folder_friendly_name)

#     except Exception as e:
#         engine_status["status"] = f"❌ Concurrent Engine Error: {str(e)}"
#         is_pipeline_active = False


# @app.post("/api/v1/enqueue")
# def enqueue_link(background_tasks: BackgroundTasks, magnet_link: str = Form(...)):
#     global is_pipeline_active
#     if is_pipeline_active:
#         return {"status": "ignored", "message": "Pipeline busy."}
#     is_pipeline_active = True
#     background_tasks.add_task(download_and_push_worker, magnet_link)
#     return {"message": "Torrent pipeline triggered successfully."}


# @app.post("/api/v1/enqueue_hf")
# def enqueue_hf(background_tasks: BackgroundTasks, repo_id: str = Form(...)):
#     global is_pipeline_active
#     if is_pipeline_active:
#         return {"status": "ignored", "message": "Pipeline busy."}
        
#     raw_input = repo_id.strip()
#     repo_type = "model"
    
#     if "huggingface.co/datasets/" in raw_input:
#         repo_type = "dataset"
#         parsed_id = raw_input.split("huggingface.co/datasets/")[1]
#     elif "huggingface.co/" in raw_input:
#         repo_type = "model"
#         parsed_id = raw_input.split("huggingface.co/")[1]
#     else:
#         parsed_id = raw_input

#     clean_repo_id = parsed_id.split("/tree/")[0].split("/blob/")[0].strip()
    
#     is_pipeline_active = True
#     background_tasks.add_task(download_huggingface_worker, clean_repo_id, repo_type)
#     return {"message": f"Hugging Face sync routine armed for {clean_repo_id}!"}


# @app.get("/api/v1/status")
# def get_engine_status():
#     return engine_status

# @app.post("/api/v1/shutdown")
# def kill_instance_server():
#     def target_shutdown():
#         time.sleep(2)
#         os.system("pkill -f uvicorn")
#     import threading
#     threading.Thread(target=target_shutdown).start()
#     return {"status": "Success"}



import sys
sys.path.append('/usr/lib/python3/dist-packages')

import os
import time
import shutil
import subprocess
import re
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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

def common_rclone_upload_engine(source_dir, display_name):
    """Shared core engine optimized to push 10 files concurrently to Google Drive with locked global telemetry"""
    global engine_status, is_pipeline_active
    rclone_errors = []
    
    engine_status["status"] = "Cloud download done! Transferring to Google Drive..."
    engine_status["speed"] = "0.00"
    engine_status["progress"] = "100.00"
    
    dest_dir = f"gdrive:CodespaceDownloads/{display_name}"
    resolved_config_path = os.path.expanduser("~/.config/rclone/rclone.conf")
    
    rclone_cmd = [
        "rclone", "copy", source_dir, dest_dir, 
        "--config", resolved_config_path,
        "--transfers", "10", 
        "--multi-thread-streams", "12", 
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
            
            # 🔥 FIXED ANCHOR: Must contain 'transferred:' AND file queue counts ' / ' to ensure it's the true global summary line
            if "transferred:" in cleaned_line.lower() and " / " in cleaned_line.lower() and "/s" in cleaned_line.lower():
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
    
    if exit_code == 0:
        engine_status["status"] = "Success! Content securely saved in Google Drive."
        engine_status["upload_progress"] = "100"
        engine_status["upload_speed"] = "0 B/s"
        engine_status["upload_eta"] = "0s"
        
        print(f"🧹 Flushing temporary cache partition path -> {source_dir}")
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
    else:
        error_context = rclone_errors[-1] if rclone_errors else "Subprocess runtime fault."
        engine_status["status"] = f"❌ Upload Error: {error_context}"
        is_pipeline_active = False


def download_and_push_worker(magnet_link: str):
    global engine_status, is_pipeline_active
    try:
        engine_status["status"] = "Connecting to Swarm Network..."
        ses = lt.session()
        ses.listen_on(6881, 6891)
        
        local_path = '/tmp/downloads'
        os.makedirs(local_path, exist_ok=True)
        magnet_link = magnet_link.strip()
        
        if magnet_link.startswith("http://") or magnet_link.startswith("https://"):
            engine_status["status"] = "Fetching remote torrent file metadata..."
            r = requests.get(magnet_link, timeout=15)
            r.raise_for_status()
            torrent_path = os.path.join('/tmp', 'downloaded.torrent')
            with open(torrent_path, 'wb') as f:
                f.write(r.content)
            
            torrent_info = lt.torrent_info(torrent_path)
            torrent_name = torrent_info.name()
            
            add_params = {
                'ti': torrent_info,
                'save_path': local_path,
                'storage_mode': lt.storage_mode_t.storage_mode_sparse
            }
            handle = ses.add_torrent(add_params)
        else:
            if len(magnet_link) == 40 and all(c in '0123456789abcdefABCDEF' for c in magnet_link):
                magnet_link = f"magnet:?xt=urn:btih:{magnet_link}"
            
            params = {'save_path': local_path, 'storage_mode': lt.storage_mode_t.storage_mode_sparse}
            handle = lt.add_magnet_uri(ses, magnet_link, params)
            
            while not handle.has_metadata():
                time.sleep(1)
                
            torrent_info = handle.get_torrent_info()
            torrent_name = torrent_info.name()
            
        handle.set_flags(lt.torrent_flags.sequential_download)
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
            
        ses.remove_torrent(handle)
        time.sleep(2)
        
        source_dir = os.path.join(local_path, torrent_name)
        common_rclone_upload_engine(source_dir, torrent_name)

    except Exception as e:
        engine_status["status"] = f"❌ Torrent Error: {str(e)}"
        is_pipeline_active = False


def download_single_file_task(download_url, dest_file_path, headers, block_size, chunk_callback, file_done_callback):
    """Thread consumer task pulling data stream blocks and forwarding sizes to the live progress callback"""
    with requests.get(download_url, headers=headers, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(dest_file_path, 'wb') as f:
            for chunk in r.iter_content(block_size):
                if chunk:
                    f.write(chunk)
                    chunk_callback(len(chunk))
    file_done_callback()


def download_huggingface_worker(repo_id: str, repo_type: str):
    """Downloads files concurrently using a safe 10-worker ThreadPool with fluid real-time metrics updates"""
    global engine_status, is_pipeline_active
    try:
        folder_friendly_name = repo_id.replace("/", "--")
        engine_status["name"] = f"HF ➔ {repo_id}"
        engine_status["status"] = "Contacting Hugging Face API Metadata Hub..."
        
        local_path = '/tmp/downloads'
        source_dir = os.path.join(local_path, folder_friendly_name)
        os.makedirs(source_dir, exist_ok=True)
        
        api_url = f"https://huggingface.co/api/{repo_type}s/{repo_id}/tree/main"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        res = requests.get(api_url, headers=headers, timeout=15)
        if res.status_code == 404 and repo_type == "model":
            api_url = f"https://huggingface.co/api/datasets/{repo_id}/tree/main"
            res = requests.get(api_url, headers=headers, timeout=15)
            
        res.raise_for_status()
        
        raw_items = res.json()
        files_metadata = [
            item for item in raw_items 
            if item.get("type") == "file" and not os.path.basename(item["path"]).startswith('.')
        ]
        
        if not files_metadata:
            raise Exception("No downloadable asset streams found in repository tree root.")
            
        total_files = len(files_metadata)
        total_repo_size_bytes = sum(item.get("size", 0) for item in files_metadata)
        
        print(f"HF Core targeting {total_files} assets. Aggregated Size: {total_repo_size_bytes / (1024**3):.2f} GB")
        block_size = 1024 * 1024  # 1 MB blocks
        
        metrics_lock = threading.Lock()
        global_bytes_downloaded = 0
        completed_files_count = 0
        global_start_time = time.time()
        
        def on_chunk_downloaded(chunk_len):
            nonlocal global_bytes_downloaded, total_repo_size_bytes, global_start_time
            with metrics_lock:
                global_bytes_downloaded += chunk_len
                elapsed_total = time.time() - global_start_time
                
                if elapsed_total > 0:
                    current_speed = (global_bytes_downloaded / (1024**2)) / elapsed_total
                    engine_status["speed"] = f"{current_speed:.2f} MB/s"
                
                if total_repo_size_bytes > 0:
                    approx_prog = (global_bytes_downloaded / total_repo_size_bytes) * 100
                    engine_status["progress"] = f"{min(approx_prog, 99.99):.2f}"
                
                _, _, free = shutil.disk_usage(local_path)
                engine_status["disk_free"] = f"{free / (1024**3):.2f}"

        def on_file_completed():
            nonlocal completed_files_count, total_files
            with metrics_lock:
                completed_files_count += 1
                engine_status["status"] = f"Piping 10 streams concurrently... Staged {completed_files_count}/{total_files} files."

        MAX_CONCURRENT_DOWNLOADS = 10 
        engine_status["status"] = f"Spawning 10 accelerated worker pipelines..."
        
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as executor:
            futures = []
            
            for item in files_metadata:
                file_path = item["path"]
                if repo_type == "dataset" or "api/datasets" in api_url:
                    download_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{file_path}"
                else:
                    download_url = f"https://huggingface.co/{repo_id}/resolve/main/{file_path}"
                    
                dest_file_path = os.path.join(source_dir, file_path)
                os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
                
                future = executor.submit(
                    download_single_file_task, 
                    download_url, dest_file_path, headers, block_size, 
                    on_chunk_downloaded, on_file_completed
                )
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as task_error:
                    print(f"⚠️ Worker pipe reported tracking exception inside execution thread: {task_error}")

        # Launch accelerated 10-channel rclone copy engine
        common_rclone_upload_engine(source_dir, folder_friendly_name)

    except Exception as e:
        engine_status["status"] = f"❌ Concurrent Engine Error: {str(e)}"
        is_pipeline_active = False


@app.post("/api/v1/enqueue")
def enqueue_link(background_tasks: BackgroundTasks, magnet_link: str = Form(...)):
    global is_pipeline_active
    if is_pipeline_active:
        return {"status": "ignored", "message": "Pipeline busy."}
    is_pipeline_active = True
    background_tasks.add_task(download_and_push_worker, magnet_link)
    return {"message": "Torrent pipeline triggered successfully."}


@app.post("/api/v1/enqueue_hf")
def enqueue_hf(background_tasks: BackgroundTasks, repo_id: str = Form(...)):
    global is_pipeline_active
    if is_pipeline_active:
        return {"status": "ignored", "message": "Pipeline busy."}
        
    raw_input = repo_id.strip()
    repo_type = "model"
    
    if "huggingface.co/datasets/" in raw_input:
        repo_type = "dataset"
        parsed_id = raw_input.split("huggingface.co/datasets/")[1]
    elif "huggingface.co/" in raw_input:
        repo_type = "model"
        parsed_id = raw_input.split("huggingface.co/")[1]
    else:
        parsed_id = raw_input

    clean_repo_id = parsed_id.split("/tree/")[0].split("/blob/")[0].strip()
    
    is_pipeline_active = True
    background_tasks.add_task(download_huggingface_worker, clean_repo_id, repo_type)
    return {"message": f"Hugging Face sync routine armed for {clean_repo_id}!"}


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