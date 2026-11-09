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


# -- 0.4.3: its boot under systemd set right, and a lookup checked before anything is downloaded inside ---------------
# What Liminal-Gentoo's two scripts print, as the stand-in answers them: the systemd step's, a lookup that works through
# WSL's /etc/resolv.conf, and a first boot's state (the stage3 ships no /etc/machine-id: systemd turned on its presets,
# systemd-resolved among them, and /etc/nsswitch.conf asks it first).
SYSTEMD_SAID = "machine-id: made\nmasked: systemd-resolved systemd-networkd\nhosts: files myhostname dns\nliminal-systemd: ready\n"
FOUND = ("lookup: ok 151.101.2.132\nresolv: link /mnt/wsl/resolv.conf\nnameserver: 10.255.255.254\n"
         "hosts: files myhostname dns\nsystemd: running\n")
FIRST_BOOT = ("lookup: failed\nresolv: link /mnt/wsl/resolv.conf\nnameserver: 10.255.255.254\n"
              "hosts: mymachines resolve [!UNAVAIL=return] files myhostname dns\nsystemd: starting\nresolved: listening\n")


@pytest.fixture(autouse=True)
def _its_own_names(monkeypatch):
    monkeypatch.delenv("WSL_GENTOO_DISTRIBUTION", raising=False)
    monkeypatch.delenv("WSL_GENTOO_USER", raising=False)


class GentooWsl(FakeWsl):
    """The stand-in wsl, with Liminal-Gentoo's answers to the plugin's two scripts (told apart by their argument)."""

    def __init__(self, dns=FOUND, systemd=SYSTEMD_SAID, **kw):
        super().__init__(**kw)
        self.dns, self.systemd = dns, systemd

    def __call__(self, args, timeout):
        said = {"liminal-dns": self.dns, "liminal-systemd": self.systemd}.get(args[-1]) if args[1] == "-d" else None
        if said is not None:
            self.calls.append(list(args))
            return 0, said.encode(), b""
        return super().__call__(args, timeout)


INSTALLED = [("Liminal-Gentoo", "Running", "2")]
ROOT = ["wsl", "-d", "Liminal-Gentoo", "-u", "root", "--exec"]


def test_its_steps_set_systemd_right_before_the_restart_into_it_and_look_up_a_name_after():
    assert MACHINE.STEPS == ("wsl", "update", "version", "distribution", "systemd", "conf", "dns", "docker", "engine", "user")


def test_setting_up_again_finishes_a_half_installed_gentoo_without_downloading_it_again(tmp_path):
    """The 2026-11-08 install stopped in its docker step: every lookup inside waited until wget gave up ("wget: unable
    to resolve host address 'distfiles.gentoo.org'"), for two hours. Run again (the platform's Set up, Everything), the
    distribution step finds Liminal-Gentoo installed and nothing is downloaded: the systemd step sets its boot right
    and restarts it, the conf step restarts it into systemd, the lookup is checked, then Docker is installed."""
    fake, g = GentooWsl(distributions=INSTALLED), Gentoo()
    p = WslGentooPlugin(wsl=Wsl(runner=fake), data=tmp_path, fetch=g.fetch, read=g.read)
    done = p.setup(log=lambda m: None)
    assert [d["step"] for d in done] == list(plugin.STEPS) and all(d["ok"] is not False for d in done), done
    assert done[3] == {"step": "distribution", "ok": None, "detail": "Liminal-Gentoo is installed"}
    assert g.reads == [] and g.fetched == []  # neither Gentoo's list nor its 268 MB stage3

    def at(command, after=-1):
        return next(i for i, c in enumerate(fake.calls) if i > after and c == command)

    s = at(ROOT + ["sh", "-s", "liminal-systemd"])
    t = at(["wsl", "--terminate", "Liminal-Gentoo"], s)  # restarted with its machine ID: no boot is systemd's first
    c = at(ROOT + ["sh", "-c", "cat > /etc/wsl.conf"], t)
    d = at(ROOT + ["sh", "-s", "liminal-dns"], c)
    assert at(ROOT + ["sh", "-s"], d) > d  # Docker's emerge only after the lookup
    assert done[4]["detail"].startswith("Liminal-Gentoo boots as WSL needs: its machine ID made, so no boot is systemd's first")
    assert "systemd-resolved and systemd-networkd masked" in done[4]["detail"] and done[4]["detail"].endswith("Liminal-Gentoo restarted")
    assert done[6]["detail"] == ("Liminal-Gentoo looks up distfiles.gentoo.org (151.101.2.132) through /etc/resolv.conf "
                                 "(WSL's, a link to /mnt/wsl/resolv.conf; nameserver 10.255.255.254)")


