from pathlib import Path
from typing import Iterator

from slith.util import subrun, Version
from slith.config import Config
from slith.solc_select import SolcSelector
from slith.pragma_solidity import (
    RichVersion,
    version_from_pragma,
)
from slith.parse_good import contracts_that_parse


def front_matter(
    index: int,
    sol_path: Path,
    found_version: Version | None,
    version: Version,
    ret_code: int,
) -> str:
    return (
        "slither:\n"
        f"  index: {index}\n"
        f'  sol: "{sol_path.name}"\n'
        f'  found_version: {found_version}\n'
        f'  checked_version: {version}\n'
        f"  ret_code: {ret_code}\n"
        f"{'=' * 3}\n\n"
    )


def dirs_from_ret_code(config: Config, ret_code: int) -> tuple[Path, Path]:
    match ret_code:
        case 255:
            return config.results_255, config.slither_results_255
        case 1:
            return config.results_1, config.slither_results_1
        case _:
            return config.results_other, config.slither_results_other


def out_text(slither_block: str, sol_text: str) -> str:
    return f"/*\n{slither_block}*/\n\n{sol_text}\n"


def write_out_file(
    out_dir: Path, sol_path: Path, slither_block: str, sol_text: str
) -> None:
    (out_dir / sol_path.name).write_text(out_text(slither_block, sol_text))


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
    print(f"{index:05d} {sol_path.name}: {ret_code}")
    slither_block = (
        f"{front_matter(index, sol_path, found_version, version, ret_code)}"
        f"{run_result.stderr}"
    )
    out_dir, slither_dir = dirs_from_ret_code(config, ret_code)
    (out_dir / sol_path.name).write_text(out_text(slither_block, sol_text))
    (slither_dir / sol_path.with_suffix(".txt").name).write_text(slither_block)


def check_contracts(
    config: Config, solc_sel: SolcSelector, contracts: Iterator[Path], limit: int = -1
) -> None:
    for index, sol_path in enumerate(contracts):
        if 0 <= limit <= index:
            break
        sol_text = sol_path.read_text()
        rich_ver: RichVersion = version_from_pragma(solc_sel, sol_text)
        version_to_use = rich_ver.version_to_use(solc_sel)
        solc_sel.solc_use(version_to_use)
        slither_one_sol(
            config, index, sol_path, sol_text, rich_ver.found_version, version_to_use
        )
        del sol_text


def run(config: Config) -> None:
    solc_sel = SolcSelector()
    check_contracts(config, solc_sel, contracts_that_parse(config), limit=-1)
    # check_contracts(config, config.contracts_glob(), limit=-1)


def main() -> None:
    config = Config()
    run(config)
