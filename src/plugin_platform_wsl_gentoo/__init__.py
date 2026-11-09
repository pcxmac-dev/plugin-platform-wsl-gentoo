"""WSL Gentoo for Liminal (the user, 2026-11-07: "the platform is the interface for the software/hardware
which facilitates the liminal framework"; "the scope of the plugin is setting up WSL/Ubuntu and supporting
docker for the platform"; "then create a gentoo and fedora plugin as well, same scope/function"): Gentoo
in WSL 2 on this Windows PC, set up by the plugin (WSL itself, the distribution, systemd and the default
user, Docker inside, the engine started, the user in the docker group), and its engine offered to the
framework as the Docker instance `wsl-gentoo` (liminal_libs.docker.instances). Everything is the library's
WslDistribution (liminal_libs.machines.wsl); this module says which distribution, and adds two steps of Gentoo's own
around the library's conf step: `systemd` (Liminal-Gentoo made to boot under systemd as WSL needs) and `dns` (a lookup
checked before anything is downloaded inside it).

    python -m plugin_platform_wsl_gentoo status | setup [STEP ...] | run -- COMMAND | instances
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from time import monotonic

from liminal_libs.machines.plugin import LIMINAL_PREFIX, liminal_scoped
from liminal_libs.machines.wsl import WslDistribution, WslError

__version__ = "0.8.0"

# The setup's steps: the library's, with two of Gentoo's own around its conf step (the restart into systemd). Why (the
# user, 2026-11-08: "gentoo WSL error - wget: unable to resolve host address 'distfiles.gentoo.org'"): the stage3 ships
# no /etc/machine-id, so its first boot under systemd was systemd's "first boot", which turns on every unit its presets
# name (systemd-resolved, its socket listening from the start of the boot, systemd-networkd ...) and runs the first-boot
# wizard; Gentoo's /etc/nsswitch.conf sends a lookup to systemd-resolved before /etc/resolv.conf ("resolve
# [!UNAVAIL=return]"), so each one waited on it and WSL's own /etc/resolv.conf was never read: emerge-webrsync went back
# a day at a time, each wget waiting its minute, until the docker step's two hours ran out.
STEPS = ("wsl", "update", "version", "distribution", "systemd", "conf", "dns", "docker", "engine", "user")
OWN_STEPS = ("systemd", "dns")
LOOKUP = "distfiles.gentoo.org"  # the name every download inside needs (emerge-webrsync's snapshots, the distfiles)
LOOKUP_S = 15  # a lookup is given this long, twice, before the check says it failed

# `systemd`, as root inside, by file operations only: it works whether systemd runs or not, and asks systemd nothing.
SYSTEMD_SCRIPT = r"""set -e
# A machine ID: with none (the stage3 ships none) the next boot is systemd's first, which turns on every unit the
# presets name and runs the first-boot wizard. One systemd made for a first boot (a transient one) is kept on disk.
id=kept
if mountpoint -q /etc/machine-id 2>/dev/null; then
  systemd-machine-id-setup --commit >/dev/null 2>&1 || umount /etc/machine-id
  id=committed
fi
if [ ! -s /etc/machine-id ] || grep -qx uninitialized /etc/machine-id; then
  tr -d '-' < /proc/sys/kernel/random/uuid > /etc/machine-id
  id=made
fi
echo "machine-id: $id"
# systemd-resolved and systemd-networkd masked, and what a first boot's presets enabled of theirs removed: WSL gives
# the distribution its network and its DNS server (its own /etc/resolv.conf)
mkdir -p /etc/systemd/system
cd /etc/systemd/system
for unit in systemd-resolved.service systemd-resolved-varlink.socket systemd-resolved-monitor.socket \
            systemd-networkd.service systemd-networkd.socket systemd-networkd-varlink.socket \
            systemd-networkd-varlink-metrics.socket systemd-networkd-resolve-hook.socket \
            systemd-networkd-wait-online.service systemd-network-generator.service; do
  find . -mindepth 2 -type l -name "$unit" -exec rm -f {} +
