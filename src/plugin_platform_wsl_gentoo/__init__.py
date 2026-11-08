"""WSL Gentoo for Liminal (the user, 2026-11-07: "the platform is the interface for the software/hardware
which facilitates the liminal framework"; "the scope of the plugin is setting up WSL/Ubuntu and supporting
docker for the platform"; "then create a gentoo and fedora plugin as well, same scope/function"): Gentoo
in WSL 2 on this Windows PC, set up by the plugin (WSL itself, the distribution, systemd and the default
user, Docker inside, the engine started, the user in the docker group), and its engine offered to the
framework as the Docker instance `wsl-gentoo` (liminal_libs.docker.instances). Everything is the library's
WslDistribution (liminal_libs.machines.wsl); this module says which distribution.

    python -m plugin_platform_wsl_gentoo status | setup [STEP ...] | run -- COMMAND | instances
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from time import monotonic

from liminal_libs.machines.wsl import WslDistribution, WslError

__version__ = "0.4.2"

STAGE3_S = 300.0  # Gentoo's list of the latest stage3 is kept this long, then read again
# The list's entry: the build's folder and tarball, then its size in bytes
# ("20261108T170107Z/stage3-amd64-systemd-20261108T170107Z.tar.xz 280639788"). Nothing around it matches: the list's
# comments, nor its PGP clear-signing (the armour, "Hash: SHA256", the signature's base64).
ENTRY = re.compile(r"^(?P<path>[\w.-]+/stage3-[\w.-]+\.tar\.\w+)\s+(?P<size>\d+)\s*$")
# A line of the tarball's .sha256, clear-signed the same way: the digest, then the file it is of (sha256sum's form).
DIGEST = re.compile(r"^(?P<sha256>[0-9a-fA-F]{64})\s+\*?(?P<name>\S+)\s*$")


def _read_text(url: str) -> str:
    import urllib.request

    with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 - the plugin's own url
        return r.read().decode("utf-8", "replace")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _discard(path: Path) -> str:
    """A tarball that failed its check removed; in words, for the error that says why."""
    try:
        path.unlink(missing_ok=True)
    except OSError as e:  # Windows still holds it (a scan, say): it stays, and is checked again before any import
        return f"it could not be removed ({e}), and is checked again before any import"
    return "it is removed, and the next install downloads it again"


class WslGentooPlugin(WslDistribution):
    name = "wsl-gentoo"
    ICON = "gentoo"  # Gentoo's g (liminal-libs 1.33.0's icons.js)
    title = "WSL Gentoo"
    about = "Gentoo in WSL 2 on this Windows PC, with Docker inside: the Linux the platform's containers run in"
    api = "2.1"
    order = 702
    distribution = "Liminal-Gentoo"  # Liminal's own, imported from Gentoo's stage3 (never a Gentoo of the user's)
    family = "emerge"
    space_gb = 20.0  # emerge compiles Docker: room for the sources and the builds
    architectures = ("AMD64", "x86_64")  # the amd64 stage3 it imports
    install_name = ""
    DISTRIBUTION_VAR = "WSL_GENTOO_DISTRIBUTION"
    USER_VAR = "WSL_GENTOO_USER"

    BASE_URL = "https://distfiles.gentoo.org/releases/amd64/autobuilds/"
    LATEST = "latest-stage3-amd64-systemd.txt"

    def __init__(self, wsl=None, data=None, fetch=None, read=None):
        super().__init__(wsl=wsl, data=data, fetch=fetch)
        self._read = read  # (url) -> text: Gentoo's list of the latest stage3 and its checksums, urllib unless given
        self._stage3: tuple[float, tuple[str, int]] | None = None  # (when read, (url, size)): kept STAGE3_S

    def _text(self, url: str, what: str) -> str:
        """`url` read; WslError in words when it cannot be (the setup reports a WslError as its step failing, where
        anything else escaped it bare: "HTTPError: HTTP Error 404: Not Found")."""
        try:
            return (self._read or _read_text)(url)
        except Exception as e:  # noqa: BLE001 - offline, a 404, a timeout: said
            raise WslError(f"{what} could not be read ({url}): {e}") from e

    def stage3(self) -> tuple[str, int]:
        """The latest systemd stage3 for amd64 and its size in bytes, from Gentoo's own list (no Gentoo on Microsoft's
        list: the distribution is imported from this tarball); kept STAGE3_S. The entry is found by its form: the list
        is PGP clear-signed now, and 0.4.1 took the armour's first line for the tarball's path (a 404); an older, plain
        list reads the same."""
        now = monotonic()
        if self._stage3 is not None and now - self._stage3[0] < STAGE3_S:
            return self._stage3[1]
        listing = self.BASE_URL + self.LATEST
        for line in self._text(listing, "Gentoo's list of the latest stage3").splitlines():
            m = ENTRY.match(line.strip())
            if m:
                self._stage3 = (now, (self.BASE_URL + m["path"], int(m["size"])))
                return self._stage3[1]
        raise WslError(f"Gentoo's list of the latest stage3 names no tarball ({listing})")

    def tarball_url(self) -> str:
        return self.stage3()[0]

    def tarball(self, out=None) -> Path:
        """The latest stage3 in the plugin's data folder (the library's download, once), kept only when its size is
        the one Gentoo's list gives and its SHA-256 the one Gentoo publishes beside it (`<tarball>.sha256`): otherwise
        removed, and WslError says why; the next install downloads it again. The checksum is read first: without one,
        nothing is downloaded or imported. The list's PGP signature is not checked: HTTPS to distfiles.gentoo.org and
        the SHA-256 are the check."""
        url, size = self.stage3()
        self._stage3 = (monotonic(), (url, size))  # the library's download asks tarball_url() again: this same one
        name = url.rsplit("/", 1)[-1]
        sha256 = self._published_sha256(url, name)
        try:
            path = super().tarball(out=out)
        except WslError:
            raise
        except Exception as e:  # noqa: BLE001 - offline, a 404, a timeout during the download: said, as above
            raise WslError(f"{name} could not be downloaded ({url}): {e}") from e
        if path.name != name:  # never checked against another tarball's figures
            raise WslError(f"{path.name} is not the {name} Gentoo's list gives: {_discard(path)}")
        if out is not None:
            out(f"checking {name}: its size and SHA-256 against Gentoo's\n")
        got = path.stat().st_size
        if got != size:  # a download cut short: http.client ends a short read without an error
            raise WslError(f"{name} is {got:,} bytes, not the {size:,} Gentoo's list gives: {_discard(path)}")
        if _sha256(path) != sha256:
            raise WslError(f"{name}'s SHA-256 is not the one Gentoo publishes in {url}.sha256: {_discard(path)}")
        if out is not None:
            out(f"checked {name}: {size:,} bytes and SHA-256 {sha256[:16]}..., as Gentoo publishes them\n")
        return path

    def _published_sha256(self, url: str, name: str) -> str:
        """The SHA-256 Gentoo publishes for `name`, from `<url>.sha256` (WslError: unread, or naming no `name`)."""
        sums = url + ".sha256"
        for line in self._text(sums, f"Gentoo's SHA-256 of {name}").splitlines():
            m = DIGEST.match(line.strip())
            if m and m["name"].rsplit("/", 1)[-1] == name:
                return m["sha256"].lower()
        raise WslError(f"{sums} gives no SHA-256 for {name}: nothing is downloaded or imported unchecked")


MACHINE = WslGentooPlugin()
