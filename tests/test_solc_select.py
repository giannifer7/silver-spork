import pytest
from typing import List, Tuple
from slith.util import Version, VerTuple
from slith.solc_select import (
    UnknownSolcVersionError,
    _ver_tuple,
    _solc_select_version,
    available_solidity_versions,
    installable_solidity_versions,
    current_solidity_version,
    caret_installable_versions,
    init_solc_select,
    next_minor_version,
    SolcSelector,
)


def test_ver_tuple_with_parentheses():
    """Test _ver_tuple with version containing parentheses"""
    assert _ver_tuple("0.8.19 (default)") == (0, 8, 19)
    assert _ver_tuple("1.2.3 (installed)") == (1, 2, 3)


def test_ver_tuple_invalid():
    """Test _ver_tuple with invalid formats"""
    with pytest.raises(ValueError):
        _ver_tuple("invalid")
    with pytest.raises(ValueError):
        _ver_tuple("0.8")


@pytest.fixture
def mock_solc_versions(monkeypatch):
    def mock_subrun(args):
        if args[0] == "solc-select":
            if args[1] == "versions":
                return type(
                    "CompletedProcess",
                    (),
                    {
                        "returncode": 0,
                        "stdout": "0.4.26\n0.5.17\n0.8.19 (default)\n",
                        "stderr": "",
                    },
                )
            elif args[1] == "install":
                return type(
                    "CompletedProcess",
                    (),
                    {
                        "returncode": 0,
                        "stdout": "Available versions:\n0.4.26\n0.5.17\n0.8.19\n",
                        "stderr": "",
                    },
                )

    monkeypatch.setattr("slith.solc_select.subrun", mock_subrun)


def test_solc_select_version_no_versions(monkeypatch):
    """Test _solc_select_version when no versions are installed"""

    def mock_subrun(args):
        return type(
            "CompletedProcess",
            (),
            {"returncode": 0, "stdout": "No solc version installed", "stderr": ""},
        )

    monkeypatch.setattr("slith.solc_select.subrun", mock_subrun)
    assert _solc_select_version() is None


def test_available_solidity_versions_empty(monkeypatch):
    """Test available_solidity_versions when no versions are available"""

    def mock_subrun(args):
        return type(
            "CompletedProcess",
            (),
            {"returncode": 0, "stdout": "No solc version installed", "stderr": ""},
        )

    monkeypatch.setattr("slith.solc_select.subrun", mock_subrun)
    assert available_solidity_versions() == []


def test_available_solidity_versions(mock_solc_versions):
    """Test available_solidity_versions with multiple versions"""
    versions = available_solidity_versions()
    assert versions == [(0, 4, 26), (0, 5, 17), (0, 8, 19)]


def test_installable_solidity_versions_error(monkeypatch):
    """Test installable_solidity_versions when command fails"""

    def mock_subrun(args):
        return type(
            "CompletedProcess", (), {"returncode": 1, "stdout": "", "stderr": ""}
        )

    monkeypatch.setattr("slith.solc_select.subrun", mock_subrun)
    assert installable_solidity_versions() == []


def test_installable_solidity_versions(mock_solc_versions):
    """Test installable_solidity_versions with available versions"""
    versions = installable_solidity_versions()
    assert versions == [(0, 4, 26), (0, 5, 17), (0, 8, 19)]


def test_current_solidity_version(mock_solc_versions):
    """Test current_solidity_version with default version"""
    assert current_solidity_version() == (0, 8, 19)


def test_current_solidity_version_no_default(monkeypatch):
    """Test current_solidity_version when no default version exists"""

    def mock_subrun(args):
        return type(
            "CompletedProcess",
            (),
            {"returncode": 0, "stdout": "0.4.26\n0.5.17\n0.8.19\n", "stderr": ""},
        )

    monkeypatch.setattr("slith.solc_select.subrun", mock_subrun)
    assert current_solidity_version() is None


def test_caret_installable_versions(mock_solc_versions):
    """Test caret_installable_versions"""
    versions = caret_installable_versions()
    assert versions == [(0, 4, 26), (0, 5, 17), (0, 8, 19)]


def test_caret_installable_versions_empty(monkeypatch):
    """Test caret_installable_versions with no versions"""

    def mock_subrun(args):
        return type(
            "CompletedProcess", (), {"returncode": 1, "stdout": "", "stderr": ""}
        )

    monkeypatch.setattr("slith.solc_select.subrun", mock_subrun)
    assert caret_installable_versions() == []


def test_init_solc_select_fresh_install(monkeypatch):
    """Test init_solc_select when no versions are installed"""
    calls = []

    def mock_subrun(args):
        calls.append(args)
        if args[0] == "solc-select":
            if args[1] == "versions":
                return type(
                    "CompletedProcess",
                    (),
                    {
                        "returncode": 0,
                        "stdout": "No solc version installed",
                        "stderr": "",
                    },
                )
            elif args[1] == "install":
                return type(
                    "CompletedProcess",
                    (),
                    {
                        "returncode": 0,
                        "stdout": "Available versions:\n0.4.26\n0.5.17\n0.8.19\n",
                        "stderr": "",
                    },
                )

    monkeypatch.setattr("slith.solc_select.subrun", mock_subrun)
    init_solc_select()
    assert any("install" in call and "0.4.26" in call for call in calls)


def test_next_minor_version():
    """Test next_minor_version function"""
    assert next_minor_version((0, 8, 19)) == (0, 9, 0)
    assert next_minor_version((1, 2, 3)) == (1, 3, 0)


def test_solc_selector_init(mock_solc_versions):
    """Test SolcSelector initialization"""
    selector = SolcSelector()
    assert selector.versions == [(0, 4, 26), (0, 5, 17), (0, 8, 19)]
    assert selector.default_solidity_version == (0, 8, 19)
    assert selector.current == (0, 8, 19)


def test_solc_selector_caret_version(mock_solc_versions):
    """Test SolcSelector caret_version method"""
    selector = SolcSelector()
    assert selector.caret_version((0, 8, 0)) == (0, 8, 19)


def test_install_solc_unknown_version(mock_solc_versions):
    """Test _install_solc with unknown version"""
    selector = SolcSelector()
    with pytest.raises(UnknownSolcVersionError):
        selector._install_solc((9, 9, 9))


def test_solc_use_same_version(mock_solc_versions):
    """Test solc_use when version is already in use"""
    selector = SolcSelector()
    selector.current = (0, 8, 19)
    selector.solc_use("0.8.19")  # Should not trigger any subrun calls
