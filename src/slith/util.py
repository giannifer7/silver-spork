import subprocess
from subprocess import run, CompletedProcess
from typing import NamedTuple
import time


from typing import TypeAlias

FileName: TypeAlias = str
Version: TypeAlias = str
VerTuple: TypeAlias = tuple[int, int, int]

# type FileName = str
# type Version = str
# type VerTuple = tuple[int, int, int]


def subrun(cmd: list[str]) -> CompletedProcess[str]:
    return run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


class ProcessResult(NamedTuple):
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool


def run_with_timeout(
    cmd: list[str], env: dict[str, str] = None, timeout_sec: float = 60.0
) -> ProcessResult:
    """
    Run a command with timeout, capturing stdout and stderr.

    Args:
        cmd: List of command arguments
        timeout_sec: Timeout in seconds

    Returns:
        ProcessResult containing return code, stdout, stderr and timeout status
    """
    try:
        # Start process with pipe for stdout/stderr
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,  # Return strings instead of bytes
        )

        # Wait for process with timeout
        stdout, stderr = process.communicate(timeout=timeout_sec)

        return ProcessResult(
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
            timed_out=False,
        )

    except subprocess.TimeoutExpired:
        # Kill process if timeout occurred
        process.kill()
        # Collect any output before killing
        stdout, stderr = process.communicate()

        return ProcessResult(
            returncode=-1,  # Use -1 to indicate timeout
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
        )


def ver_tuple(ver: Version) -> VerTuple:
    major, minor, patch = ver.split(".", maxsplit=2)
    return (
        int(major),
        int(minor),
        int(patch),
    )


def ver_from_tuple(ver: VerTuple) -> Version:
    major, minor, patch = ver
    return f"{major}.{minor}.{patch}"
