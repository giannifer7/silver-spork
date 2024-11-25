import os
import sys
from pathlib import Path
from subprocess import CompletedProcess
# import io
# import traceback
# from types import TracebackType

# from mythril.interfaces.cli import main as mythril_main

from slith.util import FileName, Version, run_with_timeout, ProcessResult
from slith.config import Config
from slith.solc_select import SolcSelector
from slith.pragma_solidity import (
    RichVersion,
    version_from_pragma,
)


def subrun(cmd: list[str]) -> ProcessResult:
    # orig_path = os.environ.get("PATH")
    # VIRTUAL_ENV = "/home/g4/_prj/leo/silver/mythril01/yourthril"
    # PATH = f"{VIRTUAL_ENV}/bin:{orig_path}"
    # new_env = {
    #     "VIRTUAL_ENV": VIRTUAL_ENV,
    #     "PATH": PATH,
    # }
    return run_with_timeout(
        cmd,
        #    env=new_env,
        env=None,
        timeout_sec=120,
    )


def dirs_from_ret_code(config: Config, ret_code: int) -> tuple[Path, Path]:
    match ret_code:
        case 255:
            return config.results_255, config.mythril_results_255
        case 1:
            return config.results_1, config.mythril_results_1
        case _:
            return config.results_other, config.mythril_results_other


def front_matter(
    index: int,
    sol_path: Path,
    found_version: Version | None,
    version: Version,
    ret_code: int,
) -> str:
    return (
        "mythril:\n"
        f"  index: {index}\n"
        f'  sol: "{sol_path.name}"\n'
        f'  found_version: {found_version}\n'
        f'  checked_version: {version}\n'
        f"  ret_code: {ret_code}\n"
        f"{'=' * 3}\n\n"
    )


def do_mythril_one_sol(
    config: Config,
    index: int,
    sol_path: Path,
    sol_text: str,
    found_version: Version | None,
    version: Version,
) -> None:
    run_result = subrun(["myth", "a", str(sol_path)])
    ret_code = run_result.returncode
    print(f"{index:05d} {sol_path.name}: {ret_code}")
    mythril_block = (
        f"{front_matter(index, sol_path, found_version, version, ret_code)}"
        f"{run_result.stderr}"
        f"{run_result.stdout}"
    )
    out_dir, mythril_dir = dirs_from_ret_code(config, ret_code)
    # (out_dir / sol_path.name).write_text(out_text(mythril_block, sol_text))
    (mythril_dir / sol_path.with_suffix(".txt").name).write_text(mythril_block)


def mythril_one_sol(
    config: Config,
    solc_sel: SolcSelector,
    index: int,
    sol_path: Path,
    sol_text: str,
) -> None:
    rich_ver: RichVersion = version_from_pragma(solc_sel, sol_text)
    version_to_use = rich_ver.version_to_use(solc_sel)
    solc_sel.solc_use(version_to_use)
    do_mythril_one_sol(
        config, index, sol_path, sol_text, rich_ver.found_version, version_to_use
    )
