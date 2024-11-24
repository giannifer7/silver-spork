import re
import bisect
from enum import IntEnum, auto
from dataclasses import dataclass
from typing import TypeAlias

from slith.util import FileName, Version, VerTuple, ver_tuple, ver_from_tuple
from slith.solc_select import SolcSelector


PRAGMA_SOLIDITY_RE = re.compile(r"pragma solidity (?P<caret>\^|>?)(?P<ver>[^;]+);")
VERSION_RANGE_RE = re.compile(r"=(?P<min>\S+)\s+<(?P<sup>.+)")


CaretFile: TypeAlias = tuple[bool, FileName]
CaretFiles: TypeAlias = list[CaretFile]
FilesOfVersion: TypeAlias = tuple[VerTuple, CaretFiles]
FilesOfVersions: TypeAlias = list[FilesOfVersion]

# type CaretFile = tuple[bool, FileName]
# type CaretFiles = list[CaretFile]
# type FilesOfVersion = tuple[VerTuple, CaretFiles]
# type FilesOfVersions = list[FilesOfVersion]


class VersionType(IntEnum):
    CARET = auto()
    STRICT = auto()
    RANGE = auto()
    UNDEFINED = auto()


@dataclass
class RichVersion:
    ver_type: VersionType
    found_version: Version | None
    version: Version
    sup_version: Version | None

    def version_to_use(self, sele: SolcSelector) -> Version:
        if self.ver_type != VersionType.RANGE:
            return self.version
        if self.sup_version is None:
            return ver_from_tuple(sele.default_solidity_version)
        sup_tuple = ver_tuple(self.sup_version)
        versions = sele.versions
        return ver_from_tuple(versions[bisect.bisect_left(versions, sup_tuple) - 1])


def match_pragma_solidity(
    sol_text: str,
) -> tuple[VersionType, VerTuple, VerTuple | None] | None:
    match = PRAGMA_SOLIDITY_RE.match(sol_text)
    if match is None:
        return None
    sver = match.group("ver")
    match match.group("caret"):
        case "^":
            return VersionType.CARET, ver_tuple(sver), None
        case ">":
            mo = VERSION_RANGE_RE.match(sver)
            if mo is None:
                return None
            return (
                VersionType.RANGE,
                ver_tuple(mo.group("min")),
                ver_tuple(mo.group("sup")),
            )
        case _:
            try:
                return VersionType.STRICT, ver_tuple(sver), None
            except Exception:
                return None


def version_from_pragma(sele: SolcSelector, sol_text: str) -> RichVersion:
    default_version = sele.default_solidity_version
    pragma = match_pragma_solidity(sol_text)
    if pragma is None:
        ver_type, ver_tup, sup = VersionType.UNDEFINED, default_version, None
    else:
        ver_type, ver_tup, sup = pragma
    ver = ver_from_tuple(ver_tup)
    match ver_type:
        case VersionType.CARET:
            return RichVersion(
                ver_type,
                ver,
                ver_from_tuple(sele.caret_version(ver_tup)),
                None,
            )
        case VersionType.RANGE:
            return RichVersion(
                ver_type,
                ver,
                ver,
                ver_from_tuple(sup if sup is not None else default_version),
            )
        case VersionType.STRICT:
            return RichVersion(
                ver_type,
                ver,
                ver,
                None,
            )
        case _:
            return RichVersion(
                ver_type,
                ver,
                ver,
                None,
            )