def test_a_lookup_that_fails_ends_the_install_before_anything_is_downloaded_inside_and_says_why():
    fake = GentooWsl(dns=FIRST_BOOT, distributions=INSTALLED)
    p = WslGentooPlugin(wsl=Wsl(runner=fake))
    (done,) = p.setup(log=lambda m: None, steps=["dns", "docker", "engine"])
    assert done["step"] == "dns" and done["ok"] is False
    assert done["detail"] == (
        "Liminal-Gentoo cannot look up distfiles.gentoo.org, so nothing is downloaded inside it: its lookups go to "
        "systemd-resolved first (/etc/nsswitch.conf: hosts: mymachines resolve [!UNAVAIL=return] files myhostname dns), "
        "and it does not answer; systemd has not finished booting (starting). Its systemd step sets Liminal-Gentoo "
        "right: run the setup again (an installed Liminal-Gentoo is not downloaded again).")
    assert ROOT + ["sh", "-s"] not in fake.calls  # no emerge, no engine


@pytest.mark.parametrize("facts, words, ours", [
    pytest.param("lookup: failed\nresolv: dangling ../run/systemd/resolve/stub-resolv.conf\nhosts: files myhostname dns\n"
                 "systemd: running\n", "its /etc/resolv.conf is a link to ../run/systemd/resolve/stub-resolv.conf, "
                 "which does not exist", True, id="resolved-stub-link"),
    pytest.param("lookup: failed\nresolv: missing\nhosts: files myhostname dns\nsystemd: running\ngenerate: off\n",
                 "it has no /etc/resolv.conf: its /etc/wsl.conf turns WSL's off (generateResolvConf = false)", False,
                 id="wsl-conf-turns-it-off"),
    pytest.param("lookup: failed\nresolv: file\nhosts: files myhostname dns\nsystemd: degraded\n",
                 "its /etc/resolv.conf names no DNS server", False, id="no-server"),
    pytest.param("lookup: failed\nresolv: link /mnt/wsl/resolv.conf\nnameserver: 10.255.255.254\nhosts: files myhostname dns\n"
                 "systemd: running\n", "the DNS server WSL gives it (10.255.255.254) does not answer: Windows' own "
                 "network, a VPN, or WSL's DNS (dnsTunneling in .wslconfig) is where to look", False, id="server-silent"),
    pytest.param("lookup: failed\nresolv: link /mnt/wsl/resolv.conf\nnameserver: 10.255.255.254\nhosts: files myhostname dns\n"
                 "systemd:\n", "systemd has not finished booting (it does not say how far it has got)", True,
                 id="boot-unfinished"),
])
def test_a_lookup_that_fails_is_said_plainly(facts, words, ours):
    p = WslGentooPlugin(wsl=Wsl(runner=GentooWsl(dns=facts, distributions=INSTALLED)))
    with pytest.raises(WslError) as e:
        p.lookup()
    said = str(e.value)
    assert said.startswith("Liminal-Gentoo cannot look up distfiles.gentoo.org") and words in said
    assert ("Its systemd step sets Liminal-Gentoo right" in said) is ours


