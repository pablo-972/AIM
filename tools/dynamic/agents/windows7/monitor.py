from __future__ import print_function

import datetime
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import traceback

try:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    from urllib import request as urllib_request
    from urllib import parse as urllib_parse
except ImportError:
    import urllib2 as urllib_request
    import urllib as urllib_parse




HOST = "127.0.0.1"
PORT = 8765

WORKING_PATH = r"C:\AIM"

STATE_LOCK = threading.Lock()
STATE = {
    "status": "idle",
    "job_path": None,
    "error": None,
    "started_at": None,
    "completed_at": None,
}

JOB = None
RECEIVER = None
SHA256_VALUE = None
PROCMON_STATE = None




# ---------------------------------------------------------------------------
# Compatibility
# ---------------------------------------------------------------------------


try:
    text_type = unicode
except NameError:
    text_type = str




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
# Monitor state
# ---------------------------------------------------------------------------


def set_state(status=None, error=None, extra=None):
    with STATE_LOCK:
        if status is not None:
            STATE["status"] = status
        if error is not None:
            STATE["error"] = error
        if extra:
            STATE.update(extra)


def snapshot_state():
    with STATE_LOCK:
        return dict(STATE)




# ---------------------------------------------------------------------------
# Filesystem and values
# ---------------------------------------------------------------------------


def ensure_dir(path):
    if path and not os.path.isdir(path):
        os.makedirs(path)


def load_json(path):
    with open(path, "r") as file_obj:
        return json.load(file_obj)


def read_bytes(path):
    with open(path, "rb") as file_obj:
        return file_obj.read()


def replace_extension(filename, extension):
    base, _old_extension = os.path.splitext(filename)
    return base + extension


def required_int(value, name):
    try:
        value = int(value)
    except Exception:
        raise RuntimeError("missing or invalid integer: {0}".format(name))
    
    if value < 1:
        raise RuntimeError("invalid integer below 1: {0}".format(name))
    
    return value




# ---------------------------------------------------------------------------
# Job configuration
# ---------------------------------------------------------------------------


def sample_config(job):
    sample = job.get("sample")
    
    if isinstance(sample, dict):
        return sample
    
    return {}


def receiver_config(job):
    receiver = job.get("receiver")
    if not isinstance(receiver, dict):
        receiver = {}

    timeout = int(receiver.get("timeout"))
    receiver_url = str(receiver.get("base_url"))

    return {
        "base_url": receiver_url.rstrip("/"),
        "timeout": timeout,
    }


def sha256_from_job(job):
    sample = sample_config(job)
    sha256 = sample.get("sha256")

    if sha256:
        return str(sha256)
    
    filename = sample.get("filename")
    if filename:
        return str(filename)
    
    return "unknown"


def enabled_tool_config(job, tool_name):
    tools = job.get("tools")
    if not isinstance(tools, dict):
        return None

    for name, config in tools.items():
        enabled = config.get("enabled")

        if enabled:
            if str(name) == tool_name:
                return config
        
    return None


def tool_parameters(tool_config):
    if not isinstance(tool_config, dict):
        return {}
    
    params = tool_config.get("parameters")
    if isinstance(params, dict):
        return params
    
    return {}


def collect_interval(job):
    tools = job.get("tools")
    if not isinstance(tools, dict):
        raise RuntimeError("job missing tools")

    maximum = None
    for name, config in tools.items():
        enabled = config.get("enabled")
        if not enabled:
            continue

        params = tool_parameters(config)
        interval = required_int(
            params.get("collect_interval_seconds"),
            "tools.{0}.parameters.collect_interval_seconds".format(name),
        )

        maximum = interval

    if maximum is None:
        raise RuntimeError("job has no enabled tools")
    
    return maximum




# ---------------------------------------------------------------------------
# Artifact upload
# ---------------------------------------------------------------------------


