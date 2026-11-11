"""What WSL Gentoo attaches to (plugin API 2.2): its cards are sound; they name every wsl command the plugin sends (the
plugin driven through a stand-in PC and a stand-in distfiles.gentoo.org over its whole setup and every task), the
commands its scripts run inside and the files it reads of Gentoo's; its facts are what it kept, asked without a
command; and the cards' pages answer (LIMINAL_VENDOR_PAGES=1 only, the one test that reaches the network)."""
from __future__ import annotations

import hashlib
import os
import re

import pytest

from liminal_libs.machines.wsl import Wsl
from liminal_libs.sources.apis import dead_links, problems
from plugin_platform_wsl_gentoo import MACHINE, WslGentooPlugin
from plugin_platform_wsl_gentoo import apis as cards

OWN, YOURS = "Liminal-Gentoo", "Gentoo"
BASE = "https://distfiles.gentoo.org/releases/amd64/autobuilds/"
BUILD = "20261108T170107Z/stage3-amd64-systemd-20261108T170107Z.tar.xz"
NAME = BUILD.split("/")[1]
TARBALL = b"a stage3 stand-in\n" * 4096
SCAN = ("== liminal-scan 1\n== init systemd systemd\n== units\n"
        "docker.service loaded active running Docker Application Container Engine\n"
        "== memory\nId=docker.service\nMainPID=120\nMemoryCurrent=52428800\n\n== processes\n  1 9000 systemd /sbin/init\n== end\n")


def u16(text: str) -> bytes:
    return text.encode("utf-16-le")


class Distfiles:
    """distfiles.gentoo.org, stood in for: the list of the latest stage3, the tarball's .sha256, the tarball."""

    def __init__(self):
        self.asked: list[str] = []

    def read(self, url):
        self.asked.append(url)
        if url == BASE + "latest-stage3-amd64-systemd.txt":
            return f"# Latest as of Sun, 08 Nov 2026\n{BUILD} {len(TARBALL)}\n"
        if url == BASE + BUILD + ".sha256":
            return f"# SHA256 HASH\n{hashlib.sha256(TARBALL).hexdigest()}  {NAME}\n"
        raise AssertionError(f"not Gentoo's: {url}")

    def fetch(self, url, path):
        self.asked.append(url)
        path.write_bytes(TARBALL)


class Pc:
    """WSL on a stand-in PC: wsl's own commands answered from what is installed (an import adds one, an unregister
    removes it, a terminate stops it, a command inside starts it), Docker there once it is built, the scripts answered
    as Gentoo's would be. Every command is kept (`calls`), with what was given on its standard input."""

    def __init__(self):
        self.wsl = False
        self.installed = {YOURS: "Stopped"}
        self.docker = False
        self.calls: list[list[str]] = []
        self.inputs: list[str] = []
        self.stdin = None

    def records(self):
        return [{"guid": "{%d}" % i, "DistributionName": n, "Flavor": "gentoo", "OsVersion": "2.18", "Version": 2}
                for i, n in enumerate(self.installed)]

    def rename(self, key, name):
        old = next(n for i, n in enumerate(self.installed) if "{%d}" % i == key)
        self.installed = {(name if n == old else n): s for n, s in self.installed.items()}

    def spawn(self, args):
        self.calls.append(list(args))
        self.installed[args[2]] = "Running"
        return type("Session", (), {"poll": lambda self: 0})()

    def __call__(self, args, timeout):
        args = list(args)
        self.calls.append(args)
        stdin, self.stdin = self.stdin, None
        self.inputs.append(stdin or "")
        if args[1] == "--status":
            return (0, u16("Default Distribution: Gentoo\r\nDefault Version: 2\r\n"), b"") if self.wsl else (1, b"", u16("no WSL"))
        if args[1:3] == ["--install", "--no-distribution"]:
            self.wsl = True
        elif args[1] == "--version":
            return 0, u16("WSL version: 2.6.3.0\r\nKernel version: 6.6.87.2-1\r\n"), b""
        elif args[1:3] == ["--list", "--verbose"]:
            rows = "".join(f"  {n} {s} 2\r\n" for n, s in self.installed.items())
            return 0, u16("  NAME STATE VERSION\r\n" + rows), b""
        elif args[1] == "--import":
            self.installed[args[2]] = "Stopped"
        elif args[1] == "--terminate":
            self.installed[args[2]] = "Stopped"
        elif args[1] == "--unregister":
            self.installed.pop(args[2], None)
        elif args[1] == "-d":
            self.installed[args[2]] = "Running"
            command = args[args.index("--exec") + 1:]
            if "app-containers/docker" in (stdin or ""):
                self.docker = True
            if command[:2] == ["docker", "--version"]:
                return (0, b"Docker version 28.5.2, build x\n", b"") if self.docker else (127, b"", b"docker: not found")
            if command[:2] == ["docker", "info"]:
                return (0, b"28.5.2\n", b"") if self.docker else (1, b"", b"no daemon")
            if "liminal-scan" in command:
                return 0, SCAN.encode(), b""
            if "liminal-systemd" in command:
                return 0, b"machine-id: made\nmasked: systemd-resolved systemd-networkd\nhosts: files myhostname dns\nliminal-systemd: ready\n", b""
            if "liminal-dns" in command:
                return 0, b"lookup: ok 151.101.2.132\nresolv: link /mnt/wsl/resolv.conf\nnameserver: 10.255.255.254\nsystemd: running\n", b""
            if command[:2] == ["sh", "-c"] and "systemctl freeze" in command[2]:
                return 0, b"frozen nginx.service\n", b""
            if command[:2] == ["sh", "-c"] and "systemctl thaw" in command[2]:
                return 0, b"thawed nginx.service\n", b""
            if "systemctl enable --now docker" in (stdin or ""):
                return 0, b"systemd\n", b""
            return 0, b"", b""
        return 0, u16("ok\r\n"), b""


