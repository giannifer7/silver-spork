import pytest
from pathlib import Path

from slith.config import Config
from slith.solc_select import SolcSelector
from slith.slither import (
    front_matter,
    dirs_from_ret_code,
    out_text,
    write_out_file,
    do_slither_one_sol,
    slither_one_sol,
)


@pytest.fixture
def mock_slither(monkeypatch):
    """Mock slither command"""

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
        return type(
            "CompletedProcess", (), {"returncode": 0, "stdout": "", "stderr": ""}
        )

    monkeypatch.setattr("slith.slither.subrun", mock_run)
    return mock_run


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


def test_front_matter():
    """Test front matter generation"""
    matter = front_matter(1, Path("test.sol"), "0.8.0", "0.8.19", 0)
    assert "index: 1" in matter
    assert 'sol: "test.sol"' in matter
    assert "found_version: 0.8.0" in matter
    assert "checked_version: 0.8.19" in matter
    assert "ret_code: 0" in matter


def test_dirs_from_ret_code(config):
    """Test directory selection based on return code"""
    # Test error code
    out_dir, slither_dir = dirs_from_ret_code(config, 255)
    assert out_dir == config.results_255
    assert slither_dir == config.slither_results_255

    # Test warning code
    out_dir, slither_dir = dirs_from_ret_code(config, 1)
    assert out_dir == config.results_1
    assert slither_dir == config.slither_results_1

    # Test other codes
    out_dir, slither_dir = dirs_from_ret_code(config, 0)
    assert out_dir == config.results_other
    assert slither_dir == config.slither_results_other


def test_out_text():
    """Test output text formatting"""
    slither_block = "Test Output"
    sol_text = "contract Test {}"
    result = out_text(slither_block, sol_text)
    assert result == "/*\nTest Output*/\n\ncontract Test {}\n"


def test_write_out_file(config):
    """Test writing output file"""
    out_dir = config.results_other
    out_dir.mkdir(parents=True, exist_ok=True)
    sol_path = Path("test.sol")
    write_out_file(out_dir, sol_path, "Test Output", "contract Test {}")
    assert (out_dir / "test.sol").exists()
    content = (out_dir / "test.sol").read_text()
    assert "Test Output" in content
    assert "contract Test {}" in content


def test_do_slither_one_sol(config, mock_slither):
    """Test slither analysis execution"""
    sol_path = config.patched_contracts_old / "error.sol"
    do_slither_one_sol(config, 0, sol_path, "contract Error {}", "0.7.0", "0.7.6")

    # Check output files
    out_file = config.results_255 / "error.sol"
    slither_file = config.slither_results_255 / "error.txt"

    assert out_file.exists()
    assert slither_file.exists()
    assert "Error analyzing contract" in slither_file.read_text()


def test_slither_one_sol(config, mock_slither, monkeypatch):
    """Test complete slither analysis process"""
    solc_sel = SolcSelector()
    sol_path = config.patched_contracts_old / "warning.sol"
    sol_text = "pragma solidity >=0.6.0 <0.9.0;\ncontract Warning {}"

    def mock_solc_use(self, version):
        pass

    monkeypatch.setattr("slith.solc_select.SolcSelector.solc_use", mock_solc_use)

    slither_one_sol(config, solc_sel, 0, sol_path, sol_text)

    # Check output files
    assert (config.results_1 / "warning.sol").exists()
    assert (config.slither_results_1 / "warning.txt").exists()
