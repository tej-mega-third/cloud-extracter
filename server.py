# server - tmp - gdrive pipe 


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
#     """Shared core engine optimized to push 10 files concurrently to Google Drive with locked global telemetry"""
#     global engine_status, is_pipeline_active
#     rclone_errors = []
    
#     # Reset tracking arrays for a clean slate
#     engine_status["status"] = "Cloud download done! Transferring to Google Drive..."
#     engine_status["speed"] = "0.00"
#     engine_status["progress"] = "100.00"
#     engine_status["upload_progress"] = "0"      
#     engine_status["upload_speed"] = "0 B/s"      
#     engine_status["upload_eta"] = "-"            
    
#     dest_dir = f"gdrive:CodespaceDownloads/{display_name}"
#     resolved_config_path = os.path.expanduser("~/.config/rclone/rclone.conf")
    
#     rclone_cmd = [
#         "rclone", "copy", source_dir, dest_dir, 
#         "--config", resolved_config_path,
#         "--transfers", "10", 
#         "--multi-thread-streams", "12", 
#         "--stats", "1s", 
#         "--stats-one-line",
#         "-v",
#         "--use-mmap"
#     ]
    
#     # 🔥 FIXED: Omitted text=True and set bufsize=0 to unlock a completely unbuffered raw binary stream channel
#     process = subprocess.Popen(
#         rclone_cmd, 
#         stdout=subprocess.PIPE, 
#         stderr=subprocess.STDOUT, 
#         bufsize=0
#     )
    
#     progress_regex = re.compile(r"(\d{1,3})%")
#     speed_regex = re.compile(r"(\d+(?:\.\d+)?\s*[a-zA-Z ]+/s)", re.IGNORECASE)
#     eta_global_regex = re.compile(r"ETA\s+(\S+)", re.IGNORECASE)

#     # Path to store the rclone log file locally in the workspace
#     local_log_path = "/workspaces/cloud-extracter/rclone_log.txt"
    
#     # Open the log file locally and stream output byte-by-byte manually
#     with open(local_log_path, "w", encoding="utf-8") as log_file:
#         byte_buf = b""
#         while True:
#             chunk = process.stdout.read(1)
#             if chunk == b"" and process.poll() is not None:
#                 break
                
#             if chunk in (b"\n", b"\r"):
#                 cleaned_line = byte_buf.decode('utf-8', errors='ignore').strip()
#                 byte_buf = b""
#                 if not cleaned_line:
#                     continue
                    
#                 print(f"RCLONE OUT: {cleaned_line}", flush=True)
                
#                 # Write the line directly to the local text file layout
#                 log_file.write(cleaned_line + "\n")
#                 log_file.flush()
                
#                 if "ERROR" in cleaned_line or "Failed to" in cleaned_line:
#                     rclone_errors.append(cleaned_line)
                
#                 speed_match = speed_regex.search(cleaned_line)
#                 prog_match = progress_regex.search(cleaned_line)
#                 eta_match = eta_global_regex.search(cleaned_line)
                
#                 # 🔥 FIXED: Decoupled matching logic ensures progress tracks correctly for multi-file payloads
#                 if speed_match:
#                     engine_status["upload_speed"] = speed_match.group(1)
#                 if prog_match:
#                     engine_status["upload_progress"] = prog_match.group(1)
#                 if eta_match:
#                     engine_status["upload_eta"] = eta_match.group(1)
#             else:
#                 byte_buf += chunk

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

#         # 🔥 FIXED: Expanded holding grace loop to 30s to completely cover fast-burst upload endings
#         print("Upload finished perfectly. Holding container process alive for 30s for frontend status polling...")
#         time.sleep(30)
#         is_pipeline_active = False
#         os.system("pkill -f uvicorn")
#         return
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
#     with requests.get(download_url, headers=headers, stream=True, timeout=30) as r:
#         r.raise_for_status()
#         with open(dest_file_path, 'wb') as f:
#             for chunk in r.iter_content(block_size):
#                 if chunk:
#                     f.write(chunk)
#                     chunk_callback(len(chunk))
#     file_done_callback()

# def download_huggingface_worker(repo_id: str, repo_type: str):
#     """Downloads files concurrently using a safe, throughput-driven dynamic thread pool scaling engine"""
#     global engine_status, is_pipeline_active
#     try:
#         folder_friendly_name = repo_id.replace("/", "--")
#         engine_status["name"] = f"HF ➔ {repo_id}"
#         engine_status["status"] = "Contacting Hugging Face API Metadata Hub..."
        
#         local_path = '/tmp/downloads'
#         source_dir = os.path.join(local_path, folder_friendly_name)
#         os.makedirs(source_dir, exist_ok=True)
        
#         headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
#         # 1. FETCH AGGREGATED METADATA INSTANTLY VIA CORES DETAILS API FOR INITIAL SPACE MAPPING
#         info_url = f"https://huggingface.co/api/{repo_type}s/{repo_id}"
#         info_res = requests.get(info_url, headers=headers, timeout=15)
#         if info_res.status_code == 404 and repo_type == "model":
#             info_url = f"https://huggingface.co/api/datasets/{repo_id}"
#             info_res = requests.get(info_url, headers=headers, timeout=15)
#         info_res.raise_for_status()
#         repo_detailed_info = info_res.json()
        
#         # Pull total size upfront
#         total_repo_size_bytes = repo_detailed_info.get("estimatedSize", 0)
        
#         # 2. RUN PAGINATED TREE CAPTURE SEQUENCE
#         base_api_url = f"https://huggingface.co/api/{repo_type}s/{repo_id}/tree/main"
#         files_metadata = []
#         params = {"recursive": "true"}
        
#         while True:
#             res = requests.get(base_api_url, headers=headers, params=params, timeout=15)
#             if res.status_code == 404 and "api/datasets" not in base_api_url:
#                 base_api_url = f"https://huggingface.co/api/datasets/{repo_id}/tree/main"
#                 res = requests.get(base_api_url, headers=headers, params=params, timeout=15)
                
#             res.raise_for_status()
#             raw_items = res.json()
            
