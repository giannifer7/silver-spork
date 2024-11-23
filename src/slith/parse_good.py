import sys
from pathlib import Path
from typing import Iterator, Any
import io
import traceback
from types import TracebackType
from solidity_parser import parser  # type: ignore
from slith.config import Config, FileName


class ErrRedirect:
    def __init__(self, config: Config, filename: FileName) -> None:
        self.config: Config = config
        self.filename: FileName = filename or "unnamed"
        self.path: Path = (self.config.contracts_errors / self.filename).with_suffix(
            ".txt"
        )
        self.occurred: bool = False
        self.out: io.StringIO | None = None
        self.prev_stderr: Any | None = None

    def __enter__(self) -> "ErrRedirect":
        self.out = io.StringIO()
        self.prev_stderr = sys.stderr
        sys.stderr = self.out
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        sys.stderr = self.prev_stderr

        if self.out is None:
            return

        stderr_output = self.out.getvalue()
        self.out.close()
        self.out = None

        if not stderr_output and exc_type is None:
            return

        self._handle_error(stderr_output, exc_type, exc_value, exc_tb)

    def _handle_error(
        self,
        stderr_output: str,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.occurred = True
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            f.write(f"{self.filename}\n")
            if stderr_output:
                f.write(stderr_output)
            if exc_type:
                traceback.print_exception(exc_type, exc_value, exc_tb, file=f)


def check_contracts_parse(
    config: Config, contracts: Iterator[Path], limit: int = -1
) -> None:
    ok_list: list[str] = []
    fail_list: list[str] = []

    for index, sol_path in enumerate(contracts):
        if 0 <= limit <= index:
            break

        with ErrRedirect(config, sol_path.name):
            try:
                parser.parse_file(sol_path, loc=False)
                ok_list.append(sol_path.name)
                print(f"{sol_path.name}: Ok")
            except Exception:
                fail_list.append(sol_path.name)
                print(f"{sol_path.name}: Fail")

    _write_results(config.contracts_ok, ok_list)
    _write_results(config.contracts_fail, fail_list)


def _write_results(file_path: Path, results: list[str]) -> None:
    with open(file_path, "w") as f:
        f.write("\n".join(results))
        f.write("\n")


def names_of_contracts_that_parse(config: Config, limit: int = -1) -> set[FileName]:
    if not config.contracts_ok.exists():
        check_contracts_parse(config, config.contracts_glob(), limit)
    return _read_results(config.contracts_ok)


def contracts_that_parse(config: Config) -> Iterator[Path]:
    parsed_names = names_of_contracts_that_parse(config)
    return (sol for sol in config.contracts_glob() if sol.name in parsed_names)


def names_of_contracts_that_dont_parse(
    config: Config, limit: int = -1
) -> set[FileName]:
    if not config.contracts_fail.exists():
        check_contracts_parse(config, config.contracts_glob(), limit)
    return _read_results(config.contracts_fail)


def contracts_that_dont_parse(config: Config) -> Iterator[Path]:
    non_parsed_names = names_of_contracts_that_dont_parse(config)
    return (sol for sol in config.contracts_glob() if sol.name in non_parsed_names)


def _read_results(file_path: Path) -> set[FileName]:
    if not file_path.exists():
        return set()
    return {line.strip() for line in file_path.read_text().splitlines() if line}