def post_artifact(
    receiver, 
    sha256_value, 
    tool_name, 
    artifact_name, 
    raw_content,
):
    base_url = str(receiver.get("base_url")).rstrip("/")
    if not base_url:
        raise RuntimeError("missing receiver base_url")

    if raw_content is None:
        raw_content = b""

    if isinstance(raw_content, text_type):
        raw_content = raw_content.encode("utf-8")

    sanitized_artifact_name = str(artifact_name).replace("\\", "/")
    quoted_name = urllib_parse.quote(sanitized_artifact_name, safe="")
    path = "/jobs/{0}/tools/{1}/artifacts/{2}".format(
        sha256_value,
        tool_name,
        quoted_name,
    )

    request = urllib_request.Request(
        base_url + path,
        data=raw_content,
        headers={
            "Content-Type": "application/octet-stream",
        },
    )

    last_error = None
    log("posting artifact tool={0} name={1} bytes={2}".format(
        tool_name,
        artifact_name,
        len(raw_content),
    ))

    for attempt in range(3):
        try:
            timeout = receiver.get("timeout")
            response = urllib_request.urlopen(
                request, 
                timeout=timeout,
            )

            try:
                response.read()
            finally:
                response.close()

            log("posted artifact tool={0} name={1}".format(
                tool_name, 
                artifact_name,
            ))

            return
        except Exception as exc:
            last_error = exc
            log("post failed attempt={0} tool={1} name={2}: {3}".format(
                attempt + 1,
                tool_name,
                artifact_name,
                exc,
            ))

            time.sleep(1)

    raise RuntimeError("failed to post artifact {0}/{1}: {2}".format(
        tool_name,
        artifact_name,
        last_error,
    ))




# ---------------------------------------------------------------------------
# Command execution
# ---------------------------------------------------------------------------


def run_command_capture(command, cwd, timeout):
    log("running command timeout={0}: {1}".format(
        timeout, 
        " ".join(command),
    ))

    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=False,
    )

    raw_output, timed_out = communicate_with_timeout(process, timeout)
    log("command finished returncode={0} timed_out={1} bytes={2}".format(
        process.returncode,
        timed_out,
        len(raw_output or b""),
    ))

    return raw_output


def communicate_with_timeout(process, timeout):
    output = []
    errors = []
    result = None

    def target():
        try:
            raw_output, _unused = process.communicate()
            output.append(raw_output)
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        try:
            process.kill()
        except Exception:
            pass

        thread.join(5)
        if output:
            result = output[0]

        return result, True

    if errors:
        raise errors[0]
    
    if output:
        result = output[0]
    
    return result, False




# ---------------------------------------------------------------------------
# Autoruns collection
# ---------------------------------------------------------------------------


def autoruns_command(params):
    executable = params.get("executable")
    arguments = params.get("arguments")
    
    command = [str(executable)]
    for argument in arguments:
        command.append(str(argument))

    return command


def capture_autoruns(job, receiver, sha256_value, phase):
    tool_config = enabled_tool_config(job, "autoruns")
    if tool_config is None:
        return

    params = tool_parameters(tool_config)
    timeout = params.get("timeout")
    command = autoruns_command(params)

    raw_output = run_command_capture(command, WORKING_PATH, timeout)
    post_artifact(
        receiver, 
        sha256_value, 
        "autoruns", 
        phase + ".csv", 
        raw_output
    )




# ---------------------------------------------------------------------------
# Registry collection
# ---------------------------------------------------------------------------


def registry_keys(params):
    keys = params.get("registry_keys")
    if isinstance(keys, list) and keys:
        return [str(key) for key in keys]
    
    raise RuntimeError("registry tool missing registry_keys")


def safe_filename(value):
    safe = []
    for char in value:
        if char.isalnum():
            safe.append(char)
        else:
            safe.append("_")
    
    return "".join(safe).strip("_") or "item"