#             if not raw_items:
#                 break
                
#             page_files = [
#                 item for item in raw_items 
#                 if item.get("type") == "file" and not os.path.basename(item["path"]).startswith('.')
#             ]
#             files_metadata.extend(page_files)
            
#             if "Link" in res.headers:
#                 match = re.search(r'<(https://[^>]+)>;\s*rel="next"', res.headers["Link"])
#                 if match:
#                     base_api_url = match.group(1)
#                     params = {}
#                     continue
            
#             if len(raw_items) >= 1000:
#                 params["cursor"] = raw_items[-1]["path"]
#             else:
#                 break
                
#         total_files = len(files_metadata)
#         if total_repo_size_bytes == 0:
#             total_repo_size_bytes = sum(item.get("size", 0) for item in files_metadata)
            
#         # 3. THROUGHPUT-DRIVEN THREAD POOL SCALING MATRIX
#         # Calculate the mathematical average density of the repository files
#         avg_file_size_bytes = total_repo_size_bytes / max(total_files, 1)
        
#         # Establish dynamic estimates for thread efficiency under connection overhead penalties
#         if avg_file_size_bytes < 500 * 1024:          # Micro files (<500 KB) -> Est 0.2 MB/s per thread
#             calculated_workers = int(50.0 / 0.2)
#         elif avg_file_size_bytes < 5 * 1024 * 1024:    # Tiny files (<5 MB) -> Est 0.5 MB/s per thread
#             calculated_workers = int(50.0 / 0.5)
#         elif avg_file_size_bytes < 50 * 1024 * 1024:  # Medium files (<50 MB) -> Est 3.0 MB/s per thread
#             calculated_workers = int(50.0 / 3.0)
#         else:                                          # Heavy files (>50 MB) -> Est 15.0 MB/s per thread
#             calculated_workers = int(50.0 / 15.0)
            
#         # Hard system boundary safeguarding clamps
#         MAX_CONCURRENT_DOWNLOADS = max(10, min(calculated_workers, 120, total_files))
        
#         print(f"📊 Dataset Profile: {total_files} files | Total Size: {total_repo_size_bytes/(1024**3):.2f} GB")
#         print(f"🏎️ Throughput Scaling: Deploying {MAX_CONCURRENT_DOWNLOADS} dynamic parallel execution workers.")
        
#         block_size = 1024 * 1024
#         metrics_lock = threading.Lock()
#         global_bytes_downloaded = 0
#         completed_files_count = 0
#         global_start_time = time.time()
        
#         def on_chunk_downloaded(chunk_len):
#             nonlocal global_bytes_downloaded, total_repo_size_bytes, global_start_time
#             with metrics_lock:
#                 global_bytes_downloaded += chunk_len
#                 elapsed_total = time.time() - global_start_time
                
#                 if elapsed_total > 0:
#                     current_speed = (global_bytes_downloaded / (1024**2)) / elapsed_total
#                     engine_status["speed"] = f"{current_speed:.2f} MB/s"
                
#                 if total_repo_size_bytes > 0:
#                     approx_prog = (global_bytes_downloaded / total_repo_size_bytes) * 100
#                     engine_status["progress"] = f"{min(approx_prog, 99.99):.2f}"
                
#                 _, _, free = shutil.disk_usage(local_path)
#                 engine_status["disk_free"] = f"{free / (1024**3):.2f}"

#         def on_file_completed():
#             nonlocal completed_files_count, total_files
#             with metrics_lock:
#                 completed_files_count += 1
#                 engine_status["status"] = f"Piping {MAX_CONCURRENT_DOWNLOADS} streams... Staged {completed_files_count}/{total_files} files."

#         engine_status["status"] = f"Spawning {MAX_CONCURRENT_DOWNLOADS} accelerated worker pipelines..."
        
#         with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as executor:
#             futures = []
#             for item in files_metadata:
#                 file_path = item["path"]
#                 if "api/datasets" in base_api_url or "/datasets/" in repo_id:
#                     download_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{file_path}"
#                 else:
#                     download_url = f"https://huggingface.co/{repo_id}/resolve/main/{file_path}"
                    
#                 dest_file_path = os.path.join(source_dir, file_path)
#                 os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
                
#                 future = executor.submit(
#                     download_single_file_task, 
#                     download_url, dest_file_path, headers, block_size, 
#                     on_chunk_downloaded, on_file_completed
#                 )
#                 futures.append(future)
            
#             for future in as_completed(futures):
#                 try:
#                     future.result()
#                 except Exception as task_error:
#                     print(f"⚠️ Worker pipe reported tracking exception: {task_error}")

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











# stream - drive

# import sys
# sys.path.append('/usr/lib/python3/dist-packages')

# import os
# import time
# import json
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
#     "upload_eta": "-",
#     "active_streams": {}  # Dynamic dictionary rendering independent thread visual components
# }


# def parse_size_to_bytes(value_str, unit_str):
#     """Normalize rclone's human units (KiB, MiB, GiB, B) to raw bytes"""
#     unit_str = unit_str.strip().lower()
#     multipliers = {
#         'b': 1,
#         'kib': 1024, 'mib': 1024**2, 'gib': 1024**3, 'tib': 1024**4,
#         'kb': 1000, 'mb': 1000**2, 'gb': 1000**3, 'tb': 1000**4,
#     }
#     return float(value_str) * multipliers.get(unit_str, 1)


# def get_true_file_size(item):
#     """Extract true LFS file allocation bounds from metadata pointers"""
#     lfs_info = item.get("lfs")
#     if lfs_info and lfs_info.get("size"):
#         return lfs_info["size"]
#     return item.get("size", 0)


# def _format_eta(seconds):
#     seconds = int(seconds)
#     if seconds < 60:
#         return f"{seconds}s"
#     minutes, seconds = divmod(seconds, 60)
#     if minutes < 60:
#         return f"{minutes}m{seconds}s"
#     hours, minutes = divmod(minutes, 60)
#     if hours < 24:
#         return f"{hours}h{minutes}m"
#     days, hours = divmod(hours, 24)
#     return f"{days}d{hours}h"


