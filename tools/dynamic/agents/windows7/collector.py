from __future__ import print_function

import datetime
import json
import os
import shutil
import subprocess
import sys
import time
import traceback

try:
    from urllib import request as urllib_request
except ImportError:
    import urllib2 as urllib_request




SHARED_PATH = r"\\VBOXSVR\shared"
WORKING_PATH = r"C:\AIM"

JOB_FILENAME = "job.json"

MONITOR_URL = "http://127.0.0.1:8765"

POLL_SECONDS = 2

SHARED_PATH_TIMEOUT_SECONDS = 120
HTTP_TIMEOUT_SECONDS = 60
MONITOR_WAIT_SECONDS = 300




# ---------------------------------------------------------------------------
# Time and logging
# ---------------------------------------------------------------------------


def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"


def monotonic_time():
    if hasattr(time, "monotonic"):
        return time.monotonic()

    return time.time() 


def log(message):
    time = now_iso()
    line = "[{0}] [collector] {1}".format(time, message)

    print(line)
    sys.stdout.flush()




# ---------------------------------------------------------------------------
# Filesystem and job configuration
# ---------------------------------------------------------------------------


def ensure_dir(path):
    if path and not os.path.isdir(path):
        os.makedirs(path)


def load_json(path):
    with open(path, "r") as file_obj:
        return json.load(file_obj)


def wait_shared_path():
    deadline = monotonic_time() + SHARED_PATH_TIMEOUT_SECONDS

    while monotonic_time() < deadline:
        if os.path.isdir(SHARED_PATH):
            return
        
        log("waiting for shared path: {0}".format(SHARED_PATH))
        time.sleep(2)

    raise RuntimeError("shared path not found after {0}s: {1}".format(
        SHARED_PATH_TIMEOUT_SECONDS,
        SHARED_PATH,
    ))


def sample_config(job):
    sample = job.get("sample")

    if isinstance(sample, dict):
        return sample
    
    return {}


def monitor_config():
    return {
        "base_url": MONITOR_URL.rstrip("/"),
        "timeout": HTTP_TIMEOUT_SECONDS,
    }


def find_sample_file(job_dir, job):
    filename = sample_config(job).get("filename")
    
    if filename:
        path = os.path.join(job_dir, filename)
        if os.path.isfile(path):
            return path

    for name in os.listdir(job_dir):
        path = os.path.join(job_dir, name)
        if not os.path.isfile(path):
            continue

        lower_name = name.lower()
        if lower_name == JOB_FILENAME or lower_name.endswith(".json"):
            continue

        return path

    raise RuntimeError("no sample file found in {0}".format(job_dir))


def copy_sample_as_exe(sample_path):
    ensure_dir(WORKING_PATH)

    sample_name = os.path.basename(sample_path)
    base, _ext = os.path.splitext(sample_name)

    if not base:
        base = sample_name

    target = os.path.join(WORKING_PATH, base + ".exe")
    shutil.copy2(sample_path, target)

    return target




# ---------------------------------------------------------------------------
# Monitor API
# ---------------------------------------------------------------------------


def http_json(monitor, method, path, payload=None):
    url = monitor["base_url"] + path
    body = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib_request.Request(
        url, 
        data=body, 
        headers=headers
    )

    if method != "POST":
        try:
            request.get_method = lambda: method
        except Exception:
            pass

    response = urllib_request.urlopen(
        request, 
        timeout=monitor["timeout"]
    )

    try:
        raw = response.read()
    finally:
        response.close()

    if not raw:
        return {}
    
    return json.loads(raw.decode("utf-8"))


def wait_monitor_health(monitor):
    deadline = monotonic_time() + monitor["timeout"]
    last_error = None

    while monotonic_time() < deadline:
        try:
            result = http_json(monitor, "GET", "/health")
            if result.get("status") == "ok":
                return
        except Exception as exc:
            last_error = exc

        time.sleep(1)

    raise RuntimeError("monitor is not healthy: {0}".format(last_error))


def wait_monitor_completed(monitor, timeout):
    deadline = monotonic_time() + timeout
    last_status = None

    while monotonic_time() < deadline:
        status = http_json(monitor, "GET", "/status")
        current = status.get("status")

        if current != last_status:
            log("monitor status: {0}".format(status))
            last_status = current

        if current == "completed":
            return status
        
        if current == "failed":
            raise RuntimeError("monitor failed: {0}".format(status))
        
        time.sleep(2)

    raise RuntimeError("monitor did not complete before timeout")




# ---------------------------------------------------------------------------
# Sample execution
# ---------------------------------------------------------------------------


def start_sample(sample_path):
    log("starting sample: {0}".format(sample_path))

    process = subprocess.Popen([sample_path], cwd=WORKING_PATH, shell=False)

    log("sample started pid={0}".format(process.pid))

    return process




# ---------------------------------------------------------------------------
# Job processing
# ---------------------------------------------------------------------------


def process_job(job_path):
    job = load_json(job_path)
    job_dir = os.path.dirname(job_path)

    sample_path = find_sample_file(job_dir, job)
    local_sample = copy_sample_as_exe(sample_path)

    monitor = monitor_config()

    log("processing job: {0}".format(job_path))
    log("using monitor: {0}".format(monitor["base_url"]))
    wait_monitor_health(monitor)

    prepare = http_json(monitor, "POST", "/prepare", {"job_path": job_path})
    log("monitor prepared: {0}".format(prepare))

    if prepare.get("status") != "ready":
        raise RuntimeError("monitor did not become ready: {0}".format(prepare))

    sample_process = start_sample(local_sample)
    log("sample left running pid={0}".format(sample_process.pid))

    started = http_json(monitor, "POST", "/start", {})
    log("monitor started collection: {0}".format(started))

    status = wait_monitor_completed(monitor, MONITOR_WAIT_SECONDS)
    log("job completed: {0}".format(status))




# ---------------------------------------------------------------------------
# Job watcher
# ---------------------------------------------------------------------------


def job_key(path):
    try:
        stat = os.stat(path)
        return "{0}|{1}".format(path, stat.st_mtime)
    except Exception:
        return path


def watch():
    wait_shared_path()
    ensure_dir(WORKING_PATH)

    log("AIM Windows collector watching {0}".format(SHARED_PATH))
    processed = {}

    while True:
        job_path = os.path.join(SHARED_PATH, JOB_FILENAME)

        if os.path.isfile(job_path):
            key = job_key(job_path)

            if key not in processed:
                processed[key] = True
                
                try:
                    process_job(job_path)
                except Exception as exc:
                    log("job failed: {0}".format(exc))
                    log(traceback.format_exc())

        time.sleep(POLL_SECONDS)




# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main(_argv):
    watch()


if __name__ == "__main__":
    main(sys.argv[1:])
