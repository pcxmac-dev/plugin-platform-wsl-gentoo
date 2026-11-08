"""WSL Gentoo: the distribution it names, its family, its variables, its engine as a Docker instance, all
through a stand-in wsl command (nothing runs here)."""
from __future__ import annotations

import pytest

from liminal_libs.machines.wsl import Wsl, WslError  # noqa: F401
from plugin_platform_wsl_gentoo import MACHINE, WslGentooPlugin


def u16(text):
    return text.encode("utf-16-le")


class FakeWsl:
    def __init__(self, distributions=(), online=("Ubuntu", "FedoraLinux-42"), docker=False):
        self.distributions = list(distributions)
        self.online = list(online)
        self.docker = docker
        self.calls = []

    def __call__(self, args, timeout):
        self.calls.append(list(args))
        if args[1] == "--status":
            return 0, u16("Default Distribution: Ubuntu\r\nDefault Version: 2\r\n"), b""
        if args[1:3] == ["--list", "--verbose"]:
            return 0, u16("  NAME STATE VERSION\r\n" + "".join(f"  {n} {s} {v}\r\n" for n, s, v in self.distributions)), b""
        if args[1:3] == ["--list", "--online"]:
            return 0, u16("NAME FRIENDLY\r\n" + "".join(f"{n} x\r\n" for n in self.online)), b""
        if args[1] == "-d":
            command = args[args.index("--exec") + 1:]
            if command[:2] == ["docker", "--version"]:
                return (0, b"Docker version 28.1.1, build x\n", b"") if self.docker else (127, b"", b"not found")
            if command[:2] == ["docker", "info"]:
                return (0, b"28.1.1\n", b"") if self.docker else (1, b"", b"no daemon")
            return 0, (" ".join(command) + "\n").encode(), b""
        return 0, u16("ok"), b""


def test_the_plugin_names_its_distribution_and_offers_its_engine(monkeypatch):
    monkeypatch.delenv("WSL_GENTOO_DISTRIBUTION", raising=False)
    monkeypatch.delenv("WSL_GENTOO_USER", raising=False)
    assert MACHINE.name == "wsl-gentoo" and MACHINE.family == "emerge" and MACHINE.SYSTEM == "platform" and MACHINE.KIND == "machine"
    assert MACHINE.options == ("WSL_GENTOO_DISTRIBUTION", "WSL_GENTOO_USER") and MACHINE.user == "liminal"
    fake = FakeWsl(distributions=[("Liminal-Gentoo", "Running", "2")], docker=True)
    p = WslGentooPlugin(wsl=Wsl(runner=fake))
    assert p.present() and p.status()["engine"]["installed"] and p.status()["family"] == "emerge"
    assert "services" in p.interface()["hooks"] and p.status()["services"]["scanned"] is False  # the stand-in answers no scan: said
    (inst,) = p.instances()
    assert inst.name == "wsl-gentoo" and inst.command == f"wsl -d {p.distribution_name} --exec docker" and inst.translate("C:\\\\x") == "/mnt/c/x"
    assert p.run("echo", "hi") == "echo hi\n"
    assert WslGentooPlugin(wsl=Wsl(runner=FakeWsl())).instances() == ()
    assert MACHINE.distribution == "Liminal-Gentoo" and p.status()["valid"] is True
    assert WslGentooPlugin(wsl=Wsl(runner=FakeWsl(distributions=[("Gentoo", "Running", "2")]))).status()["valid"] is False


def test_gentoos_tarball_is_the_latest_stage3_from_its_own_list():
    listing = "# Latest as of Sun, 02 Nov 2025 16:53:11 +0000\n# ts=1762102391\n20251102T165311Z/stage3-amd64-systemd-20251102T165311Z.tar.xz 311264512\n"
    p = WslGentooPlugin(wsl=Wsl(runner=FakeWsl()), read=lambda url: listing)
    assert p.tarball_url() == "https://distfiles.gentoo.org/releases/amd64/autobuilds/20251102T165311Z/stage3-amd64-systemd-20251102T165311Z.tar.xz"
    assert p.install_name == "" and p.family == "emerge"
    with pytest.raises(WslError):
        WslGentooPlugin(wsl=Wsl(runner=FakeWsl()), read=lambda url: "# nothing\n").tarball_url()


def test_it_checks_this_pc_updates_its_packages_and_opens_a_terminal():
    """liminal-libs 1.26.0: the check before the install, the packages' update, the login terminal."""
    assert {"check", "update_packages", "terminal"} <= set(MACHINE.interface()["hooks"])
    assert MACHINE.space_gb == 20.0 and MACHINE.architectures == ("AMD64", "x86_64")