# def common_rclone_upload_engine(source_dir, display_name):
#     """Shared core engine optimized to push local disk structures concurrently to Google Drive."""
#     global engine_status, is_pipeline_active
#     rclone_errors = []

#     engine_status["status"] = "Cloud download done! Transferring to Google Drive..."
#     engine_status["speed"] = "0.00"
#     engine_status["progress"] = "100.00"
#     engine_status["upload_progress"] = "0"
#     engine_status["upload_speed"] = "0 B/s"
#     engine_status["upload_eta"] = "-"
#     engine_status["active_streams"] = {}

#     dest_dir = f"gdrive:CodespaceDownloads/{display_name}"
#     resolved_config_path = os.path.expanduser("~/.config/rclone/rclone.conf")

#     rclone_cmd = [
#         "rclone", "copy", source_dir, dest_dir,
#         "--config", resolved_config_path,
#         "--transfers", "10",
#         "--multi-thread-streams", "12",
#         "--stats", "1s",
#         "--stats-one-line",
#         "-v",
#         "--use-mmap"
#     ]

#     process = subprocess.Popen(
#         rclone_cmd,
#         stdout=subprocess.PIPE,
#         stderr=subprocess.STDOUT,
#         bufsize=0
#     )

#     progress_regex = re.compile(r"(\d{1,3})%")
#     speed_regex = re.compile(r"(\d+(?:\.\d+)?\s*[a-zA-Z ]+/s)", re.IGNORECASE)
#     eta_global_regex = re.compile(r"ETA\s+(\S+)", re.IGNORECASE)

#     local_log_path = "/workspaces/cloud-extracter/rclone_log.txt"

#     with open(local_log_path, "w", encoding="utf-8") as log_file:
#         byte_buf = b""
#         while True:
#             chunk = process.stdout.read(1)
#             if chunk == b"" and process.poll() is not None:
#                 break

#             if chunk in (b"\n", b"\r"):
#                 cleaned_line = byte_buf.decode('utf-8', errors='ignore').strip()
#                 byte_buf = b""
#                 if not cleaned_line:
#                     continue

#                 print(f"RCLONE OUT: {cleaned_line}", flush=True)
#                 log_file.write(cleaned_line + "\n")
#                 log_file.flush()

#                 if "ERROR" in cleaned_line or "Failed to" in cleaned_line:
#                     rclone_errors.append(cleaned_line)

#                 speed_match = speed_regex.search(cleaned_line)
#                 prog_match = progress_regex.search(cleaned_line)
#                 eta_match = eta_global_regex.search(cleaned_line)

#                 if speed_match:
#                     engine_status["upload_speed"] = speed_match.group(1)
#                 if prog_match:
#                     engine_status["upload_progress"] = prog_match.group(1)
#                 if eta_match:
#                     engine_status["upload_eta"] = eta_match.group(1)
#             else:
#                 byte_buf += chunk

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

#         time.sleep(30)
#         is_pipeline_active = False
#         os.system("pkill -f uvicorn")
#         return
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


# def stream_huggingface_file_task(download_url, dest_dir, file_path, resolved_config_path, headers, callback_bytes_handler):
#     """Streams chunks through Python memory directly into rclone rcat via standard input."""
#     dest_file_target = f"{dest_dir}/{file_path}"
    
#     # Using rclone rcat to receive incoming data directly from stdin pipe channels
#     rclone_cmd = [
#         "rclone", "rcat", dest_file_target,
#         "--config", resolved_config_path
#     ]
    
#     process = subprocess.Popen(
#         rclone_cmd,
#         stdin=subprocess.PIPE,
#         stdout=subprocess.PIPE,
#         stderr=subprocess.PIPE
#     )
    
#     try:
#         # Native unbuffered streaming download loop
#         with requests.get(download_url, headers=headers, stream=True, timeout=30) as r:
#             r.raise_for_status()
#             for chunk in r.iter_content(chunk_size=256 * 1024): # 256KB chunks ensure instantaneous updates
#                 if chunk:
#                     process.stdin.write(chunk)
#                     process.stdin.flush()
#                     callback_bytes_handler(len(chunk), is_done=False)
#         process.stdin.close()
#     except (BrokenPipeError, Exception) as e:
#         print(f"⚠️ Streaming runtime write error on pipe target: {e}")
#         process.kill()
#         return -1
        
#     process.wait()
#     callback_bytes_handler(0, is_done=True)
#     return process.returncode


# def download_huggingface_worker(repo_id: str, repo_type: str):
#     global engine_status, is_pipeline_active
#     try:
#         folder_friendly_name = repo_id.replace("/", "--")
#         engine_status["name"] = f"HF ➔ {repo_id}"
#         engine_status["status"] = "Contacting Hugging Face API Metadata Hub..."

#         engine_status["speed"] = "0.00"
#         engine_status["progress"] = "0.00"
#         engine_status["upload_progress"] = "0"
#         engine_status["upload_speed"] = "0 B/s"
#         engine_status["upload_eta"] = "-"
#         engine_status["active_streams"] = {}

#         headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
#         resolved_config_path = os.path.expanduser("~/.config/rclone/rclone.conf")
#         dest_dir = f"gdrive:CodespaceDownloads/{folder_friendly_name}"

#         base_api_url = f"https://huggingface.co/api/{repo_type}s/{repo_id}/tree/main"
#         files_metadata = []
#         params = {"recursive": "true"}

#         while True:
#             res = requests.get(base_api_url, headers=headers, params=params, timeout=15)
#             if res.status_code == 404 and "api/datasets" not in base_api_url:
#                 base_api_url = f"https://huggingface.co/api/datasets/{repo_id}/tree/main"
#                 res = requests.get(base_api_url, headers=headers, params=params, timeout=15)

#             res.raise_for_status()
#             raw_items = res.json()
#             if not raw_items:
#                 break

#             page_files = [
#                 item for item in raw_items
#                 if item.get("type") == "file" and not os.path.basename(item["path"]).startswith('.')
#             ]
#             files_metadata.extend(page_files)