class Recording(Wsl):
    """The library's Wsl over the stand-in PC, the PC told what each command is given on its standard input."""

    def __init__(self, pc: Pc):
        super().__init__(runner=pc, registry=pc.records, spawn=pc.spawn, rename=pc.rename)
        self.pc = pc
        self.read_registry = self.set_registry = 0
        reader = self._registry

        def counted():
            self.read_registry += 1
            return reader()
        self._registry = counted

    def run(self, name, *command, user=None, stdin=None, timeout=600.0, out=None):
        self.pc.stdin = stdin
        return super().run(name, *command, user=user, stdin=stdin, timeout=timeout, out=out)

    def rename(self, key, name):
        self.set_registry += 1
        super().rename(key, name)


def call_of(args: list[str]) -> str:
    """A wsl command as the WSL card names it."""
    if args[1] != "-d":
        if args[1] == "--import":
            return "wsl --import <distribution> <folder> <file> --version 2"
        if args[1] in ("--terminate", "--unregister"):
            return f"wsl {args[1]} <distribution>"
        return " ".join(args)
    rest, user = args[3:], ""
    if rest[:1] == ["-u"]:
        user, rest = f" -u {rest[1]}", rest[2:]
    if rest[:2] == ["--cd", "~"]:
        return f"wsl -d <distribution>{user} --cd ~ --exec sh -c <login shell>"
    command = rest[rest.index("--exec") + 1:]
    if command[0] == "docker":
        return f"wsl -d <distribution>{user} --exec docker"
    if command[:2] == ["sh", "-s"]:
        return f"wsl -d <distribution>{user} --exec sh -s"
    if command[:2] == ["sh", "-c"]:
        return cards.KEEP_RUNNING if "sleep 3600" in command[2] else f"wsl -d <distribution>{user} --exec sh -c"
    return f"wsl -d <distribution>{user} --exec <command>"


def drive(tmp_path, monkeypatch):
    """The plugin over the stand-in PC and distfiles through everything it does: the check, the whole setup (its own
    systemd and dns steps too), the status, the instance, a command, the terminal, and every task on an install (start,
    pause, resume, stop, update, rename, uninstall); what it sent, and what it read of Gentoo's."""
    monkeypatch.delenv("WSL_GENTOO_DISTRIBUTION", raising=False)
    monkeypatch.delenv("WSL_GENTOO_USER", raising=False)
    monkeypatch.setattr("liminal_libs.machines.wsl.time.sleep", lambda s: None)
    pc, gentoo = Pc(), Distfiles()
    wsl = Recording(pc)
    p = WslGentooPlugin(wsl=wsl, data=tmp_path, fetch=gentoo.fetch, read=gentoo.read)
    p._system = lambda: {"windows": True, "build": 26300, "machine": "AMD64"}
    p._free = lambda path: 100 * 2**30
    p.check()
    done = p.setup(log=lambda m: None)
    assert [d["step"] for d in done] == list(p.STEPS) and all(d["ok"] is not False for d in done), done
    assert p.check()["installed"] and p.status()["engine"]["running"]
    assert p.instances() and p.run("echo", "hi") == ""
    terminal = p.terminal()
    p.pick_install(YOURS)
    assert p.start_install(YOURS)["ok"] and p.pause_install(YOURS)["ok"] and p.start_install(YOURS)["ok"]
    assert p.stop_install(YOURS)["ok"]
    p.pick_install(OWN)
    assert p.update_packages(log=lambda m: None)[-1]["ok"]
    assert p.rename_install(YOURS, "Gentoo-Work")["ok"]
    assert p.uninstall("Gentoo-Work", accept_risk=True)["ok"]
    return p, pc, wsl, terminal, gentoo