def capture_registry(job, receiver, sha256_value, phase):
    tool_config = enabled_tool_config(job, "registry")
    if tool_config is None:
        return

    params = tool_parameters(tool_config)
    executable = params.get("executable")
    timeout = params.get("timeout")

    temp_dir = os.path.join(tempfile.gettempdir(), "aim_registry")
    ensure_dir(temp_dir)

    for key in registry_keys(params):
        filename = safe_filename(key) + ".reg"
        reg_path = os.path.join(temp_dir, phase + "_" + filename)

        command = [str(executable), "export", key, reg_path, "/y"]
        run_command_capture(command, WORKING_PATH, timeout)

        artifact_name = phase + "/" + filename
        if os.path.exists(reg_path):
            try:
                post_artifact(
                    receiver, 
                    sha256_value, 
                    "registry", 
                    artifact_name, 
                    read_bytes(reg_path),
                )
            finally:
                try:
                    os.remove(reg_path)
                except Exception:
                    pass
        else:
            log("registry export missing file phase={0} key={1} path={2}".format(
                phase,
                key,
                reg_path,
            ))




# ---------------------------------------------------------------------------
# Procmon collection
# ---------------------------------------------------------------------------


def procmon_executable(params):
    return str(params.get("executable"))


def procmon_csv_name(params, pml_name):
    csv_name = str(params.get("csv_file"))

    return csv_name or replace_extension(pml_name, ".csv")


def wait_for_stable_file(path, timeout):
    deadline = monotonic_time() + timeout
    last_size = -1
    stable_reads = 0

    while monotonic_time() < deadline:
        if os.path.exists(path):
            try:
                current_size = os.path.getsize(path)
            except Exception:
                current_size = -1

            if current_size > 0 and current_size == last_size:
                stable_reads += 1

                if stable_reads >= 2:
                    return True
            else:
                stable_reads = 0
                last_size = current_size

        time.sleep(1)

    return os.path.exists(path)


def resolve_optional_file(path_value, job_path):
    if not path_value:
        return None

    candidates = []
    path_value = str(path_value)

    if os.path.isabs(path_value):
        candidates.append(path_value)
    else:
        if job_path:
            candidates.append(os.path.join(
                os.path.dirname(job_path), 
                path_value,
            ))

        candidates.append(os.path.join(WORKING_PATH, path_value))

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    log("optional file not found: {0}".format(path_value))
    return None


def resolve_procmon_arguments(
    arguments, 
    pml_name, 
    pml_path, 
    csv_path, 
    filter_config_path,
):
    resolved = []
    index = 0

    while index < len(arguments):
        argument = str(arguments[index])
        lower_argument = argument.lower()

        if lower_argument == "/loadconfig":
            next_argument = ""
            if index + 1 < len(arguments):
                next_argument = str(arguments[index + 1]) 

            if next_argument == "{filter_config_path}" and not filter_config_path:
                index += 2
                continue

        if argument == "{filter_config_path}" and not filter_config_path:
            index += 1
            continue

        argument = argument.replace("{pml_path}", pml_path)
        argument = argument.replace("{csv_path}", csv_path)
        argument = argument.replace("{filter_config_path}", filter_config_path or "")

        if argument == pml_name:
            argument = pml_path

        resolved.append(argument)
        index += 1

    return resolved


def procmon_save_arguments(params, pml_path, csv_path, filter_config_path):
    arguments = params.get("save_arguments")
    if not isinstance(arguments, list):
        resolved = [
            "/AcceptEula", 
            "/Quiet", 
            "/OpenLog", 
            pml_path, 
            "/SaveAs", 
            csv_path,
        ]

        if filter_config_path:
            resolved.append("/SaveApplyFilter")

        return resolved

    procmon_arguments = resolve_procmon_arguments(
        arguments, 
        None, 
        pml_path, 
        csv_path, 
        filter_config_path,
    )
    return procmon_arguments