#             if "Link" in res.headers:
#                 match = re.search(r'<(https://[^>]+)>;\s*rel="next"', res.headers["Link"])
#                 if match:
#                     base_api_url = match.group(1)
#                     params = {}
#                     continue
#             if len(raw_items) >= 1000:
#                 params["cursor"] = raw_items[-1]["path"]
#             else:
#                 break

#         total_files = len(files_metadata)
#         if total_files == 0:
#             raise Exception("No operational files detected inside the parsed repository directory path mapping.")

#         file_sizes = {item["path"]: get_true_file_size(item) for item in files_metadata}
#         grand_total_bytes = sum(file_sizes.values()) or 1

#         metrics_lock = threading.Lock()
#         bytes_done_per_file = {path: 0 for path in file_sizes}
#         completed_files_count = 0

#         # Centralized Speed Clock Parameters
#         last_sample_time = time.time()
#         last_sample_bytes = 0

#         def make_bytes_handler(file_path):
#             """Generates independent, native metrics listeners tracking file-level deltas instantly"""
#             f_name = os.path.basename(file_path)
#             file_start_time = time.time()
            
#             def handle_bytes(chunk_len, is_done):
#                 with metrics_lock:
#                     if is_done:
#                         engine_status["active_streams"].pop(f_name, None)
#                         return
                        
#                     bytes_done_per_file[file_path] += chunk_len
#                     done = bytes_done_per_file[file_path]
#                     total = file_sizes.get(file_path, 0) or 1
                    
#                     pct = min((done / total) * 100, 100.0)
#                     elapsed = time.time() - file_start_time
                    
#                     if elapsed > 0:
#                         f_speed = (done / (1024 * 1024)) / elapsed
#                         speed_str = f"{f_speed:.2f} MB/s"
#                         eta_str = _format_eta((total - done) / (done / elapsed)) if f_speed > 0.01 else "-"
#                     else:
#                         speed_str = "Calculating..."
#                         eta_str = "-"
                        
#                     # Push independent multi-stream tracking state arrays straight to the global API context map
#                     engine_status["active_streams"][f_name] = {
#                         "speed": speed_str,
#                         "progress": f"{pct:.2f}",
#                         "eta": eta_str
#                     }
#             return handle_bytes

#         # Centralized metrics ticking thread engine
#         stop_ticker_event = threading.Event()

#         def global_metrics_ticker_loop():
#             nonlocal last_sample_time, last_sample_bytes
#             while not stop_ticker_event.is_set():
#                 time.sleep(0.5)
#                 with metrics_lock:
#                     total_done = sum(bytes_done_per_file.values())
#                     now = time.time()
#                     elapsed = now - last_sample_time

#                     if elapsed >= 0.5:
#                         delta_bytes = total_done - last_sample_bytes
#                         speed_bps = delta_bytes / elapsed if elapsed > 0 else 0
#                         speed_mbps = speed_bps / (1024 * 1024)

#                         engine_status["speed"] = f"{speed_mbps:.2f}"
#                         engine_status["upload_speed"] = f"{speed_mbps:.2f} MB/s"

#                         remaining_bytes = grand_total_bytes - total_done
#                         MIN_TRUSTED_SPEED_BPS = 50 * 1024  
#                         if speed_bps > MIN_TRUSTED_SPEED_BPS:
#                             engine_status["upload_eta"] = _format_eta(remaining_bytes / speed_bps)
#                         else:
#                             engine_status["upload_eta"] = "calculating..."

#                         last_sample_time = now
#                         last_sample_bytes = total_done

#                     pct = (total_done / grand_total_bytes) * 100
#                     engine_status["progress"] = f"{pct:.2f}"

#                     file_pct = (completed_files_count / total_files) * 100
#                     engine_status["upload_progress"] = str(int(file_pct))
#                     engine_status["status"] = f"Streaming... {completed_files_count}/{total_files} files complete, {pct:.1f}% of total bytes."

#         ticker_thread = threading.Thread(target=global_metrics_ticker_loop, daemon=True)
#         ticker_thread.start()

#         # Initialize the target parent workspace structure before splitting threads
#         subprocess.run(["rclone", "mkdir", dest_dir, "--config", resolved_config_path], capture_output=True)

#         MAX_STREAMING_WORKERS = min(5, total_files)
#         with ThreadPoolExecutor(max_workers=MAX_STREAMING_WORKERS) as executor:
#             futures = {}
#             for item in files_metadata:
#                 file_path = item["path"]
#                 if "api/datasets" in base_api_url or "/datasets/" in repo_id:
#                     download_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{file_path}"
#                 else:
#                     download_url = f"https://huggingface.co/{repo_id}/resolve/main/{file_path}"

#                 bytes_callback = make_bytes_handler(file_path)

#                 future = executor.submit(
#                     stream_huggingface_file_task,
#                     download_url, dest_dir, file_path, resolved_config_path,
#                     headers, bytes_callback
#                 )
#                 futures[future] = file_path

#             for future in as_completed(futures):
#                 path = futures[future]
#                 try:
#                     exit_code = future.result()
#                     if exit_code != 0:
#                         raise Exception(f"Streaming failed with exit code {exit_code} for {path}")
#                     with metrics_lock:
#                         completed_files_count += 1
#                 except Exception as task_error:
#                     print(f"⚠️ Streaming pipeline reported thread failure: {task_error}")
#                     stop_ticker_event.set()
#                     raise task_error

#         stop_ticker_event.set()
#         ticker_thread.join()

#         engine_status["status"] = "Success! Content securely saved in Google Drive."
#         engine_status["progress"] = "100.00"
#         engine_status["upload_progress"] = "100"
#         engine_status["upload_speed"] = "0 B/s"
#         engine_status["upload_eta"] = "0s"
#         engine_status["active_streams"] = {}

#         time.sleep(30)
#         is_pipeline_active = False
#         os.system("pkill -f uvicorn")

#     except Exception as e:
#         engine_status["status"] = f"❌ Streaming Engine Error: {str(e)}"
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


# @app.get("/api/v1/explore_drive")
# def explore_drive(path: str = ""):
#     resolved_config_path = os.path.expanduser("~/.config/rclone/rclone.conf")
#     remote_path = f"gdrive:CodespaceDownloads/{path}".rstrip("/")

