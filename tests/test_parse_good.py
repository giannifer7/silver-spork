import pytest
from pathlib import Path
import sys
from unittest.mock import patch
from slith.parse_good import (
    ErrRedirect,
    check_contracts_parse,
    names_of_contracts_that_parse,
    contracts_that_parse,
    names_of_contracts_that_dont_parse,
    contracts_that_dont_parse,
    _write_results,
    _read_results,
)
from slith.config import Config


@pytest.fixture
def mock_config(tmp_path):
    """Fixture to create a mock configuration with temporary paths."""
    config = Config()
    config.contracts_errors = tmp_path / "errors"
    config.contracts_errors.mkdir(parents=True, exist_ok=True)
    config.contracts_ok = tmp_path / "ok.txt"
    config.contracts_fail = tmp_path / "fail.txt"
    config.contracts_glob = lambda: []
    return config


@pytest.fixture
def mock_contract_files(tmp_path):
    """Fixture to create mock contract files in a temporary directory."""
    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    return [contracts_dir / f"contract{i}.sol" for i in range(1, 4)]


def test_err_redirect_no_error(mock_config):
    """Test ErrRedirect when no error occurs."""
    with ErrRedirect(mock_config, "test.sol") as redirect:
        pass
    error_file = mock_config.contracts_errors / "test.txt"
    assert not error_file.exists()
    assert not redirect.occurred


def test_err_redirect_stderr_output(mock_config):
    """Test ErrRedirect captures standard error output."""
    error_message = "Captured stderr message"
    with ErrRedirect(mock_config, "test.sol") as redirect:
        print(error_message, file=sys.stderr)
    error_file = mock_config.contracts_errors / "test.txt"
    assert redirect.occurred
    assert error_file.exists()
    assert error_message in error_file.read_text()


def test_err_redirect_exception(mock_config):
    """Test ErrRedirect captures exceptions and their traceback."""
    with pytest.raises(ValueError):
        with ErrRedirect(mock_config, "test.sol") as redirect:
            raise ValueError("Example error")
    error_file = mock_config.contracts_errors / "test.txt"
    assert redirect.occurred
    assert error_file.exists()
    content = error_file.read_text()
    assert "ValueError: Example error" in content


def test_check_contracts_parse_empty(mock_config):
    """Test check_contracts_parse when no contracts are provided."""
    check_contracts_parse(mock_config, iter([]))
    assert mock_config.contracts_ok.exists()
    assert mock_config.contracts_fail.exists()
    assert mock_config.contracts_ok.read_text().strip() == ""
    assert mock_config.contracts_fail.read_text().strip() == ""


def test_check_contracts_parse_unexpected_exception(mock_config, mock_contract_files):
    """Test check_contracts_parse handles unexpected exceptions."""
    for file in mock_contract_files:
        file.touch()

    mock_config.contracts_glob = lambda: iter(mock_contract_files)
    with patch(
        "solidity_parser.parser.parse_file",
        side_effect=RuntimeError("Unexpected error"),
    ):
        check_contracts_parse(mock_config, mock_config.contracts_glob())

    fail_content = mock_config.contracts_fail.read_text()
    assert all(contract.name in fail_content for contract in mock_contract_files)


def test_write_results_empty(tmp_path):
    """Test _write_results with an empty list."""
    file_path = tmp_path / "results.txt"
    _write_results(file_path, [])
    assert file_path.exists()
    assert file_path.read_text() == "\n"


def test_write_results_large_list(tmp_path):
    """Test _write_results with a large list."""
    file_path = tmp_path / "results.txt"
    data = [f"contract{i}.sol" for i in range(100)]
    _write_results(file_path, data)
    content = file_path.read_text().strip().splitlines()
    assert len(content) == 100
    assert content[0] == "contract0.sol"
    assert content[-1] == "contract99.sol"


def test_read_results_empty_file(tmp_path):
    """Test _read_results with an empty file."""
    file_path = tmp_path / "empty.txt"
    file_path.touch()
    result = _read_results(file_path)
    assert result == set()


def test_read_results_missing_file(tmp_path):
    """Test _read_results with a missing file."""
    file_path = tmp_path / "missing.txt"
    result = _read_results(file_path)
    assert result == set()


def test_read_results_with_data(tmp_path):
    """Test _read_results with a populated file."""
    file_path = tmp_path / "results.txt"
    with open(file_path, "w") as f:
        f.write("contract1.sol\ncontract2.sol\n")
    result = _read_results(file_path)
    assert result == {"contract1.sol", "contract2.sol"}


def test_names_of_contracts_no_ok_file(mock_config):
    """Test names_of_contracts_that_parse when contracts_ok does not exist."""
    assert not mock_config.contracts_ok.exists()
    result = names_of_contracts_that_parse(mock_config)
    assert result == set()


def test_names_of_contracts_no_fail_file(mock_config):
    """Test names_of_contracts_that_dont_parse when contracts_fail does not exist."""
    assert not mock_config.contracts_fail.exists()
    result = names_of_contracts_that_dont_parse(mock_config)
    assert result == set()