def save_procmon_csv(params, pml_path, csv_path, filter_config_path):
    executable = [procmon_executable(params)]
    arguments = procmon_save_arguments(params, pml_path, csv_path, filter_config_path)

    command = executable + arguments
    timeout = params.get("timeout")
    log("saving procmon csv: {0}".format(" ".join(command)))
    
    run_command_capture(
        command,
        WORKING_PATH,
        timeout,
    )

    save_wait_seconds = params.get("save_wait_seconds")
    wait_for_stable_file(csv_path, save_wait_seconds)


def start_procmon(job, job_path):
    tool_config = enabled_tool_config(job, "procmon")
    if tool_config is None:
        return None

    params = tool_parameters(tool_config)

    pml_name = str(params.get("backing_file"))
    pml_path = os.path.join(
        tempfile.gettempdir(), 
        "aim_procmon_{0}.pml".format(os.getpid()),
    )

    csv_name = procmon_csv_name(params, pml_name)
    csv_path = os.path.join(
        tempfile.gettempdir(), 
        "aim_procmon_{0}.csv".format(os.getpid()),
    )

    filter_config = params.get("filter_config")
    filter_config_path = resolve_optional_file(filter_config, job_path)

    arguments = params.get("start_arguments")
    if not isinstance(arguments, list):
        arguments = ["/AcceptEula", "/Quiet"]

        if filter_config_path:
            arguments.extend(["/LoadConfig", filter_config_path])

        arguments.extend(["/BackingFile", pml_path])
    else:
        arguments = resolve_procmon_arguments(
            arguments, 
            pml_name, 
            pml_path, 
            csv_path, 
            filter_config_path,
        )

    command = [procmon_executable(params)]
    for argument in arguments:
        command.append(str(argument))

    log("starting procmon: {0}".format(" ".join(command)))

    with open(os.devnull, "wb") as stdout_file:
        process = subprocess.Popen(
            command,
            cwd=WORKING_PATH,
            stdout=stdout_file,
            stderr=subprocess.STDOUT,
            shell=False,
        )

    log("procmon launcher pid={0} pml={1}".format(process.pid, pml_path))

    return {
        "params": params,
        "pml_name": pml_name,
        "pml_path": pml_path,
        "csv_name": csv_name,
        "csv_path": csv_path,
        "filter_config_path": filter_config_path,
    }


def stop_procmon(procmon_state, receiver, sha256_value):
    if procmon_state is None:
        return

    params = procmon_state["params"]
    arguments = params.get("stop_arguments")

    if not isinstance(arguments, list):
        arguments = ["/Terminate"]

    command = [procmon_executable(params)]
    for argument in arguments:
        command.append(str(argument)) 
    
    timeout = params.get("timeout")
    run_command_capture(
        command,
        WORKING_PATH,
        timeout
    )

    pml_path = procmon_state["pml_path"]
    csv_path = procmon_state["csv_path"]

    stop_wait_seconds = params.get("stop_wait_seconds")
    waited = wait_for_stable_file(pml_path, stop_wait_seconds)
    if not waited:
        raise RuntimeError("procmon pml missing: {0}".format(pml_path))

    try:
        log("procmon pml exists bytes={0}".format(os.path.getsize(pml_path)))

        filter_config_path = procmon_state.get("filter_config_path")
        save_procmon_csv(params, pml_path, csv_path, filter_config_path)

        if os.path.exists(csv_path):
            log("procmon csv exists bytes={0}".format(os.path.getsize(csv_path)))

            post_artifact(
                receiver, 
                sha256_value, 
                "procmon", 
                procmon_state["csv_name"], 
                read_bytes(csv_path)
            )
        else:
            log("procmon csv missing after save: {0}".format(csv_path))
    finally:
        for path in [csv_path, pml_path]:
            try:
                os.remove(path)
            except Exception:
                pass




# ---------------------------------------------------------------------------
# Collection lifecycle
# ---------------------------------------------------------------------------