#     try:
#         result = subprocess.run(
#             ["rclone", "lsjson", remote_path, "--config", resolved_config_path],
#             capture_output=True, text=True, timeout=20
#         )
#         if result.returncode != 0:
#             return {"status": "error", "items": [], "message": result.stderr.strip()}

#         raw_items = json.loads(result.stdout or "[]")
#         items = [
#             {
#                 "name": it["Name"],
#                 "type": "directory" if it.get("IsDir") else "file",
#                 "relative_path": f"{path}/{it['Name']}" if path else it["Name"],
#             }
#             for it in raw_items
#         ]
#         return {"status": "success", "items": items}
#     except Exception as e:
#         return {"status": "error", "items": [], "message": str(e)}


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
import json
import shutil
import subprocess
import re
import requests
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import FastAPI, BackgroundTasks, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import libtorrent as lt

app = FastAPI()

# -------------------------------------------------------------------------
# 🔥 NEW: SYSTEM WORKFLOW LOGGER ARCHITECTURE
# -------------------------------------------------------------------------
LOG_FILE_PATH = "/workspaces/cloud-extracter/server_workflow.log"

# Setup robust multi-threaded formatting configuration
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [Thread-%(thread)d] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout) # Mirrors logs straight to terminal console
    ]
)
logger = logging.getLogger("WorkflowEngine")

logger.info("=========================================================")
logger.info("🚀 INITIALIZING CLOUD EXTRACTER WORKFLOW BACKEND ENGINE")
logger.info("=========================================================")

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
    logger.debug(f"Incoming Request HTTP Method: {request.method} | Path: {request.url.path}")
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
    "upload_eta": "-",
    "active_streams": {}  
}

def parse_size_to_bytes(value_str, unit_str):
    unit_str = unit_str.strip().lower()
    multipliers = {
        'b': 1, 'kib': 1024, 'mib': 1024**2, 'gib': 1024**3, 'tib': 1024**4,
        'kb': 1000, 'mb': 1000**2, 'gb': 1000**3, 'tb': 1000**4,
    }
    return float(value_str) * multipliers.get(unit_str, 1)

def get_true_file_size(item):
    lfs_info = item.get("lfs")
    if lfs_info and lfs_info.get("size"):
        return lfs_info["size"]
    return item.get("size", 0)

def _format_eta(seconds):
    seconds = int(seconds)
    if seconds < 60: return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60: return f"{minutes}m{seconds}s"
    hours, minutes = divmod(minutes, 60)
    if hours < 24: return f"{hours}h{minutes}m"
    days, hours = divmod(hours, 24)
    return f"{days}d{hours}h"

