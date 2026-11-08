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

import os

from liminal_libs.machines.wsl import WslDistribution, WslError

__version__ = "0.3.0"


def _read_text(url: str) -> str:
    import urllib.request

    with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 - the plugin's own url
        return r.read().decode("utf-8", "replace")


class WslGentooPlugin(WslDistribution):
    name = "wsl-gentoo"
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
        self._read = read  # (url) -> text: Gentoo's list of the latest stage3, urllib unless given

    def tarball_url(self) -> str:
        """The latest systemd stage3 for amd64, from Gentoo's own list (no Gentoo on Microsoft's list: the
        distribution is imported from this tarball)."""
        text = (self._read or _read_text)(self.BASE_URL + self.LATEST)
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return self.BASE_URL + line.split()[0]
        raise WslError("Gentoo's list of the latest stage3 is empty")


MACHINE = WslGentooPlugin()
