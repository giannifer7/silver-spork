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
    next_minor_version,
    caret_version,
    solc_use,
)
from slith.config import Config, subrun


@pytest.fixture
def mock_solc_select(monkeypatch):
    """Mock solc-select command"""

    def mock_run(*args, **kwargs):
        if args[0] == ["solc-select", "versions"]:
            return type(
                "CompletedProcess",
                (),
                {
                    "returncode": 0,
                    "stdout": "0.4.26\n0.5.17\n0.6.12\n0.7.6\n0.8.19\n",
                    "stderr": "",
                },
            )
        elif args[0][:2] == ["solc-select", "use"]:
            return type(
                "CompletedProcess", (), {"returncode": 0, "stdout": "", "stderr": ""}
            )
        return type(
            "CompletedProcess",
            (),
            {"returncode": 1, "stdout": "", "stderr": "Unknown command"},
        )

    monkeypatch.setattr("slith.pragma_solidity.subrun", mock_run)
    return mock_run


@pytest.fixture
def config(mock_solc_select, tmp_path):
    """Create a Config instance with mocked solidity versions"""
    return Config()


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


def test_version_from_pragma_caret(config):
    """Test version_from_pragma with caret version"""
    rich_ver = version_from_pragma(config, "pragma solidity ^0.8.0;")
    assert rich_ver.ver_type == VersionType.CARET
    assert rich_ver.found_version == "0.8.0"
    assert rich_ver.version == "0.8.19"  # Latest compatible version
    assert rich_ver.sup_version is None


def test_version_from_pragma_strict(config):
    """Test version_from_pragma with strict version"""
    rich_ver = version_from_pragma(config, "pragma solidity 0.8.0;")
    assert rich_ver.ver_type == VersionType.STRICT
    assert rich_ver.found_version == "0.8.0"
    assert rich_ver.version == "0.8.0"
    assert rich_ver.sup_version is None


def test_version_from_pragma_range(config):
    """Test version_from_pragma with range version"""
    rich_ver = version_from_pragma(config, "pragma solidity >=0.8.0 <0.9.0;")
    assert rich_ver.ver_type == VersionType.RANGE
    assert rich_ver.found_version == "0.8.0"
    assert rich_ver.version == "0.8.0"
    assert rich_ver.sup_version == "0.9.0"


def test_version_from_pragma_undefined(config):
    """Test version_from_pragma with undefined version"""
    rich_ver = version_from_pragma(config, "// no pragma")
    assert rich_ver.ver_type == VersionType.UNDEFINED
    assert rich_ver.found_version == "0.8.19"  # Default version
    assert rich_ver.version == "0.8.19"
    assert rich_ver.sup_version is None


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


def test_next_minor_version():
    """Test next minor version calculation"""
    assert next_minor_version((0, 8, 0)) == (0, 9, 0)
    assert next_minor_version((1, 2, 3)) == (1, 3, 0)


def test_caret_version(config):
    """Test caret version resolution"""
    result = caret_version(config, (0, 8, 0))
    assert result == (0, 8, 19)  # Should get latest compatible version


def test_solc_use(mock_solc_select):
    """Test solc version switching"""
    solc_use("0.8.0")
    # No exception means success
    # We could add more assertions if the function returned something


def test_rich_version_version_to_use(config):
    """Test RichVersion.version_to_use method"""
    # Test CARET version
    caret_ver = RichVersion(VersionType.CARET, "0.8.0", "0.8.19", None)
    assert caret_ver.version_to_use(config) == "0.8.19"

    # Test STRICT version
    strict_ver = RichVersion(VersionType.STRICT, "0.8.0", "0.8.0", None)
    assert strict_ver.version_to_use(config) == "0.8.0"

    # Test RANGE version
    range_ver = RichVersion(VersionType.RANGE, "0.8.0", "0.8.0", "0.9.0")
    assert range_ver.version_to_use(config) == "0.8.19"

    # Test UNDEFINED version (should use default)
    undef_ver = RichVersion(VersionType.UNDEFINED, None, "0.8.19", None)
    assert undef_ver.version_to_use(config) == "0.8.19"


@pytest.mark.parametrize(
    "ver_str,expected",
    [
        ("0.8.0", (0, 8, 0)),
        ("1.2.3", (1, 2, 3)),
        ("0.4.26", (0, 4, 26)),
    ],
)
def test_ver_tuple_variations(ver_str, expected):
    """Test ver_tuple function with various version formats"""
    assert ver_tuple(ver_str) == expected


def test_rich_version_invalid_range(config):
    """Test RichVersion with invalid range"""
    # Create a RichVersion with a sup_version that doesn't exist
    rich_ver = RichVersion(VersionType.RANGE, "0.8.0", "0.8.0", "999.999.999")
    # Should fall back to default version
    assert rich_ver.version_to_use(config) == ver_from_tuple(
        config.default_solidity_version
    )
