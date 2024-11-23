from pathlib import Path
from dataclasses import dataclass
from typing import Iterator
from subprocess import run, CompletedProcess
from functools import cache

type FileName = str
type VerTuple = tuple[int, int, int]


class SolcSelectVersionsError(RuntimeError):
    pass


def subrun(cmd: list[str]) -> CompletedProcess[str]:
    return run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


@cache
def _available_solidity_versions() -> list[VerTuple]:
    run_result = subrun(["solc-select", "versions"])
    if run_result.returncode:
        raise SolcSelectVersionsError(
            "solc-select versions failed: {run_result.returncode}"
        )

    def ver_tuple(line: str) -> VerTuple:
        major, minor, patch = line.split(".", maxsplit=2)
        return (
            int(major),
            int(minor),
            int(patch if not "(" in patch else patch.split()[0]),
        )

    versions_list = [ver_tuple(line) for line in run_result.stdout.splitlines()]
    versions_list.sort()
    return versions_list


@dataclass
class Config:
    data_dir = Path("../data")
    patched_contracts_old: Path
    contracts_meta: Path
    results_base_dir: Path
    contracts_ok: Path
    contracts_fail: Path
    contracts_errors: Path
    available_solidity_versions: list[VerTuple]
    default_solidity_version: VerTuple
    results_255: Path
    results_1: Path
    results_other: Path
    slither_results_base_dir: Path
    slither_results_255: Path
    slither_results_1: Path
    slither_results_other: Path

    def __init__(self) -> None:
        self.patched_contracts_old = self.data_dir / "patched_contracts_old"
        self.contracts_meta = self.data_dir / "meta"
        self.results_base_dir = self.data_dir / "results"
        self.contracts_ok = self.contracts_meta / "contracts_parse_ok.txt"
        self.contracts_fail = self.contracts_meta / "contracts_parse_fail.txt"
        self.contracts_errors = self.contracts_meta / "errors"
        self.available_solidity_versions = _available_solidity_versions()
        self.default_solidity_version = _available_solidity_versions()[-1]
        self.results_255 = self.results_base_dir / "ret_255"
        self.results_1 = self.results_base_dir / "ret_1"
        self.results_other = self.results_base_dir / "ret_other"
        self.slither_results_base_dir = self.results_base_dir / "slither_results"
        self.slither_results_255 = self.slither_results_base_dir / "ret_255"
        self.slither_results_1 = self.slither_results_base_dir / "ret_1"
        self.slither_results_other = self.slither_results_base_dir / "ret_other"

        def mkd(f: Path) -> None:
            f.mkdir(parents=True, exist_ok=True)

        mkd(self.contracts_meta)
        mkd(self.contracts_errors)
        mkd(self.results_255)
        mkd(self.results_1)
        mkd(self.results_other)
        mkd(self.contracts_errors)
        mkd(self.slither_results_255)
        mkd(self.slither_results_1)
        mkd(self.slither_results_other)

    def contracts_glob(self) -> Iterator[Path]:
        return self.patched_contracts_old.glob("*.sol")
