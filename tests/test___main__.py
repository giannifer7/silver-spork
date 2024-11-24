import pytest
from pathlib import Path
from typing import Iterator

from slith.util import subrun
from slith.config import Config
from slith.solc_select import SolcSelector
from slith.__main__ import slither_one_sol, check_contracts, run


@pytest.fixture
def mock_solc_select(monkeypatch):
    """Mock solc-select command"""

    def mock_run(*args, **kwargs):
        if args[0][0] == "slither":
            # Simulate different slither return codes
            if "error.sol" in args[0][1]:
                return type(
                    "CompletedProcess",
                    (),
                    {
                        "returncode": 255,
                        "stderr": "Error analyzing contract\n",
                        "stdout": "",
                    },
                )
            elif "warning.sol" in args[0][1]:
                return type(
                    "CompletedProcess",
                    (),
                    {"returncode": 1, "stderr": "Warning in contract\n", "stdout": ""},
                )
            else:
                return type(
                    "CompletedProcess",
                    (),
                    {"returncode": 0, "stderr": "Analysis completed\n", "stdout": ""},
                )
        elif args[0][:2] == ["solc-select", "versions"]:
            return type(
                "CompletedProcess",
                (),
                {
                    "returncode": 0,
                    "stdout": "0.4.26\n0.5.17\n0.6.12\n0.7.6\n0.8.19\n",
                    "stderr": "",
                },
            )
        return type(
            "CompletedProcess", (), {"returncode": 0, "stdout": "", "stderr": ""}
        )

    monkeypatch.setattr("slith.util.subrun", mock_run)
    monkeypatch.setattr("slith.__main__.subrun", mock_run)
    return mock_run


@pytest.fixture
def mock_solc_use(monkeypatch):
    """Mock solc_use function"""
    calls = []

    def mock_use(self, version):  # Added self parameter
        calls.append(version)

    monkeypatch.setattr("slith.solc_select.SolcSelector.solc_use", mock_use)
    return calls


@pytest.fixture
def config(tmp_path, mock_solc_select, monkeypatch):
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


def test_slither_one_sol_error(config, sample_contracts):
    """Test slither_one_sol with a contract that produces error (code 255)"""
    sol_path = config.patched_contracts_old / "error.sol"
    sol_text = sol_path.read_text()

    slither_one_sol(config, 0, sol_path, sol_text, "^0.7.0", "0.7.6")

    # Check output files
    out_file = config.results_255 / "error.sol"
    slither_file = config.slither_results_255 / "error.txt"

    assert out_file.exists()
    assert slither_file.exists()

    out_content = out_file.read_text()
    slither_content = slither_file.read_text()

    # Check content
    assert "slither:" in out_content
    assert "index: 0" in out_content
    assert 'sol: "error.sol"' in out_content
    assert "ret_code: 255" in out_content
    assert sol_text in out_content

    assert "Error analyzing contract" in slither_content


def test_slither_one_sol_warning(config, sample_contracts):
    """Test slither_one_sol with a contract that produces warning (code 1)"""
    sol_path = config.patched_contracts_old / "warning.sol"
    sol_text = sol_path.read_text()

    slither_one_sol(config, 1, sol_path, sol_text, ">=0.6.0 <0.9.0", "0.8.19")

    # Check output files
    out_file = config.results_1 / "warning.sol"
    slither_file = config.slither_results_1 / "warning.txt"

    assert out_file.exists()
    assert slither_file.exists()


def test_check_contracts(config, sample_contracts, mock_solc_select):
    """Test check_contracts function"""
    solc_sel = SolcSelector()

    def mock_contracts_iterator() -> Iterator[Path]:
        return iter(sorted(sample_contracts))

    check_contracts(config, solc_sel, mock_contracts_iterator(), limit=-1)

    # Verify output files were created
    assert any(config.results_255.glob("*.sol"))
    assert any(config.results_1.glob("*.sol"))

    # Check content of output directories
    assert (config.results_255 / "error.sol").exists()
    assert (config.results_1 / "warning.sol").exists()


def test_check_contracts_with_limit(config, sample_contracts, mock_solc_select):
    """Test check_contracts function with limit"""
    solc_sel = SolcSelector()

    def mock_contracts_iterator() -> Iterator[Path]:
        return iter(sorted(sample_contracts))

    check_contracts(config, solc_sel, mock_contracts_iterator(), limit=1)

    # Verify only one contract was processed
    total_outputs = (
        len(list(config.results_255.glob("*.sol")))
        + len(list(config.results_1.glob("*.sol")))
        + len(list(config.results_other.glob("*.sol")))
    )
    assert total_outputs == 1


def test_run(config, sample_contracts, monkeypatch):
    """Test run function"""

    def mock_contracts_that_parse(config):
        return iter(sorted(sample_contracts))

    monkeypatch.setattr(
        "slith.__main__.contracts_that_parse", mock_contracts_that_parse
    )

    run(config)

    # Verify all contracts were processed
    assert any(config.results_255.glob("*.sol"))
    assert any(config.results_1.glob("*.sol"))


def test_version_switching(config, mock_solc_use):
    """Test version switching logic in check_contracts"""
    solc_sel = SolcSelector()

    # Ensure the directory exists
    config.patched_contracts_old.mkdir(parents=True, exist_ok=True)

    # Create contract paths relative to patched_contracts_old
    contracts = [
        (
            config.patched_contracts_old / "contract1.sol",
            "pragma solidity 0.4.26;\ncontract C1 {}",
        ),
        (
            config.patched_contracts_old / "contract2.sol",
            "pragma solidity 0.8.0;\ncontract C2 {}",
        ),
        (
            config.patched_contracts_old / "contract3.sol",
            "pragma solidity 0.8.0;\ncontract C3 {}",
        ),
    ]

    # Write contract files
    for path, content in contracts:
        path.write_text(content)

    # Pass just the paths to check_contracts
    check_contracts(config, solc_sel, (path for path, _ in contracts))

    # Should see version changes in the calls
    assert len(mock_solc_use) >= 1