def test_the_cards_are_sound_and_each_says_where_its_documentation_is():
    assert problems(MACHINE.apis) == [] and MACHINE.apis == cards.APIS
    assert [a.name for a in MACHINE.apis] == ["WSL (wsl.exe)", "Gentoo's stage3 releases", "Portage (Gentoo's emerge)",
                                              "Docker (Gentoo's packages)", "systemd (the install's init)"]
    assert all(a.docs and a.verified == "2026-11-11" and a.used and a.covered for a in MACHINE.apis)
    assert all(len(a.areas) > len(a.covered) for a in MACHINE.apis)  # more of each API than the plugin uses
    assert cards.STAGE3.base == WslGentooPlugin.BASE_URL and cards.STAGE3.link("source") == WslGentooPlugin.BASE_URL
    assert cards.DOCKER_ENGINE.docs == "https://wiki.gentoo.org/wiki/Docker"  # Docker has no Gentoo page: Gentoo's is the guide
    assert not any(c.costs for a in MACHINE.apis for c in a.calls)  # nothing here costs money


def test_the_wsl_card_names_every_command_the_plugin_sends_and_nothing_it_does_not(tmp_path, monkeypatch):
    p, pc, wsl, terminal, gentoo = drive(tmp_path, monkeypatch)
    sent = {call_of(a) for a in pc.calls} | {call_of(terminal)}
    used = {c.name for c in cards.WSL.used}
    registry = {c.name for c in cards.WSL.used if "Lxss" in c.name}
    assert sent <= used, sorted(sent - used)
    assert used - registry <= sent, sorted(used - registry - sent)
    assert wsl.read_registry and wsl.set_registry == 1  # WSL's record read, and written once (the rename)
    assert "wsl --list --online" not in sent  # Gentoo is not on Microsoft's list: never asked


def fragments(name: str) -> list[str]:
    """A call's words as they appear in a script or an address: its name without its placeholders, "GET " dropped."""
    return [f.strip() for f in re.split(r"<[^>]+>", name.removeprefix("GET ")) if f.strip()]


def test_the_cards_name_the_commands_the_plugins_scripts_run_and_the_files_it_reads(tmp_path, monkeypatch):
    p, pc, wsl, terminal, gentoo = drive(tmp_path, monkeypatch)
    texts = [*pc.inputs, *(" ".join(a) for a in pc.calls), *gentoo.asked]
    for api in (cards.STAGE3, cards.PORTAGE, cards.DOCKER_ENGINE, cards.INIT):
        for call in api.used:
            assert all(any(f in t for t in texts) for f in fragments(call.name)), f"{api.name}: {call.name} is not sent"
    assert gentoo.asked == [BASE + "latest-stage3-amd64-systemd.txt", BASE + BUILD + ".sha256", BASE + BUILD]


def test_its_facts_are_what_it_kept_and_asking_them_sends_nothing(tmp_path, monkeypatch):
    pc = Pc()
    fresh = WslGentooPlugin(wsl=Recording(pc), data=tmp_path, read=lambda url: pytest.fail("asked Gentoo"))
    assert fresh.api_facts() == {} and pc.calls == []
    p, pc, wsl, terminal, gentoo = drive(tmp_path, monkeypatch)
    before, asked = len(pc.calls), len(gentoo.asked)
    facts = p.api_facts()
    assert len(pc.calls) == before and len(gentoo.asked) == asked  # nothing asked
    assert facts["Gentoo's stage3 releases"]["Newest systemd stage3"].startswith(f"{NAME}, 0 MB, read ")
    assert facts["Docker (Gentoo's packages)"] == {"Docker inside": "28.5.2, its daemon answering (as last seen)"}
    assert facts["systemd (the install's init)"]["Init"] == "systemd (PID 1: systemd)"


@pytest.mark.skipif(os.environ.get("LIMINAL_VENDOR_PAGES") != "1", reason="reaches the makers' pages: LIMINAL_VENDOR_PAGES=1")
def test_the_cards_pages_answer():
    assert dead_links(MACHINE.apis) == []