done
rm -f dbus-org.freedesktop.resolve1.service dbus-org.freedesktop.network1.service
for unit in systemd-resolved.service systemd-resolved-varlink.socket systemd-resolved-monitor.socket systemd-networkd.service; do
  ln -sfn /dev/null "$unit"
done
echo "masked: systemd-resolved systemd-networkd"
# systemd's rule linking /etc/resolv.conf to systemd-resolved's stub wherever there is none, off
mkdir -p /etc/tmpfiles.d
ln -sfn /dev/null /etc/tmpfiles.d/systemd-resolve.conf
# /etc/resolv.conf is WSL's, written at every start (a link to /mnt/wsl/resolv.conf): a link into systemd-resolved's
# folder, or one to nothing, is removed, and WSL writes its own at the next start
if [ -L /etc/resolv.conf ]; then
  target=$(readlink /etc/resolv.conf)
  case "$target" in
    *systemd/resolve/*) rm -f /etc/resolv.conf; echo "resolv: removed $target" ;;
    *) if [ ! -e /etc/resolv.conf ]; then rm -f /etc/resolv.conf; echo "resolv: removed $target"; fi ;;
  esac
fi
# Names looked up in /etc/hosts, then through /etc/resolv.conf: Gentoo's systemd default asks systemd-machined and
# systemd-resolved first, which have nothing to say in WSL, and a lookup waits on them while they cannot answer
if [ -f /etc/nsswitch.conf ] && ! grep -Eq '^hosts:[[:space:]]+files myhostname dns[[:space:]]*$' /etc/nsswitch.conf; then
  if grep -q '^hosts:' /etc/nsswitch.conf; then
    sed -i 's/^hosts:.*/# &   (before Liminal, for WSL)\nhosts:      files myhostname dns/' /etc/nsswitch.conf
  else
    echo 'hosts:      files myhostname dns' >> /etc/nsswitch.conf
  fi
fi
echo "hosts: $(awk '$1 == "hosts:" {$1 = ""; sub(/^ +/, ""); print; exit}' /etc/nsswitch.conf)"
echo "liminal-systemd: ready"
"""

# `dns`, as root inside: the lookup (twice, LOOKUP_S each), then what bears on it, one `key: value` a line; it always
# ends well, so its words are read whatever WSL itself prints.
DNS_SCRIPT = r"""host=@LOOKUP@
got=
for attempt in 1 2; do
  got=$(timeout @LOOKUP_S@ getent ahosts "$host" 2>/dev/null) && break
  got=
  sleep 3
done
if [ -n "$got" ]; then echo "lookup: ok $(echo "$got" | awk 'NR == 1 {print $1}')"; else echo "lookup: failed"; fi
if [ -L /etc/resolv.conf ]; then
  if [ -e /etc/resolv.conf ]; then echo "resolv: link $(readlink /etc/resolv.conf)"; else echo "resolv: dangling $(readlink /etc/resolv.conf)"; fi
elif [ -f /etc/resolv.conf ]; then echo "resolv: file"
else echo "resolv: missing"; fi
awk '$1 == "nameserver" {print "nameserver: " $2}' /etc/resolv.conf 2>/dev/null
echo "hosts: $(awk '$1 == "hosts:" {$1 = ""; sub(/^ +/, ""); print; exit}' /etc/nsswitch.conf 2>/dev/null)"
if [ -d /run/systemd/system ]; then echo "systemd: $(timeout 5 systemctl is-system-running 2>/dev/null)"; else echo "systemd: off"; fi
if [ -S /run/systemd/resolve/io.systemd.Resolve ]; then echo "resolved: listening"; fi
if grep -Eiq '^[[:space:]]*generateResolvConf[[:space:]]*=[[:space:]]*false' /etc/wsl.conf 2>/dev/null; then echo "generate: off"; fi
exit 0
""".replace("@LOOKUP@", LOOKUP).replace("@LOOKUP_S@", str(LOOKUP_S))
FACTS = ("lookup", "resolv", "nameserver", "hosts", "systemd", "resolved", "generate", "machine-id", "masked", "liminal-systemd")

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


def _facts(text: str) -> dict:
    """The `key: value` lines one of the plugin's scripts prints (FACTS; each nameserver in a list), the first of each."""
    out: dict = {}
    for line in text.splitlines():
        key, sep, value = line.strip().partition(":")
        if sep and key in FACTS:
            if key == "nameserver":
                out.setdefault(key, []).append(value.strip())
            else:
                out.setdefault(key, value.strip())
    return out


