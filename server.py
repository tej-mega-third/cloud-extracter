# import sys
# sys.path.append('/usr/lib/python3/dist-packages')

# import os
# import time
# import shutil
# from fastapi import FastAPI, BackgroundTasks, Form, Request
# from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
# import libtorrent as lt

# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

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

# STAGING_DIR = '/tmp/downloads'
# os.makedirs(STAGING_DIR, exist_ok=True)
# app.mount("/files", StaticFiles(directory=STAGING_DIR), name="files")

# is_pipeline_active = False
# engine_status = {
#     "status": "Sleeping",
#     "name": "None",
#     "progress": "0.00",
#     "speed": "0.00",
#     "peers": 0,
#     "disk_free": "0.00",
#     "ready_for_local_sync": False
# }

# def download_torrent_worker(magnet_link: str):
#     global engine_status, is_pipeline_active
    
#     try:
#         engine_status["status"] = "Connecting to Academic Swarm Network..."
        
#         ses = lt.session()
#         ses.listen_on(6881, 6891)
        
#         params = {
#             'save_path': STAGING_DIR, 
#             'storage_mode': lt.storage_mode_t.storage_mode_sparse
#         }
#         handle = lt.add_magnet_uri(ses, magnet_link, params)
        
#         while not handle.has_metadata():
#             time.sleep(1)
            
#         handle.set_flags(lt.torrent_flags.sequential_download)
#         torrent_info = handle.get_torrent_info()
#         engine_status["name"] = torrent_info.name()
#         engine_status["status"] = "Staging Data on Cloud Instance..."
        
#         while not handle.status().is_seeding:
#             s = handle.status()
#             engine_status["speed"] = f"{s.download_rate / (1024 * 1024):.2f}"
#             engine_status["progress"] = f"{s.progress * 100:.2f}"
#             engine_status["peers"] = s.num_peers
            
#             _, _, free = shutil.disk_usage(STAGING_DIR)
#             engine_status["disk_free"] = f"{free / (1024**3):.2f}"
#             time.sleep(2)
            
#         engine_status["status"] = "Staging Complete! Awaiting Local PC Sync..."
#         engine_status["speed"] = "0.00"
#         engine_status["progress"] = "100.00"
#         engine_status["ready_for_local_sync"] = True
#         print("Dataset completely cached in cloud staging array. System awaiting local hook.")
        
#     except Exception as e:
#         engine_status["status"] = f"❌ Cloud Fetch Error: {str(e)}"
#         is_pipeline_active = False

# @app.post("/api/v1/enqueue")
# def enqueue_link(background_tasks: BackgroundTasks, magnet_link: str = Form(...)):
#     global is_pipeline_active
#     if is_pipeline_active:
#         return {"status": "ignored", "message": "Pipeline busy handling another asset queue."}
        
#     is_pipeline_active = True
#     engine_status["ready_for_local_sync"] = False
#     engine_status["progress"] = "0.00"
#     engine_status["speed"] = "0.00"
    
#     background_tasks.add_task(download_torrent_worker, magnet_link)
#     return {"message": "Pipeline triggered successfully on cloud worker environment."}

# @app.get("/api/v1/status")
# def get_engine_status():
#     return engine_status

# @app.get("/api/v1/directory")
# def list_staged_files():
#     if not engine_status["ready_for_local_sync"]:
#         return {"files": [], "error": "Data staging incomplete"}
        
#     file_list = []
#     target_path = os.path.join(STAGING_DIR, engine_status["name"])
    
#     if os.path.isfile(target_path):
#         file_list.append({
#             "rel_path": engine_status["name"], 
#             "size": os.path.getsize(target_path)
#         })
#     elif os.path.isdir(target_path):
#         for root, _, files in os.walk(target_path):
#             for file in files:
#                 full_path = os.path.join(root, file)
#                 rel_path = os.path.relpath(full_path, STAGING_DIR)
#                 file_list.append({
#                     "rel_path": rel_path, 
#                     "size": os.path.getsize(full_path)
#                 })
                
#     return {
#         "target_name": engine_status["name"],
#         "files": file_list,
#         "download_prefix": "/files/"
#     }

# @app.post("/api/v1/shutdown")
# def kill_instance_server():
#     print("Local transmission finalized. Sending death signal to web engine shell...")
#     def target_shutdown():
#         time.sleep(2)
#         os.system("pkill -f uvicorn")
    
#     import threading
#     threading.Thread(target=target_shutdown).start()
#     return {"status": "Success", "message": "Uvicorn worker execution terminated cleanly."}\











import sys
sys.path.append('/usr/lib/python3/dist-packages')

import os
import time
import shutil
from fastapi import FastAPI, BackgroundTasks, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import libtorrent as lt

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

STAGING_DIR = '/tmp/downloads'
os.makedirs(STAGING_DIR, exist_ok=True)

is_pipeline_active = False
engine_status = {
    "status": "Sleeping",
    "name": "None",
    "progress": "0.00",
    "speed": "0.00",
    "peers": 0,
    "disk_free": "0.00",
    "ready_for_local_sync": False
}

def download_torrent_worker(magnet_link: str):
    global engine_status, is_pipeline_active
    try:
        engine_status["status"] = "Connecting to Swarm Infrastructure..."
        ses = lt.session()
        ses.listen_on(6881, 6891)
        params = {'save_path': STAGING_DIR, 'storage_mode': lt.storage_mode_t.storage_mode_sparse}
        handle = lt.add_magnet_uri(ses, magnet_link, params)
        
        while not handle.has_metadata():
            time.sleep(1)
            
        handle.set_flags(lt.torrent_flags.sequential_download)
        torrent_info = handle.get_torrent_info()
        engine_status["name"] = torrent_info.name()
        engine_status["status"] = "Caching Data on Instance Drive..."
        
        while not handle.status().is_seeding:
            s = handle.status()
            engine_status["speed"] = f"{s.download_rate / (1024 * 1024):.2f}"
            engine_status["progress"] = f"{s.progress * 100:.2f}"
            engine_status["peers"] = s.num_peers
            _, _, free = shutil.disk_usage(STAGING_DIR)
            engine_status["disk_free"] = f"{free / (1024**3):.2f}"
            time.sleep(2)
            
        engine_status["status"] = "Staging Complete! Awaiting Local PC Sync..."
        engine_status["progress"] = "100.00"
        engine_status["ready_for_local_sync"] = True
        
    except Exception as e:
        engine_status["status"] = f"❌ Staging Error: {str(e)}"
        is_pipeline_active = False

@app.post("/api/v1/enqueue")
def enqueue_link(background_tasks: BackgroundTasks, magnet_link: str = Form(...)):
    global is_pipeline_active
    if is_pipeline_active: return {"status": "ignored"}
    is_pipeline_active = True
    engine_status["ready_for_local_sync"] = False
    background_tasks.add_task(download_torrent_worker, magnet_link)
    return {"message": "Pipeline triggered successfully."}

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