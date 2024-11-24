from subprocess import run, CompletedProcess

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