def common_rclone_upload_engine(source_dir, display_name):
    global engine_status, is_pipeline_active
    logger.info(f"⚡ Launching local-to-cloud disk transfer engine for payload: {display_name}")
    logger.info(f"Target Source Directory Path: {source_dir}")
    
    rclone_errors = []
    engine_status["status"] = "Cloud download done! Transferring to Google Drive..."
    dest_dir = f"newdrive-64:CodespaceDownloads/{display_name}"
    resolved_config_path = os.path.expanduser("~/.config/rclone/rclone.conf")

    rclone_cmd = [
        "rclone", "copy", source_dir, dest_dir,
        "--config", resolved_config_path,
        "--transfers", "10", "--multi-thread-streams", "12",
        "--stats", "1s", "--stats-one-line", "-v", "--use-mmap"
    ]
    
    logger.info(f"Executing subprocess command array: {' '.join(rclone_cmd)}")
    process = subprocess.Popen(rclone_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
    
    progress_regex = re.compile(r"(\d{1,3})%")
    speed_regex = re.compile(r"(\d+(?:\.\d+)?\s*[a-zA-Z ]+/s)", re.IGNORECASE)
    eta_global_regex = re.compile(r"ETA\s+(\S+)", re.IGNORECASE)

    local_log_path = "/workspaces/cloud-extracter/rclone_log.txt"
    with open(local_log_path, "w", encoding="utf-8") as log_file:
        byte_buf = b""
        while True:
            chunk = process.stdout.read(1)
            if chunk == b"" and process.poll() is not None: break
            if chunk in (b"\n", b"\r"):
                cleaned_line = byte_buf.decode('utf-8', errors='ignore').strip()
                byte_buf = b""
                if not cleaned_line: continue
                log_file.write(cleaned_line + "\n")
                log_file.flush()
                
                if "ERROR" in cleaned_line or "Failed to" in cleaned_line:
                    rclone_errors.append(cleaned_line)
                    logger.warning(f"[Rclone Runtime Flag] {cleaned_line}")
                
                speed_match = speed_regex.search(cleaned_line)
                prog_match = progress_regex.search(cleaned_line)
                eta_match = eta_global_regex.search(cleaned_line)
                if speed_match: engine_status["upload_speed"] = speed_match.group(1)
                if prog_match: engine_status["upload_progress"] = prog_match.group(1)
                if eta_match: engine_status["upload_eta"] = eta_match.group(1)
            else:
                byte_buf += chunk

    process.wait()
    exit_code = process.returncode
    logger.info(f"Rclone copy process exited with status token code: {exit_code}")

    if exit_code == 0:
        logger.info("🎉 Disk-to-Drive pipeline complete! Clearing local cache directory partitions.")
        engine_status["status"] = "Success! Content securely saved in Google Drive."
        try:
            if os.path.isdir(source_dir): 
                shutil.rmtree(source_dir)
                logger.info(f"Successfully scrubbed folder structure: {source_dir}")
            elif os.path.isfile(source_dir): 
                os.remove(source_dir)
                logger.info(f"Successfully scrubbed target file path: {source_dir}")
        except Exception as ce: 
            logger.error(f"⚠️ Cache flush optimization warnings generated: {str(ce)}")
            
        logger.info("⏳ Core work complete. Entering termination cooldown block...")
        time.sleep(10)
        is_pipeline_active = False
        logger.info("💀 Flushing system process instance: pkill -f uvicorn initiated.")
        os.system("pkill -f uvicorn")
    else:
        err_msg = rclone_errors[-1] if rclone_errors else 'Subprocess breakdown'
        logger.critical(f"❌ Core Disk Upload Process Aborted: {err_msg}")
        engine_status["status"] = f"❌ Upload Error: {err_msg}"
        is_pipeline_active = False

def download_and_push_worker(magnet_link: str):
    global engine_status, is_pipeline_active
    logger.info("🧲 Initializing Torrent pipeline extraction worker routine.")
    try:
        engine_status["status"] = "Connecting to Swarm Network..."
        ses = lt.session()
        ses.listen_on(6881, 6891)
        local_path = '/tmp/downloads'
        os.makedirs(local_path, exist_ok=True)
        magnet_link = magnet_link.strip()

        if magnet_link.startswith("http://") or magnet_link.startswith("https://"):
            logger.info(f"Target detected as web-hosted torrent metadata block file: {magnet_link}")
            r = requests.get(magnet_link, timeout=15)
            r.raise_for_status()
            torrent_path = os.path.join('/tmp', 'downloaded.torrent')
            with open(torrent_path, 'wb') as f: f.write(r.content)
            torrent_info = lt.torrent_info(torrent_path)
            torrent_name = torrent_info.name()
            add_params = {'ti': torrent_info, 'save_path': local_path, 'storage_mode': lt.storage_mode_t.storage_mode_sparse}
            handle = ses.add_torrent(add_params)
        else:
            logger.info("Target detected as standard protocol raw magnet URI string parameters.")
            if len(magnet_link) == 40 and all(c in '0123456789abcdefABCDEF' for c in magnet_link):
                magnet_link = f"magnet:?xt=urn:btih:{magnet_link}"
            params = {'save_path': local_path, 'storage_mode': lt.storage_mode_t.storage_mode_sparse}
            handle = lt.add_magnet_uri(ses, magnet_link, params)
            logger.info("Awaiting initial swarm metadata retrieval pipeline hook...")
            while not handle.has_metadata(): time.sleep(1)
            torrent_info = handle.get_torrent_info()
            torrent_name = torrent_info.name()

        logger.info(f"Target swarm meta-identity acquired: [{torrent_name}]. Initializing cloud block streaming structures.")
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
            logger.info(f"[Swarm Sync Info] Progress: {engine_status['progress']}% | Speed: {engine_status['speed']} MB/s | Active Swarm Peers: {engine_status['peers']}")
            time.sleep(4)

        logger.info("🔥 Swarm seeding parameters matched. Deregistering handle block routines.")
        ses.remove_torrent(handle)
        common_rclone_upload_engine(os.path.join(local_path, torrent_name), torrent_name)
    except Exception as e:
        logger.exception("❌ Error encountered inside swarm worker sequence thread:")
        engine_status["status"] = f"❌ Torrent Error: {str(e)}"
        is_pipeline_active = False

def stream_huggingface_file_task(download_url, dest_dir, file_path, resolved_config_path, file_total_bytes, headers, callback_bytes_handler):
    f_name = os.path.basename(file_path)
    dest_file_target = f"{dest_dir}/{file_path}"
    
    logger.info(f"📥 [Thread Spawn] Preparing stream pipe for target file object -> {f_name} ({file_total_bytes} Bytes)")
    
    for attempt in range(1, 4):
        logger.info(f"➡️ [Attempt {attempt}/3] Spawning pipe stream link layer for: {f_name}")
        rclone_cmd = ["rclone", "rcat", dest_file_target, "--config", resolved_config_path]
        process = subprocess.Popen(rclone_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            with requests.get(download_url, headers=headers, stream=True, timeout=30) as r:
                r.raise_for_status()
                logger.info(f"🔗 [HTTP Connected] Direct download link established for file shard: {f_name}")
                for chunk in r.iter_content(chunk_size=4 * 1024 * 1024): 
                    if chunk:
                        process.stdin.write(chunk)
                        # process.stdin.flush()  # Optimized: Disabled active blocking flushes
                        callback_bytes_handler(len(chunk), is_done=False, exit_code=None)
            process.stdin.close()
            logger.debug(f"📤 Memory channel dump finished for shard object: {f_name}. Awaiting rclone flush.")
        except Exception as e:
            logger.error(f"⚠️ [Attempt {attempt}/3] Network exception caught during runtime memory pipe mapping of {f_name} -> {e}")
            process.kill()
            process.wait()
            if attempt == 3:
                logger.critical(f"❌ [Aborted Shard] Absolute thread execution failure sustained on target file: {f_name}")
                callback_bytes_handler(0, is_done=True, exit_code=-1)
                return -1
            time.sleep(5)
            continue
        
        try:
            logger.info(f"⏳ [Awaiting Cloud Commit] Waiting for Google Drive to confirm closing handshake for: {f_name}")
            exit_code = process.wait(timeout=300)
            if exit_code == 0:
                logger.info(f"✅ [File Success] Shard successfully committed, closed, and saved in remote Drive: {f_name}")
                callback_bytes_handler(file_total_bytes, is_done=True, exit_code=0)
                return 0
            else:
                logger.error(f"⚠️ [Attempt {attempt}/3] rclone closed with non-zero code {exit_code} on shard finalization for {f_name}")
        except subprocess.TimeoutExpired:
            logger.warning(f"⚠️ [Attempt {attempt}/3] Finalization timeout reached (300s) on Google Drive for {f_name}. Re-spawning pipeline.")
            process.kill()
            process.wait()
            
        if attempt == 3:
            logger.critical(f"❌ [Aborted Shard] 3 consecutive errors sustained. Aborting file link stream: {f_name}")
            callback_bytes_handler(0, is_done=True, exit_code=-1)
            return -1
        time.sleep(5)
    return -1

def download_huggingface_worker(repo_id: str, repo_type: str):
    global engine_status, is_pipeline_active
    logger.info(f"🤗 Initializing Hugging Face workflow syncing layout engine. Repository: {repo_id} | Type: {repo_type}")
    try:
        folder_friendly_name = repo_id.replace("/", "--")
        engine_status["name"] = f"HF ➔ {repo_id}"
        engine_status["status"] = "Contacting Hugging Face API Metadata Hub..."
        engine_status["active_streams"] = {}

        # Optimized: Reading Bearer token dynamically from system variables to bypass Git leaks
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Authorization": f"Bearer {os.environ.get('HF_TOKEN', '')}"
        }
        resolved_config_path = os.path.expanduser("~/.config/rclone/rclone.conf")
        
        # Upgraded remote path target destination pointer
        dest_dir = f"newdrive-64:CodespaceDownloads/{folder_friendly_name}"

        base_api_url = f"https://huggingface.co/api/{repo_type}s/{repo_id}/tree/main"
        files_metadata = []
        params = {"recursive": "true"}

        logger.info(f"Querying Hugging Face API Tree Node Mapping endpoint URL: {base_api_url}")
        while True:
            res = requests.get(base_api_url, headers=headers, params=params, timeout=15)
            if res.status_code == 404 and "api/datasets" not in base_api_url:
                logger.info("🔄 Tree route returned 404 status code. Re-routing endpoint to Dataset namespace hierarchy parameters.")
                base_api_url = f"https://huggingface.co/api/datasets/{repo_id}/tree/main"
                res = requests.get(base_api_url, headers=headers, params=params, timeout=15)
            
            res.raise_for_status()
            raw_items = res.json()
            if not raw_items: break
            
            page_files = [item for item in raw_items if item.get("type") == "file" and not os.path.basename(item["path"]).startswith('.')]
            files_metadata.extend(page_files)
            
            if "Link" in res.headers:
                match = re.search(r'<(https://[^>]+)>;\s*rel="next"', res.headers["Link"])
                if match:
                    base_api_url = match.group(1)
                    params = {}
                    logger.debug(f"Paging Hugging Face model registry tree cursor layer: {base_api_url}")
                    continue
            if len(raw_items) >= 1000: 
                params["cursor"] = raw_items[-1]["path"]
            else: 
                break

        total_files = len(files_metadata)
        logger.info(f"Metadata scanning sequence resolved successfully. Found {total_files} file objects to fetch.")

        if total_files == 0: raise Exception("No operational files detected inside the parsed repository directory path mapping.")

        file_sizes = {item["path"]: get_true_file_size(item) for item in files_metadata}
        grand_total_bytes = sum(file_sizes.values()) or 1
        logger.info(f"Calculated Target Repository Weight Density Blueprint: {grand_total_bytes / (1024**3):.3f} GB total allocation metrics.")

        metrics_lock = threading.Lock()
        bytes_done_per_file = {path: 0 for path in file_sizes}
        completed_files_count = 0
        failed_files_count = 0

        last_sample_time = time.time()
        last_sample_bytes = 0

        def make_bytes_handler(file_path):
            f_name = os.path.basename(file_path)
            file_start_time = time.time()
            
            def handle_bytes(chunk_len, is_done, exit_code=None):
                nonlocal completed_files_count, failed_files_count
                with metrics_lock:
                    if is_done:
                        engine_status["active_streams"].pop(f_name, None)
                        if exit_code == 0:
                            completed_files_count += 1
                            logger.info(f"📈 Workflow Progress Counter Update: [{completed_files_count}/{total_files}] files successfully landed.")
                        else:
                            failed_files_count += 1
                            logger.error(f"📉 Workflow Error Counter Update: [{failed_files_count}] items registered as anomalies.")
                        return
                        
                    bytes_done_per_file[file_path] += chunk_len
                    done = bytes_done_per_file[file_path]
                    total = file_sizes.get(file_path, 0) or 1
                    pct = min((done / total) * 100, 100.0)
                    elapsed = time.time() - file_start_time
                    
                    if elapsed > 0:
                        f_speed = (done / (1024 * 1024)) / elapsed
                        speed_str = f"{f_speed:.2f} MB/s"
                        eta_str = _format_eta((total - done) / (done / elapsed)) if f_speed > 0.01 else "-"
                    else:
                        speed_str = "Calculating..."
                        eta_str = "-"
                        
                    engine_status["active_streams"][f_name] = {
                        "speed": speed_str, "progress": f"{pct:.2f}", "eta": eta_str
                    }
            return handle_bytes

        stop_ticker_event = threading.Event()

        def global_metrics_ticker_loop():
            nonlocal last_sample_time, last_sample_bytes
            while not stop_ticker_event.is_set():
                time.sleep(2.0) # Throttled logs log updates to every 2 seconds to ensure log cleanliness
                with metrics_lock:
                    total_done = sum(bytes_done_per_file.values())
                    now = time.time()
                    elapsed = now - last_sample_time
                    if elapsed >= 0.5:
                        delta_bytes = total_done - last_sample_bytes
                        speed_bps = delta_bytes / elapsed if elapsed > 0 else 0
                        speed_mbps = speed_bps / (1024 * 1024)
                        engine_status["speed"] = f"{speed_mbps:.2f}"
                        engine_status["upload_speed"] = f"{speed_mbps:.2f} MB/s"
                        remaining_bytes = grand_total_bytes - total_done
                        if speed_bps > 50 * 1024:
                            engine_status["upload_eta"] = _format_eta(remaining_bytes / speed_bps)
                        else:
                            engine_status["upload_eta"] = "calculating..."
                        last_sample_time = now
                        last_sample_bytes = total_done

                    pct = (total_done / grand_total_bytes) * 100
                    engine_status["progress"] = f"{pct:.2f}"
                    file_pct = ((completed_files_count + failed_files_count) / total_files) * 100
                    engine_status["upload_progress"] = str(int(file_pct))
                    engine_status["status"] = f"Streaming... {completed_files_count}/{total_files} complete ({failed_files_count} skipped/failed)."
                    
                    logger.info(f"[Global Workflow Pulse] Overall Progress: {engine_status['progress']}% | Aggregated Pipe Throughput: {engine_status['upload_speed']} | Global Network ETA: {engine_status['upload_eta']} | Files Handled: {completed_files_count + failed_files_count}/{total_files}")

        ticker_thread = threading.Thread(target=global_metrics_ticker_loop, daemon=True)
        ticker_thread.start()

        logger.info(f"Ensuring parent extraction target space exists inside Google Drive path: {dest_dir}")
        subprocess.run(["rclone", "mkdir", dest_dir, "--config", resolved_config_path], capture_output=True)

        MAX_STREAMING_WORKERS = min(4, total_files) # Optimized: set to 4 to protect Drive API Creation quotas
        logger.info(f"Spawning target parallel execution matrix using ThreadPoolExecutor size ceiling: {MAX_STREAMING_WORKERS}")
        
        with ThreadPoolExecutor(max_workers=MAX_STREAMING_WORKERS) as executor:
            futures = {}
            for item in files_metadata:
                file_path = item["path"]
                if "api/datasets" in base_api_url or "/datasets/" in repo_id:
                    download_url = f"https://huggingface.co/datasets/{repo_id}/resolve/main/{file_path}"
                else:
                    download_url = f"https://huggingface.co/{repo_id}/resolve/main/{file_path}"

                bytes_callback = make_bytes_handler(file_path)
                time.sleep(0.25)

                future = executor.submit(
                    stream_huggingface_file_task,
                    download_url, dest_dir, file_path, resolved_config_path,
                    file_sizes.get(file_path, 0), headers, bytes_callback
                )
                futures[future] = file_path

            for future in as_completed(futures):
                path = futures[future]
                try:
                    future.result()
                except Exception as task_error:
                    logger.error(f"❌ Thread execution pool caught fatal unhandled structural task drop on object path [{path}]: {task_error}")

        logger.info("🏁 All execution threads joined inside context block scope boundary limits. Terminating metrics loops.")
        stop_ticker_event.set()
        ticker_thread.join()

        # Update final engine tracking logs status metrics
        engine_status["status"] = f"Finished processing layout structure. Completed: {completed_files_count}, Errors: {failed_files_count}"
        engine_status["progress"] = "100.00"
        engine_status["upload_progress"] = "100"
        engine_status["upload_speed"] = "finished"
        engine_status["upload_eta"] = "arrived"
        engine_status["active_streams"] = {}

        logger.info("=========================================================")
        logger.info(f"🏁 PIPELINE SYNC COMPLETE. Summary -> Successful: {completed_files_count} | Aborted: {failed_files_count} out of {total_files} files.")
        logger.info("Entering 2-minute workflow hold phase for final cloud indexing allocation updates...")
        logger.info("=========================================================")
        
        time.sleep(120) 
        is_pipeline_active = False
        logger.info("💀 Hold phase complete. Issuing final instance uvicorn server kill signal.")
        os.system("pkill -f uvicorn")

    except Exception as e:
        logger.exception("❌ Critical engine breakdown triggered during active pipeline run configuration:")
        engine_status["status"] = f"❌ Streaming Engine Fatal Error: {str(e)}"
        is_pipeline_active = False

@app.post("/api/v1/enqueue")
def enqueue_link(background_tasks: BackgroundTasks, magnet_link: str = Form(...)):
    global is_pipeline_active
    logger.info(f"📥 POST endpoint trigger: /api/v1/enqueue accessed. Pipeline state token: {is_pipeline_active}")
    if is_pipeline_active: 
        logger.warning("Pipeline request rejected: Core Engine status evaluates to BUSY.")
        return {"status": "ignored", "message": "Pipeline busy."}
    is_pipeline_active = True
    background_tasks.add_task(download_and_push_worker, magnet_link)
    return {"message": "Torrent pipeline triggered successfully."}

@app.post("/api/v1/enqueue_hf")
def enqueue_hf(background_tasks: BackgroundTasks, repo_id: str = Form(...)):
    global is_pipeline_active
    logger.info(f"📥 POST endpoint trigger: /api/v1/enqueue_hf accessed. Input ID parsed: {repo_id}")
    if is_pipeline_active: 
        logger.warning("Pipeline request rejected: Core Engine status evaluates to BUSY.")
        return {"status": "ignored", "message": "Pipeline busy."}
        
    raw_input = repo_id.strip()
    repo_type = "model"
    if "huggingface.co/datasets/" in raw_input:
        repo_type = "dataset"
        parsed_id = raw_input.split("huggingface.co/datasets/")[1]
    elif "huggingface.co/" in raw_input:
        repo_type = "model"
        parsed_id = raw_input.split("huggingface.co/")[1]
    else: parsed_id = raw_input
    
    clean_repo_id = parsed_id.split("/tree/")[0].split("/blob/")[0].strip()
    is_pipeline_active = True
    background_tasks.add_task(download_huggingface_worker, clean_repo_id, repo_type)
    return {"message": f"Hugging Face sync routine armed for {clean_repo_id}!"}

@app.get("/api/v1/status")
def get_engine_status(): 
    return engine_status

@app.get("/api/v1/explore_drive")
def explore_drive(path: str = ""):
    resolved_config_path = os.path.expanduser("~/.config/rclone/rclone.conf")
    remote_path = f"newdrive-64:CodespaceDownloads/{path}".rstrip("/") # Upgraded target endpoint Explorer path
    try:
        result = subprocess.run(["rclone", "lsjson", remote_path, "--config", resolved_config_path], capture_output=True, text=True, timeout=20)
        if result.returncode != 0: return {"status": "error", "items": [], "message": result.stderr.strip()}
        raw_items = json.loads(result.stdout or "[]")
        items = [{"name": it["Name"], "type": "directory" if it.get("IsDir") else "file", "relative_path": f"{path}/{it['Name']}" if path else it["Name"]} for it in raw_items]
        return {"status": "success", "items": items}
    except Exception as e: return {"status": "error", "items": [], "message": str(e)}

@app.post("/api/v1/shutdown")
def kill_instance_server():
    logger.info("🛑 POST endpoint /api/v1/shutdown triggered by direct API call.")
    def target_shutdown():
        time.sleep(2)
        os.system("pkill -f uvicorn")
    threading.Thread(target=target_shutdown).start()
    return {"status": "Success"}