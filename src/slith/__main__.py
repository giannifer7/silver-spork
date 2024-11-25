from pathlib import Path
from typing import Iterator

from slith.config import Config
from slith.solc_select import SolcSelector
from slith.parse_good import contracts_that_parse
from slith.slither import slither_one_sol
from slith.mythril import mythril_one_sol


def check_contracts(
    config: Config, solc_sel: SolcSelector, contracts: Iterator[Path], limit: int = -1
) -> None:
    for index, sol_path in enumerate(contracts):
        if index < 1:
            continue
        if 0 <= limit <= index:
            break
        sol_text = sol_path.read_text()
        # slither_one_sol(config, solc_sel, index, sol_path, sol_text)
        mythril_one_sol(config, solc_sel, index, sol_path, sol_text)
        del sol_text


def run(config: Config) -> None:
    solc_sel = SolcSelector()
    check_contracts(config, solc_sel, contracts_that_parse(config), limit=-1)


def main() -> None:
    config = Config()
    run(config)
