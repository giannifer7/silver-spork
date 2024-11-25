import pytest
from pathlib import Path
from typing import Iterator

from slith.config import Config
from slith.solc_select import SolcSelector
from slith.__main__ import check_contracts, run


@pytest.fixture
def config(tmp_path, monkeypatch):
    """Create a Config instance with temporary directories"""
    # Create base paths
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Override data_dir in Config
    monkeypatch.setattr(Config, "data_dir", data_dir)

    # Create config instance (it will use the mocked data_dir)
    config = Config()

    return config


@pytest.fixture
def sample_contracts(config):
    """Create sample contract files for testing"""
    contracts = {
        "normal.sol": "pragma solidity 0.8.0;\ncontract Normal {}\n",
        "error.sol": "pragma solidity ^0.7.0;\ncontract Error {}\n",
        "warning.sol": "pragma solidity >=0.6.0 <0.9.0;\ncontract Warning {}\n",
    }

    # Ensure the directory exists
    config.patched_contracts_old.mkdir(parents=True, exist_ok=True)

    for name, content in contracts.items():
        path = config.patched_contracts_old / name
        path.write_text(content)

    return list(config.patched_contracts_old.glob("*.sol"))


def test_check_contracts(config, sample_contracts, monkeypatch):
    """Test check_contracts function"""
    solc_sel = SolcSelector()
    called_count = 0

    def mock_contracts_iterator() -> Iterator[Path]:
        return iter(sorted(sample_contracts))

    def mock_slither_one_sol(*args, **kwargs):
        nonlocal called_count
        called_count += 1

    monkeypatch.setattr("slith.__main__.slither_one_sol", mock_slither_one_sol)

    check_contracts(config, solc_sel, mock_contracts_iterator(), limit=-1)
    assert called_count == len(sample_contracts)


def test_check_contracts_with_limit(config, sample_contracts, monkeypatch):
    """Test check_contracts function with limit"""
    solc_sel = SolcSelector()
    called_count = 0

    def mock_contracts_iterator() -> Iterator[Path]:
        return iter(sorted(sample_contracts))

    def mock_slither_one_sol(*args, **kwargs):
        nonlocal called_count
        called_count += 1

    monkeypatch.setattr("slith.__main__.slither_one_sol", mock_slither_one_sol)

    check_contracts(config, solc_sel, mock_contracts_iterator(), limit=1)
    assert called_count == 1


def test_run(config, sample_contracts, monkeypatch):
    """Test run function"""
    called_count = 0

    def mock_contracts_that_parse(config):
        return iter(sorted(sample_contracts))

    def mock_slither_one_sol(*args, **kwargs):
        nonlocal called_count
        called_count += 1

    monkeypatch.setattr(
        "slith.__main__.contracts_that_parse", mock_contracts_that_parse
    )
    monkeypatch.setattr("slith.__main__.slither_one_sol", mock_slither_one_sol)

    run(config)
    assert called_count == len(sample_contracts)
