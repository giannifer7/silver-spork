from pathlib import Path
from typing import Iterator

from slith.config import Config, subrun
from slith.pragma_solidity import (
    Version,
    RichVersion,
    version_from_pragma,
    solc_use,
)
from slith.parse_good import contracts_that_parse


def slither_one_sol(
    config: Config,
    index: int,
    sol_path: Path,
    sol_text: str,
    found_version: Version | None,
    version: Version,
) -> None:
    run_result = subrun(["slither", str(sol_path)])
    ret_code = run_result.returncode
    match ret_code:
        case 255:
            out_dir = config.results_255
            slither_dir = config.slither_results_255
        case 1:
            out_dir = config.results_1
            slither_dir = config.slither_results_1
        case _:
            out_dir = config.results_other
            slither_dir = config.slither_results_other
    print(f"{index:05d} {sol_path.name}: {ret_code}")
    slither_block = (
        "slither:\n"
        f"  index: {index:05d}\n"
        f'  sol: "{sol_path.name}"\n'
        f'  found_version: {found_version}\n'
        f'  checked_version: {version}\n'
        f"  ret_code: {ret_code}\n"
        f"{'=' * 3}\n\n"
        f"{run_result.stderr}"
    )
    with open(out_dir / sol_path.name, "w") as out_file:
        out_file.write("/*\n")
        out_file.write(slither_block)
        out_file.write("*/\n\n")
        out_file.write(sol_text)
        out_file.write("\n")
    with open(slither_dir / sol_path.with_suffix(".txt").name, "w") as slither_file:
        slither_file.write(slither_block)


def check_contracts(config: Config, contracts: Iterator[Path], limit=-1) -> None:
    prev_ver: Version = "0.4.26"
    solc_use(prev_ver)
    for index, sol_path in enumerate(contracts):
        if 0 <= limit <= index:
            break
        sol_text = sol_path.read_text()
        rich_ver: RichVersion = version_from_pragma(config, sol_text)
        version_to_use = rich_ver.version_to_use(config)
        if version_to_use != prev_ver:
            solc_use(version_to_use)
            prev_ver = version_to_use
        slither_one_sol(
            config, index, sol_path, sol_text, rich_ver.found_version, version_to_use
        )
        del sol_text


def run(config: Config) -> None:
    # check_contracts(config, contracts_that_parse(config), limit=-1)
    check_contracts(config, config.contracts_glob(), limit=-1)


def main() -> None:
    config = Config()
    run(config)
