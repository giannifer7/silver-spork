import bisect
import pytest
from slith.pragma_solidity import (
    PRAGMA_SOLIDITY_RE,
    VERSION_RANGE_RE,
    VersionType,
    RichVersion,
    match_pragma_solidity,
    version_from_pragma,
    ver_tuple,
    ver_from_tuple,
)

from slith.solc_select import SolcSelector


@pytest.fixture
def mock_solc_selector(monkeypatch):
    """Mock SolcSelector with predefined versions"""

    class MockSolcSelector:
        def __init__(self):
            self.versions = [  # Changed from available_solidity_versions
                (0, 4, 26),
                (0, 5, 17),
                (0, 6, 12),
                (0, 7, 6),
                (0, 8, 19),
            ]
            self.default_solidity_version = (0, 8, 19)

        def caret_version(self, ver_tup):
            return max(
                v
                for v in self.versions
                if v[:2] == ver_tup[:2]  # Changed this too
            )

    return MockSolcSelector()


def test_pragma_solidity_re_caret():
    """Test pragma solidity regex with caret version"""
    match = PRAGMA_SOLIDITY_RE.match("pragma solidity ^0.8.0;")
    assert match is not None
    assert match.group("caret") == "^"
    assert match.group("ver") == "0.8.0"


def test_pragma_solidity_re_strict():
    """Test pragma solidity regex with strict version"""
    match = PRAGMA_SOLIDITY_RE.match("pragma solidity 0.8.0;")
    assert match is not None
    assert match.group("caret") == ""
    assert match.group("ver") == "0.8.0"


def test_pragma_solidity_re_range():
    """Test pragma solidity regex with range version"""
    match = PRAGMA_SOLIDITY_RE.match("pragma solidity >=0.8.0 <0.9.0;")
    assert match is not None
    assert match.group("caret") == ">"
    assert match.group("ver") == "=0.8.0 <0.9.0"


def test_version_range_re():
    """Test version range regex"""
    match = VERSION_RANGE_RE.match("=0.8.0 <0.9.0")
    assert match is not None
    assert match.group("min") == "0.8.0"
    assert match.group("sup") == "0.9.0"


@pytest.mark.parametrize(
    "sol_text,expected",
    [
        ("pragma solidity ^0.8.0;", (VersionType.CARET, (0, 8, 0), None)),
        ("pragma solidity 0.8.0;", (VersionType.STRICT, (0, 8, 0), None)),
        ("pragma solidity >=0.8.0 <0.9.0;", (VersionType.RANGE, (0, 8, 0), (0, 9, 0))),
        ("// no pragma", None),
        ("pragma solidity invalid;", None),
    ],
)
def test_match_pragma_solidity(sol_text, expected):
    """Test pragma solidity matching with various formats"""
    result = match_pragma_solidity(sol_text)
    assert result == expected


def test_version_from_pragma_caret(mock_solc_selector):
    """Test version_from_pragma with caret version"""
    rich_ver = version_from_pragma(mock_solc_selector, "pragma solidity ^0.8.0;")
    assert rich_ver.ver_type == VersionType.CARET
    assert rich_ver.found_version == "0.8.0"
    assert rich_ver.version == "0.8.19"  # Highest available 0.8.x version
    assert rich_ver.sup_version is None


def test_version_from_pragma_range(mock_solc_selector):
    """Test version_from_pragma with range version"""
    rich_ver = version_from_pragma(
        mock_solc_selector, "pragma solidity >=0.8.0 <0.9.0;"
    )
    assert rich_ver.ver_type == VersionType.RANGE
    assert rich_ver.found_version == "0.8.0"
    assert rich_ver.version == "0.8.0"
    assert rich_ver.sup_version == "0.9.0"


def test_version_from_pragma_strict(mock_solc_selector):
    """Test version_from_pragma with strict version"""
    rich_ver = version_from_pragma(mock_solc_selector, "pragma solidity 0.8.0;")
    assert rich_ver.ver_type == VersionType.STRICT
    assert rich_ver.found_version == "0.8.0"
    assert rich_ver.version == "0.8.0"
    assert rich_ver.sup_version is None


def test_version_from_pragma_undefined(mock_solc_selector):
    """Test version_from_pragma with undefined version"""
    rich_ver = version_from_pragma(mock_solc_selector, "// no pragma")
    assert rich_ver.ver_type == VersionType.UNDEFINED
    assert rich_ver.found_version == "0.8.19"
    assert rich_ver.version == "0.8.19"
    assert rich_ver.sup_version is None


def test_version_to_use_caret(mock_solc_selector):
    """Test version_to_use with caret version"""
    rich_ver = RichVersion(
        ver_type=VersionType.CARET,
        found_version="0.8.0",
        version="0.8.19",
        sup_version=None,
    )
    assert rich_ver.version_to_use(mock_solc_selector) == "0.8.19"


def test_version_to_use_strict(mock_solc_selector):
    """Test version_to_use with strict version"""
    rich_ver = RichVersion(
        ver_type=VersionType.STRICT,
        found_version="0.8.0",
        version="0.8.0",
        sup_version=None,
    )
    assert rich_ver.version_to_use(mock_solc_selector) == "0.8.0"


def test_version_to_use_range(mock_solc_selector):
    """Test version_to_use with range version"""
    rich_ver = RichVersion(
        ver_type=VersionType.RANGE,
        found_version="0.8.0",
        version="0.8.0",
        sup_version="0.9.0",
    )
    assert rich_ver.version_to_use(mock_solc_selector) == "0.8.19"


def test_version_to_use_range_no_sup(mock_solc_selector):
    """Test version_to_use with range version but no sup_version"""
    rich_ver = RichVersion(
        ver_type=VersionType.RANGE,
        found_version="0.8.0",
        version="0.8.0",
        sup_version=None,
    )
    assert rich_ver.version_to_use(mock_solc_selector) == "0.8.19"


def test_ver_tuple():
    """Test version tuple conversion"""
    assert ver_tuple("0.8.0") == (0, 8, 0)
    assert ver_tuple("1.2.3") == (1, 2, 3)
    with pytest.raises(ValueError):
        ver_tuple("invalid")


def test_ver_from_tuple():
    """Test tuple to version string conversion"""
    assert ver_from_tuple((0, 8, 0)) == "0.8.0"
    assert ver_from_tuple((1, 2, 3)) == "1.2.3"
