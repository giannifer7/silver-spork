import bisect
from slith.util import VerTuple, Version, subrun, ver_from_tuple, ver_tuple


class UnknownSolcVersionError(RuntimeError):
    pass


def _ver_tuple(line: str) -> VerTuple:
    major, minor, patch = line.split(".", maxsplit=2)
    return (
        int(major),
        int(minor),
        int(patch if not "(" in patch else patch.split()[0]),
    )


def _solc_select_version() -> VerTuple | None:
    run_result = subrun(["solc-select", "versions"])
    if run_result.stdout.startswith("No solc version"):
        return None
    return run_result.stdout.splitlines()


def available_solidity_versions() -> list[VerTuple]:
    ver_lines = _solc_select_version()
    if ver_lines is None:
        return []
    versions_list = [_ver_tuple(line) for line in ver_lines]
    versions_list.sort()
    return versions_list


def installable_solidity_versions() -> list[VerTuple]:
    run_result = subrun(["solc-select", "install"])
    if run_result.returncode:
        return []
    versions_list = [
        _ver_tuple(line)
        for idx, line in enumerate(run_result.stdout.splitlines())
        if idx > 0
    ]
    versions_list.sort()
    return versions_list


def current_solidity_version() -> VerTuple | None:
    ver_lines = _solc_select_version()
    if ver_lines is None:
        return None
    # Get the first line containing "(" (or None if don't exists)
    line_with_paren = next(filter(lambda x: "(" in x, ver_lines), None)
    return None if line_with_paren is None else _ver_tuple(line_with_paren)


def caret_installable_versions() -> list[VerTuple]:
    result: list[VerTuple] = []
    old: VerTuple = (0, 0, 0)
    ver: VerTuple = (0, 0, 0)
    versions = installable_solidity_versions()
    for idx, ver in enumerate(versions):
        if idx > 0 and (ver[0] > old[0] or ver[1] > old[1]):
            result.append(old)
        old = ver
    if versions:
        result.append(ver)
    return result


def init_solc_select() -> None:
    if result := available_solidity_versions():
        return result
    caret_versions = caret_installable_versions()
    for tupver in caret_versions:
        ver = ver_from_tuple(tupver)
        print(f"Installing solc-{ver}")
        subrun(["solc-select", "install", ver])
    ver = ver_from_tuple(caret_versions[0])
    subrun(["solc-select", "use", ver])


def next_minor_version(ver: VerTuple) -> VerTuple:
    return ver[0], ver[1] + 1, 0


class SolcSelector:
    versions: list[VerTuple]
    versions_dict: set[VerTuple]
    installables: list[VerTuple]
    installables_dict: set[VerTuple]
    all_versions: list[VerTuple, bool]
    current: VerTuple | None
    default_solidity_version: VerTuple

    def update(self) -> None:
        self.versions = available_solidity_versions()
        self.versions_dict = set(self.versions)
        self.installables = installable_solidity_versions()
        self.installables_dict = set(self.installables)
        self.all_versions = [(ver, True) for ver in self.versions]
        self.all_versions.extend([(ver, False) for ver in self.installables])
        self.all_versions.sort()
        self.default_solidity_version = self.versions[-1]

    def __init__(self) -> None:
        init_solc_select()
        self.update()
        self.current = current_solidity_version()

    def caret_version_and_installed(self, in_ver: VerTuple) -> tuple[VerTuple, bool]:
        all_vers = self.all_versions
        return all_vers[
            bisect.bisect_left(all_vers, (next_minor_version(in_ver), False)) - 1
        ]

    def caret_version(self, in_ver: VerTuple) -> VerTuple:
        return self.caret_version_and_installed(in_ver)[0]

    def _install_solc(self, ver: VerTuple) -> None:
        if ver not in self.installables_dict:
            raise UnknownSolcVersionError(
                (
                    "Trying to install unknown solc version "
                    f"{ver_from_tuple(ver)}. Try to run 'solc-select upgrade'."
                )
            )
        subrun(["solc-select", "install", ver_from_tuple(ver)])
        self.update()

    def solc_use(self, ver: Version) -> None:
        if ver == ver_from_tuple(self.current):
            return
        vertup = ver_tuple(ver)
        if vertup not in self.versions_dict:
            self._install_solc(vertup)
        subrun(["solc-select", "use", ver])
        self.current = ver_tuple(ver)
