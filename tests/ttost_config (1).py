import pytest
from pathlib import Path
from subprocess import CompletedProcess

from slith.config import Config, subrun, make_banner, _available_solidity_versions


@pytest.fixture
def mock_solc_select(monkeypatch):
    def mock_run(*args, **kwargs):
        return CompletedProcess(
            args=["solc-select", "versions"],
            returncode=0,
            stdout="0.4.26\n0.5.17\n0.6.12\n0.7.6\n0.8.19",
            stderr="",
        )

    monkeypatch.setattr("slith.config.subrun", mock_run)
    return mock_run


@pytest.fixture
def config(tmp_path, mock_solc_select):
    """Create a Config instance with temporary directories"""
    # Create base paths
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Patch the paths in Config to use temporary directory
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        Config, "patched_contracts_old", data_dir / "patched_contracts_old"
    )
    monkeypatch.setattr(Config, "contracts_meta", data_dir / "meta")
    monkeypatch.setattr(Config, "results_base_dir", data_dir / "results")

    config = Config()
    return config


def test_subrun():
    """Test subrun function with a simple command"""
    result = subrun(["echo", "test"])
    assert result.returncode == 0
    assert result.stdout.strip() == "test"


def test_make_banner():
    """Test banner creation with different texts"""
    text = "Test Banner"
    banner = make_banner(text)
    assert len(banner) == 100  # Banner width should be 100
    assert text in banner
    assert banner.startswith("=")
    assert banner.endswith("=")


def test_available_solidity_versions(mock_solc_select):
    """Test parsing of available Solidity versions"""
    versions = _available_solidity_versions()
    assert len(versions) == 5
    assert versions[0] == (0, 4, 26)
    assert versions[-1] == (0, 8, 19)


def test_available_solidity_versions_error(monkeypatch):
    """Test error handling when solc-select fails"""

    def mock_failed_run(*args, **kwargs):
        return CompletedProcess(
            args=["solc-select", "versions"], returncode=1, stdout="", stderr="Error"
        )

    monkeypatch.setattr("slith.config.subrun", mock_failed_run)

    with pytest.raises(RuntimeError) as exc_info:
        _available_solidity_versions()
    assert "solc-select versions failed" in str(exc_info.value)


def test_config_initialization(config):
    """Test Config initialization and directory creation"""
    # Check that all required directories are created
    assert config.contracts_meta.exists()
    assert config.contracts_errors.exists()
    assert config.results_255.exists()
    assert config.results_1.exists()
    assert config.results_other.exists()
    assert config.slither_results_255.exists()
    assert config.slither_results_1.exists()
    assert config.slither_results_other.exists()


def test_config_default_solidity_version(config):
    """Test that default Solidity version is set to latest available version"""
    assert config.default_solidity_version == (0, 8, 19)


def test_contracts_glob(config):
    """Test contract file globbing"""
    # Create some test contract files
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


def test_directory_permissions(config):
    """Test that directories are created and are writable"""
    # Check that all directories exist and are writable
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
        # Check directory exists
        assert directory.exists()

        # Check if directory is writable by trying to create a test file
        test_file = directory / "test_permissions.tmp"
        try:
            test_file.touch()
            assert test_file.exists()
        finally:
            # Clean up test file
            if test_file.exists():
                test_file.unlink()


def test_config_paths_are_pathlib_paths(config):
    """Test that all path attributes are Path objects"""
    path_attributes = [
        "patched_contracts_old",
        "contracts_meta",
        "contracts_ok",
        "contracts_fail",
        "contracts_errors",
        "results_base_dir",
        "results_255",
        "results_1",
        "results_other",
        "slither_results_base_dir",
        "slither_results_255",
        "slither_results_1",
        "slither_results_other",
    ]

    for attr in path_attributes:
        assert isinstance(getattr(config, attr), Path)
