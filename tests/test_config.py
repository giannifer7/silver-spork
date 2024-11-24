import pytest
from pathlib import Path
from subprocess import CompletedProcess

from slith.util import subrun
from slith.config import Config


@pytest.fixture
def mock_solc_select(monkeypatch):
    def mock_run(*args, **kwargs):
        return CompletedProcess(
            args=["solc-select", "versions"],
            returncode=0,
            stdout="0.4.26\n0.5.17\n0.6.12\n0.7.6\n0.8.19",
            stderr="",
        )

    monkeypatch.setattr("slith.util.subrun", mock_run)
    return mock_run


@pytest.fixture
def mock_failed_solc_select(monkeypatch):
    def mock_run(*args, **kwargs):
        return CompletedProcess(
            args=["solc-select", "versions"],
            returncode=1,
            stdout="",
            stderr="Error running solc-select",
        )

    monkeypatch.setattr("slith.util.subrun", mock_run)
    return mock_run


@pytest.fixture
def config(tmp_path, mock_solc_select):
    """Create a Config instance with temporary directories"""
    # Create base paths
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Patch the paths in Config to use temporary directory
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(Config, "data_dir", data_dir / "data_dir")

    config = Config()
    return config


def test_subrun():
    """Test subrun function with a simple command"""
    result = subrun(["echo", "test"])
    assert result.returncode == 0
    assert result.stdout.strip() == "test"


def test_available_solidity_versions_with_parentheses(monkeypatch):
    """Test parsing versions with parentheses in patch number"""

    def mock_run(*args, **kwargs):
        return CompletedProcess(
            args=["solc-select", "versions"],
            returncode=0,
            stdout="0.4.26\n0.5.17\n0.6.12 (some text)\n0.7.6\n0.8.19",
            stderr="",
        )

    monkeypatch.setattr("slith.util.subrun", mock_run)

    versions = _available_solidity_versions()
    assert len(versions) == 5
    assert versions[2] == (0, 6, 12)  # Verify parentheses are handled correctly


def test_config_initialization(config):
    """Test Config initialization and directory creation"""
    # Check that all required directories are created
    dirs_to_check = [
        config.contracts_meta,
        config.contracts_errors,
        config.results_255,
        config.results_1,
        config.results_other,
        config.slither_results_255,
        config.slither_results_1,
        config.slither_results_other,
    ]

    for directory in dirs_to_check:
        assert directory.exists()
        # Test directory is writable
        test_file = directory / "test_write.tmp"
        try:
            test_file.touch()
            assert test_file.exists()
        finally:
            if test_file.exists():
                test_file.unlink()


def test_config_default_solidity_version(config):
    """Test that default Solidity version is set to latest available version"""
    assert config.default_solidity_version == (0, 8, 19)
    assert config.default_solidity_version == config.available_solidity_versions[-1]


def test_config_paths_structure(config):
    """Test the proper structure of all paths"""
    # Test relative paths
    assert config.contracts_ok == config.contracts_meta / "contracts_parse_ok.txt"
    assert config.contracts_fail == config.contracts_meta / "contracts_parse_fail.txt"
    assert config.contracts_errors == config.contracts_meta / "errors"

    # Test results directory structure
    assert config.results_255 == config.results_base_dir / "ret_255"
    assert config.results_1 == config.results_base_dir / "ret_1"
    assert config.results_other == config.results_base_dir / "ret_other"

    # Test slither results directory structure
    assert (
        config.slither_results_base_dir == config.results_base_dir / "slither_results"
    )
    assert config.slither_results_255 == config.slither_results_base_dir / "ret_255"
    assert config.slither_results_1 == config.slither_results_base_dir / "ret_1"
    assert config.slither_results_other == config.slither_results_base_dir / "ret_other"


def test_contracts_glob(config):
    """Test contract file globbing"""
    # Create test contract files
    contract_dir = config.patched_contracts_old
    contract_dir.mkdir(parents=True, exist_ok=True)

    # Create test files
    (contract_dir / "test1.sol").touch()
    (contract_dir / "test2.sol").touch()
    (contract_dir / "not_a_contract.txt").touch()

    # Get list of contracts
    contracts = list(config.contracts_glob())

    # Verify results
    assert len(contracts) == 2
    assert all(c.suffix == ".sol" for c in contracts)
    assert all(c.parent == contract_dir for c in contracts)
    assert set(c.name for c in contracts) == {"test1.sol", "test2.sol"}