def _resolv_said(facts: dict) -> str:
    """What /etc/resolv.conf is, in words."""
    kind, _, target = facts.get("resolv", "").partition(" ")
    if kind == "link":
        return f"WSL's, a link to {target}" if target.endswith("/wsl/resolv.conf") else f"a link to {target}"
    if kind == "dangling":
        return f"a link to {target}, which does not exist"
    return "a file" if kind == "file" else "missing"


def _found_words(name: str, facts: dict) -> str:
    address = facts["lookup"].partition(" ")[2] or "an address"
    servers = ", ".join(facts.get("nameserver", [])) or "none named"
    return f"{name} looks up {LOOKUP} ({address}) through /etc/resolv.conf ({_resolv_said(facts)}; nameserver {servers})"


def _lookup_words(name: str, facts: dict) -> str:
    """Why a lookup failed, in plain words, from what the check found (where wget said only "unable to resolve host
    address"), and what sets it right when the plugin can."""
    why, ours = [], False
    kind, _, target = facts.get("resolv", "").partition(" ")
    servers = facts.get("nameserver", [])
    if kind in ("", "missing"):
        why.append("it has no /etc/resolv.conf" + (": its /etc/wsl.conf turns WSL's off (generateResolvConf = false)"
                                                  if facts.get("generate") == "off" else ""))
    elif kind == "dangling":
        why.append(f"its /etc/resolv.conf is a link to {target}, which does not exist")
        ours = "systemd/resolve/" in target
    elif not servers:
        why.append("its /etc/resolv.conf names no DNS server")
    hosts = facts.get("hosts", "")
    if "resolve" in hosts.split() and facts.get("resolved") == "listening":
        why.append(f"its lookups go to systemd-resolved first (/etc/nsswitch.conf: hosts: {hosts}), and it does not answer")
        ours = True
    state = facts.get("systemd", "")
    if state not in ("running", "degraded", "off"):
        why.append(f"systemd has not finished booting ({state or 'it does not say how far it has got'})")
        ours = True
    if not why:
        why.append(f"the DNS server WSL gives it ({', '.join(servers)}) does not answer: Windows' own network, a VPN, or "
                   "WSL's DNS (dnsTunneling in .wslconfig) is where to look")
    fix = (f" Its systemd step sets {name} right: run the setup again (an installed {name} is not downloaded again)."
           if ours else "")
    return f"{name} cannot look up {LOOKUP}, so nothing is downloaded inside it: " + "; ".join(why) + "." + fix


def _systemd_words(name: str, facts: dict) -> str:
    made = {"made": "made", "committed": "kept from its first boot", "kept": "kept"}.get(facts.get("machine-id", ""), "set")
    kind, _, target = facts.get("resolv", "").partition(" ")
    removed = f"; a stale /etc/resolv.conf removed (a link to {target})" if kind == "removed" else ""
    return (f"{name} boots as WSL needs: its machine ID {made}, so no boot is systemd's first (which turns on every preset "
            f"and runs a wizard on a console nobody answers); systemd-resolved and systemd-networkd masked (WSL gives the "
            f"network and DNS); names looked up in /etc/hosts, then WSL's /etc/resolv.conf (hosts: "
            f"{facts.get('hosts') or '?'}){removed}; {name} restarted")


