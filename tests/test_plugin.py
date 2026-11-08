"""WSL Gentoo: the distribution it names, its family, its variables, its engine as a Docker instance, all
through a stand-in wsl command (nothing runs here)."""
from __future__ import annotations

import hashlib
from urllib.error import HTTPError

import pytest

import plugin_platform_wsl_gentoo as plugin
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


BASE = "https://distfiles.gentoo.org/releases/amd64/autobuilds/"
BUILD = "20261108T170107Z/stage3-amd64-systemd-20261108T170107Z.tar.xz"  # the latest on 2026-11-08
NAME = BUILD.split("/")[1]
TARBALL = b"a stage3 stand-in\n" * 4096  # 73,728 bytes


def signed(body: str) -> str:
    """`body` clear-signed, as Gentoo signs its list and its checksums (recorded 2026-11-08, the signature cut short)."""
    return ("-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA256\n\n" + body + "-----BEGIN PGP SIGNATURE-----\n\n"
            "iQFPBAEBCAA5FiEEU05CCatJ7uHBnZYWLERpXbn2BD0FAmrw9dAbFIAAAAAABAAO\n"
            "bWFudTIsMi41KzEuMTIsMiwyAAoJECxEaV259gQ9JIAH/RgwS4lRK3ce465T0R5R\n=C2st\n-----END PGP SIGNATURE-----\n")


def latest(size: int) -> str:
    """Gentoo's list of the latest stage3 as it reads now: its one entry, clear-signed."""
    return signed(f"# Latest as of Sun, 08 Nov 2026 22:15:00 +0000\n# ts=1794176100\n{BUILD} {size}\n")


class Gentoo:
    """distfiles.gentoo.org, stood in for: the list, the tarball's .sha256 (`sums`: True, Gentoo's; False, none; or the
    text given), and the download (`wrote`: what a download leaves; the tarball, unless a test cuts or changes it;
    `fails`: the download answers 404)."""

    def __init__(self, tarball=TARBALL, wrote=None, sums=True, fails=False):
        self.pages = {BASE + "latest-stage3-amd64-systemd.txt": latest(len(tarball))}
        if sums is True:
            sums = signed(f"# SHA256 HASH\n{hashlib.sha256(tarball).hexdigest()}  {NAME}\n")
        if sums:
            self.pages[BASE + BUILD + ".sha256"] = sums
        self.wrote = tarball if wrote is None else wrote
        self.fails = fails
        self.reads, self.fetched = [], []

    def read(self, url):  # the plugin's `read`
        self.reads.append(url)
        if url not in self.pages:
            raise HTTPError(url, 404, "Not Found", None, None)
        return self.pages[url]

    def fetch(self, url, path):  # the library's `fetch`: the download
        self.fetched.append(url)
        if self.fails:
            raise HTTPError(url, 404, "Not Found", None, None)
        path.write_bytes(self.wrote)

    def plugin(self, data=None):
        return WslGentooPlugin(wsl=Wsl(runner=FakeWsl()), data=data, fetch=self.fetch, read=self.read)


def test_gentoos_tarball_is_the_latest_stage3_from_its_own_list():
    """The 0.4.1 install stopped at a 404 (the user, 2026-11-08: "gentoo wsl install is reporting a 404 error for the
    installer"): Gentoo's list is PGP clear-signed now, and its armour's first line was taken for the tarball's path.
    The entry is found by its form, in the signed list and in the older plain one; a list naming none, or not read, is
    said in words."""
    p = WslGentooPlugin(wsl=Wsl(runner=FakeWsl()), read=lambda url: latest(280639788))
    assert p.stage3() == (BASE + BUILD, 280639788) and p.tarball_url() == BASE + BUILD
    assert p.install_name == "" and p.family == "emerge"
    plain = ("# Latest as of Sun, 02 Nov 2025 16:53:11 +0000\n# ts=1762102391\n"
             "20251102T165311Z/stage3-amd64-systemd-20251102T165311Z.tar.xz 311264512\n")
    p = WslGentooPlugin(wsl=Wsl(runner=FakeWsl()), read=lambda url: plain)
    assert p.stage3() == (BASE + "20251102T165311Z/stage3-amd64-systemd-20251102T165311Z.tar.xz", 311264512)
    for nothing in ("# nothing\n", signed("# Latest as of Sun, 08 Nov 2026 22:15:00 +0000\n")):
        with pytest.raises(WslError, match="names no tarball"):
            WslGentooPlugin(wsl=Wsl(runner=FakeWsl()), read=lambda url: nothing).tarball_url()  # noqa: B023
    gone = Gentoo()
    gone.pages.clear()
    with pytest.raises(WslError, match=r"list of the latest stage3 could not be read \(https://.*\): HTTP Error 404"):
        gone.plugin().tarball_url()
    ok, why = gone.plugin().source_check()  # the check before an install says it, and Install stays locked
    assert not ok and "HTTP Error 404" in why