def test_the_systemd_step_keeps_a_first_boots_machine_id_and_removes_a_stale_resolv_conf():
    systemd = ("machine-id: committed\nmasked: systemd-resolved systemd-networkd\nresolv: removed "
               "../run/systemd/resolve/stub-resolv.conf\nhosts: files myhostname dns\nliminal-systemd: ready\n")
    fake = GentooWsl(systemd=systemd, distributions=INSTALLED)
    (done,) = WslGentooPlugin(wsl=Wsl(runner=fake)).setup(log=lambda m: None, steps=["systemd"])
    assert done["ok"] is True and "its machine ID kept from its first boot" in done["detail"]
    assert "a stale /etc/resolv.conf removed (a link to ../run/systemd/resolve/stub-resolv.conf)" in done["detail"]
    assert fake.calls[-2:] == [ROOT + ["sh", "-s", "liminal-systemd"], ["wsl", "--terminate", "Liminal-Gentoo"]]


def test_its_own_steps_change_nothing_in_a_distribution_not_liminals_nor_in_one_not_there(monkeypatch):
    (done,) = WslGentooPlugin(wsl=Wsl(runner=GentooWsl())).setup(log=lambda m: None, steps=["dns"])
    assert done == {"step": "dns", "ok": False, "detail": "Liminal-Gentoo is not installed: its distribution step installs it"}
    monkeypatch.setenv("WSL_GENTOO_DISTRIBUTION", "Gentoo")
    fake = GentooWsl(distributions=[("Gentoo", "Running", "2")])
    (done,) = WslGentooPlugin(wsl=Wsl(runner=fake)).setup(log=lambda m: None, steps=["systemd"])
    assert done["ok"] is False and done["detail"].startswith("Gentoo is not one of Liminal's own distributions (Liminal-...)")
    assert fake.calls == []  # not even asked what is installed


def test_the_scripts_set_the_boot_right_by_files_alone_and_look_up_with_a_time_limit():
    s = plugin.SYSTEMD_SCRIPT
    assert s.startswith("set -e\n") and "systemctl" not in s  # asks systemd nothing: works whether it runs or not
    assert "systemd-machine-id-setup --commit" in s and "tr -d '-' < /proc/sys/kernel/random/uuid > /etc/machine-id" in s
    for unit in ("systemd-resolved.service", "systemd-resolved-varlink.socket", "systemd-resolved-monitor.socket",
                 "systemd-networkd.service"):
        assert unit in s.split('ln -sfn /dev/null "$unit"')[0].rsplit("for unit in", 1)[1]  # masked
    assert "ln -sfn /dev/null /etc/tmpfiles.d/systemd-resolve.conf" in s and "hosts:      files myhostname dns" in s
    d = plugin.DNS_SCRIPT
    assert d.startswith("host=distfiles.gentoo.org\n") and "timeout 15 getent ahosts" in d and d.rstrip().endswith("exit 0")
    assert plugin._facts("lookup: ok 1.2.3.4\nnameserver: 10.0.0.1\nnameserver: fe80::1%eth0\nhosts:\nnoise\n") == {
        "lookup": "ok 1.2.3.4", "nameserver": ["10.0.0.1", "fe80::1%eth0"], "hosts": ""}


def test_the_docker_install_and_the_packages_update_look_up_first():
    guard, _, recipe = MACHINE.install_script().partition("fi\n")
    assert guard.startswith("if ! timeout 30 getent ahosts distfiles.gentoo.org >/dev/null 2>&1; then\n") and "exit 3" in guard
    assert recipe.startswith("set -e\nemerge --sync --quiet || emerge-webrsync\n") and "app-containers/docker " in recipe
    fake = GentooWsl(dns=FIRST_BOOT, distributions=INSTALLED)
    p = WslGentooPlugin(wsl=Wsl(runner=fake))
    (done,) = p.update_packages(log=lambda m: None)
    assert done["step"] == "packages" and done["ok"] is False and "cannot look up distfiles.gentoo.org" in done["detail"]
    assert ROOT + ["sh", "-s"] not in fake.calls
    fake.dns = FOUND
    (done,) = p.update_packages(log=lambda m: None)
    assert done["ok"] is True and ROOT + ["sh", "-s"] in fake.calls