def sleep_collect_interval(seconds):
    deadline = monotonic_time() + seconds
    log("collection sleep start seconds={0}".format(seconds))

    while monotonic_time() < deadline:
        remaining = deadline - monotonic_time()
        time.sleep(max(0, remaining))

    log("collection sleep completed seconds={0}".format(seconds))


def prepare_monitor(job_path):
    global JOB, RECEIVER, SHA256_VALUE, PROCMON_STATE

    set_state(
        "preparing", 
        None, 
        {
            "job_path": job_path, 
            "started_at": now_iso(), 
            "completed_at": None,
        },
    )

    JOB = load_json(job_path)
    RECEIVER = receiver_config(JOB)
    SHA256_VALUE = sha256_from_job(JOB)
    PROCMON_STATE = None

    log("prepare job={0} sha256={1}".format(job_path, SHA256_VALUE))


    capture_autoruns(JOB, RECEIVER, SHA256_VALUE, "before_execution")
    capture_registry(JOB, RECEIVER, SHA256_VALUE, "before_execution")
    PROCMON_STATE = start_procmon(JOB, job_path)

    set_state("ready", None)

    return snapshot_state()


def collection_worker():
    global PROCMON_STATE

    try:
        set_state("collecting", None)

        interval = collect_interval(JOB)
        sleep_collect_interval(interval)

        stop_procmon(PROCMON_STATE, RECEIVER, SHA256_VALUE)
        PROCMON_STATE = None
        capture_autoruns(JOB, RECEIVER, SHA256_VALUE, "after_execution")
        capture_registry(JOB, RECEIVER, SHA256_VALUE, "after_execution")

        set_state(
            "completed", 
            None, 
            {
                "completed_at": now_iso(),
            },
        )
        log("collection completed")
    except Exception as exc:
        set_state(
            "failed", 
            str(exc), 
            {
                "completed_at": now_iso(),
            },
        )
        log("collection failed: {0}".format(exc))
        log(traceback.format_exc())


def start_collection():
    state = snapshot_state()
    if state.get("status") != "ready":
        raise RuntimeError("monitor is not ready: {0}".format(state))

    thread = threading.Thread(target=collection_worker)
    thread.daemon = True

    thread.start()

    return snapshot_state()




# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

class MonitorHandler(BaseHTTPRequestHandler):
    def log_message(self, _format, *args):
        return

    def do_GET(self):
        if self.path == "/health":
            self.send_json(
                {
                    "status": "ok",
                },
            )
            return
        
        if self.path == "/status":
            self.send_json(snapshot_state())
            return
        
        self.send_json(
            {
                "error": "not found",
            }, 
            status=404
        )

    def do_POST(self):
        try:
            payload = self.read_json()

            if self.path == "/prepare":
                job_path = payload.get("job_path")

                if not job_path:
                    raise RuntimeError("missing job_path")
                
                self.send_json(prepare_monitor(str(job_path)))
                return
            
            if self.path == "/start":
                self.send_json(start_collection())
                return
            
            self.send_json({"error": "not found"}, status=404)
        except Exception as exc:
            set_state("failed", str(exc), {"completed_at": now_iso()})

            log("request failed {0}: {1}".format(self.path, exc))
            log(traceback.format_exc())

            self.send_json(
                {
                    "status": "failed", 
                    "error": str(exc),
                }, 
                status=500,
            )

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def send_json(self, data, status=200):
        raw = json.dumps(data, sort_keys=True).encode("utf-8")

        self.send_response(status)

        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()

        self.wfile.write(raw)




# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main(_argv):
    ensure_dir(WORKING_PATH)

    server = HTTPServer((HOST, PORT), MonitorHandler)

    log("AIM monitor listening on http://{0}:{1}".format(HOST, PORT))
    server.serve_forever()


if __name__ == "__main__":
    main(sys.argv[1:])