def test_gentoos_list_is_kept_five_minutes_then_read_again(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(plugin, "monotonic", lambda: now[0])
    g = Gentoo()
    p = g.plugin()
    assert p.tarball_url() == p.tarball_url() == BASE + BUILD and len(g.reads) == 1
    now[0] += plugin.STAGE3_S - 1
    assert p.stage3() == (BASE + BUILD, len(TARBALL)) and len(g.reads) == 1
    now[0] += 2
    p.stage3()
    assert len(g.reads) == 2


def test_the_stage3_is_kept_only_with_the_size_and_sha256_gentoo_publishes(tmp_path):
    """Downloaded once into the data folder; its size checked against the list's and its SHA-256 against the one Gentoo
    publishes beside it (its .sha256), said on the platform's terminal panel; checked again before each import."""
    g, said = Gentoo(), []
    p = g.plugin(tmp_path)
    path = p.tarball(out=said.append)
    assert path == tmp_path / NAME and path.read_bytes() == TARBALL and g.fetched == [BASE + BUILD]
    assert said[0].startswith(f"checking {NAME}") and said[-1].startswith(f"checked {NAME}: 73,728 bytes")
    assert p.tarball() == path and g.fetched == [BASE + BUILD] and g.reads.count(BASE + BUILD + ".sha256") == 2


@pytest.mark.parametrize("gentoo, fetched, words", [
    pytest.param(Gentoo(wrote=TARBALL[:-4096]), 1, "is 69,632 bytes, not the 73,728 Gentoo's list gives", id="cut-short"),
    pytest.param(Gentoo(wrote=TARBALL.replace(b"stand-in", b"stand-by")), 1, "SHA-256 is not the one Gentoo publishes",
                 id="changed"),
    pytest.param(Gentoo(fails=True), 1, r"could not be downloaded \(https://.*\.tar\.xz\): HTTP Error 404", id="download-404"),
    pytest.param(Gentoo(sums=False), 0, r"SHA-256 of .* could not be read \(.*\.sha256\): HTTP Error 404", id="no-checksum"),
    pytest.param(Gentoo(sums=signed(f"# SHA256 HASH\n{'0' * 64}  stage3-amd64-openrc-20261108T170107Z.tar.xz\n")), 0,
                 "gives no SHA-256 for stage3-amd64-systemd", id="another-files-checksum"),
])
def test_a_stage3_not_as_gentoo_publishes_it_is_never_kept_and_the_install_says_why(tmp_path, gentoo, fetched, words):
    """Fail closed: a download cut short, changed or failing is not kept, one with no checksum to check it by is not
    even downloaded, and WslError says why."""
    with pytest.raises(WslError, match=words):
        gentoo.plugin(tmp_path).tarball()
    assert len(gentoo.fetched) == fetched and list(tmp_path.iterdir()) == []


def test_a_bad_stage3_left_from_before_is_removed_and_the_next_install_downloads_it_again(tmp_path):
    """One already in the data folder is checked too: cut short (http.client ends a short read without an error, and
    the library's download renames it whole), it is removed, and the next install downloads it again."""
    g = Gentoo()
    (tmp_path / NAME).write_bytes(TARBALL[:100])
    p = g.plugin(tmp_path)
    with pytest.raises(WslError, match="it is removed, and the next install downloads it again"):
        p.tarball()
    assert g.fetched == [] and not (tmp_path / NAME).exists()
    assert p.tarball().read_bytes() == TARBALL and g.fetched == [BASE + BUILD]


def test_the_install_imports_only_a_checked_stage3_and_says_why_not(tmp_path):
    """The setup's distribution step, as the platform's Install runs it: a checked stage3 imported (wsl --import); a
    check failing ends the step in words, where 0.4.1's HTTPError escaped the setup bare."""
    fake, g = FakeWsl(), Gentoo()
    p = WslGentooPlugin(wsl=Wsl(runner=fake), data=tmp_path, fetch=g.fetch, read=g.read)
    (done,) = p.setup(log=lambda m: None, steps=["distribution"])
    assert done["ok"] is True and NAME in done["detail"]
    assert ["wsl", "--import", p.distribution_name, str(tmp_path / "root"), str(tmp_path / NAME), "--version", "2"] in fake.calls
    bad = Gentoo(sums=False)
    q = WslGentooPlugin(wsl=Wsl(runner=FakeWsl()), data=tmp_path / "again", fetch=bad.fetch, read=bad.read)
    (done,) = q.setup(log=lambda m: None, steps=["distribution"])
    assert done == {"step": "distribution", "ok": False, "detail": done["detail"]} and "HTTP Error 404" in done["detail"]
    assert bad.fetched == []


def test_it_checks_this_pc_updates_its_packages_and_opens_a_terminal():
    """liminal-libs 1.26.0: the check before the install, the packages' update, the login terminal."""
    assert {"check", "update_packages", "terminal"} <= set(MACHINE.interface()["hooks"])
    assert MACHINE.space_gb == 20.0 and MACHINE.architectures == ("AMD64", "x86_64")
