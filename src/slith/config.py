from pathlib import Path
from dataclasses import dataclass
from typing import Iterator

# from slith.solc_select import available_solidity_versions as avail_solidity_versions
# from slith.util import VerTuple


@dataclass
class Config:
    data_dir = Path("../data")
    patched_contracts_old: Path
    contracts_meta: Path
    results_base_dir: Path
    contracts_ok: Path
    contracts_fail: Path
    contracts_errors: Path
    # available_solidity_versions: list[VerTuple]
    # default_solidity_version: VerTuple
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
        # self.available_solidity_versions = avail_solidity_versions()
        # self.available_solidity_versions = avail_solidity_versions()
        # self.default_solidity_version = avail_solidity_versions()[-1]
        # self.default_solidity_version = self.available_solidity_versions[-1]
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