def _guard(name: str) -> str:
    """The first lines of a script that downloads inside: a name that cannot be looked up ends it at once, in words."""
    return (f"if ! timeout {LOOKUP_S * 2} getent ahosts {LOOKUP} >/dev/null 2>&1; then\n"
            f"  echo \"{name} cannot look up {LOOKUP}: nothing is downloaded (its setup's dns step says why)\" >&2\n"
            "  exit 3\n"
            "fi\n")


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
    STEPS = STEPS  # the library's, with `systemd` before its conf step and `dns` after it
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

    # -- the setup: the library's steps, and Gentoo's own two ---------------------------------------------------------
    def setup(self, log=print, steps=None) -> list[dict]:
        """Everything, in order, each step reported (`steps`: only these): the library's steps, with `systemd` before its
        conf step (the restart into systemd) and `dns` after it. A step that fails ends it. Run again on a Liminal-Gentoo
        already installed (the platform's Set up, Everything), the distribution step finds it installed and nothing is
        downloaded again: a half-installed one is finished from where it stopped."""
        chosen = set(steps) if steps else set(self.STEPS)
        done: list[dict] = []
        batch: list[str] = []

        def library() -> bool:  # the library's steps gathered so far, run in its order; False once one has failed
            if batch:
                done.extend(WslDistribution.setup(self, log=log, steps=list(batch)))
                batch.clear()
            return not done or done[-1]["ok"] is not False

        for s in self.STEPS:
            if s not in chosen:
                continue
            if s not in OWN_STEPS:
                batch.append(s)
                continue
            if not library():
                return done
            done.append(self._own_step(s, log))
            if done[-1]["ok"] is False:
                return done
        library()
        return done

    def _own_step(self, what: str, log) -> dict:
        name = self.distribution_name

        def step(ok: bool, detail: str) -> dict:
            log(f"{self.name}: {what}: {'ok' if ok else 'FAILED'}: {detail}")
            return {"step": what, "ok": ok, "detail": detail}

        if not liminal_scoped(name):  # never the user's own distribution
            return step(False, f"{name} is not one of Liminal's own distributions ({LIMINAL_PREFIX}...): nothing is changed or asked in it")
        if not self.wsl.here or self.wsl.distribution(name) is None:
            return step(False, f"{name} is not installed: its distribution step installs it")
        try:
            if what == "systemd":
                log(f"{self.name}: systemd: making {name} boot as WSL needs it (its machine ID; systemd-resolved and "
                    f"systemd-networkd off; names through WSL's /etc/resolv.conf), then restarting it...")
                facts = _facts(self.wsl.run(name, "sh", "-s", "liminal-systemd", user="root", stdin=SYSTEMD_SCRIPT, timeout=120))
                self.wsl.terminate(name)  # the next start boots with all of it
                return step(True, _systemd_words(name, facts))
            log(f"{self.name}: dns: looking up {LOOKUP} in {name} before anything is downloaded inside it...")
            return step(True, self.lookup())
        except WslError as e:
            return step(False, str(e))

    def lookup(self) -> str:
        """Whether Liminal-Gentoo can look up LOOKUP, asked inside it as root before anything is downloaded there: the
        step's words when it can; WslError in plain words when it cannot (what /etc/resolv.conf is, the DNS server it
        names, where /etc/nsswitch.conf sends a lookup, whether systemd has finished booting)."""
        name = self.distribution_name
        facts = _facts(self.wsl.run(name, "sh", "-s", "liminal-dns", user="root", stdin=DNS_SCRIPT, timeout=120))
        if facts.get("lookup", "").startswith("ok"):
            return _found_words(name, facts)
        raise WslError(_lookup_words(name, facts))

    def install_script(self) -> str:
        """The library's emerge recipe (emerge --sync, else emerge-webrsync, then Docker), after a lookup of LOOKUP: a
        name that cannot be looked up ends it at once, in words (the docker step run alone included)."""
        return _guard(self.distribution_name) + super().install_script()

    def update_packages(self, log=print) -> list[dict]:
        """The library's update (emerge --sync, else emerge-webrsync, then @world), after the lookup: a name that cannot
        be looked up ends it at once, in words."""
        name = self.distribution_name
        if liminal_scoped(name) and self.wsl.here and self.wsl.distribution(name) is not None:
            try:
                self.lookup()
            except WslError as e:
                log(f"{self.name}: packages: FAILED: {e}")
                return [{"step": "packages", "ok": False, "detail": str(e)}]
        return super().update_packages(log=log)


MACHINE = WslGentooPlugin()
