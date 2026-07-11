from typing import Any

EXECUTABLE = "procmon.exe"
START_ARGUMENTS = [
    "/AcceptEula",
    "/Quiet",
    "/BackingFile",
    "procmon.pml",
]
STOP_ARGUMENTS = [
    "/Terminate",
]
SAVE_ARGUMENTS = [
    "/AcceptEula",
    "/Quiet",
    "/OpenLog",
    "{pml}",
    "/SaveAs",
    "{csv}",
]
BACKING_FILE = "procmon.pml"
CSV_FILE = "procmon.csv"


def build_procmon_job(
    enabled: bool,
    timeout: int,
    collect_interval_seconds: int = 60,
    filter_config: str | None = None,
) -> dict[str, Any]:
    if filter_config:
        START_ARGUMENTS.extend(
            [
                "/LoadConfig",
                "{filter_config}",
            ]
        )

        SAVE_ARGUMENTS.extend(
            [
                "/SaveApplyFilter"
            ]
        )

    parameters = {
        "executable": EXECUTABLE,
        "start_arguments": START_ARGUMENTS,
        "stop_arguments": [
            "/Terminate",
        ],
        "save_arguments": SAVE_ARGUMENTS,
        "backing_file": BACKING_FILE,
        "csv_file": CSV_FILE,
        "stop_wait_seconds": 30,
        "save_wait_seconds": 30,
        "timeout": timeout,
        "collect_interval_seconds": collect_interval_seconds,
    }
    
    if filter_config:
        parameters["filter_config"] = filter_config

    return {
        "enabled": enabled,
        "parameters": parameters,
    }
