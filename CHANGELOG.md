# Changelog

## 0.9.0 (2026-11-11)

Its API on its page, plugin API 2.2 (the user: "each plugin should reflect the the API its attached to, and present
links that provide documentation, the plugin interface should more or less contain what it already has, BUT, it should
also expose more of what the API is about"). Five cards (`apis.py`), each with the makers' pages, every part of the API
said covered or not, and every call the plugin makes beside the API's other notable ones:
- WSL (wsl.exe): Microsoft's basic commands, install, wsl.conf and .wslconfig, systemd and import pages, its releases
  and source; the wsl commands the setup and the tasks send (the import, never Microsoft's list), and WSL's own record
  (Lxss) read and renamed.
- Gentoo's stage3 releases: the downloads page, the Handbook's stage file, Gentoo in WSL, the autobuilds and the
  newest systemd stage3's list, the release signatures; the list, the .sha256 and the tarball read, and Gentoo's WSL
  image (stage4) beside them, unused.
- Portage: the Portage and emerge pages, emerge(1), the Handbook's Portage chapter, Upgrading Gentoo, emerge-webrsync.
- Docker, as Gentoo packages it: Gentoo's Docker page and packages, Docker's post-installation steps and references.
- systemd, the install's init: the services scan, Pause, and the plugin's own systemd step (the machine ID,
  systemd-resolved and systemd-networkd masked) and dns step (getent, systemctl is-system-running).

`api_facts()` says what the plugin kept while it ran, asking nothing: Gentoo's newest stage3 as last read, Docker
inside as last seen, the init of the last services scan. Tests: the cards name every wsl command the plugin sends over
the whole setup and every task (a stand-in PC and a stand-in distfiles.gentoo.org), the commands its scripts run
inside and the files it reads of Gentoo's; a link check runs with LIMINAL_VENDOR_PAGES=1. Needs liminal-libs>=1.49.0.

## 0.8.0 (2026-11-09)

Update packages among an install's tasks, liminal-libs 1.39.0's (the user: "move the update packages on to the TASK"):
the Gentoo install chosen brought up to date by emerge, its output in the terminal panel. Needs
liminal-libs>=1.39.0.

## 0.7.0 (2026-11-09)

Rename… among an install's tasks, liminal-libs 1.38.0's (the user: "lets allow renaming the o/s on all three plugins"):
any Gentoo install renamed in WSL's own record (WSL has no command for it), stopped first when it runs;
Liminal-Gentoo keeps Liminal- in front and the plugin follows it through the login (WSL_GENTOO_DISTRIBUTION).
Needs liminal-libs>=1.38.0.

## 0.6.0 (2026-11-09)

The installs' tasks, liminal-libs 1.37.0's (the user: "instead of chosen, put task and for the tasks lets do terminal,
start, pause, stop, allow selection of the linux install by clicking on the list"; "tasks also include uninstall"): a
Gentoo install is chosen by a click on its row in the "Gentoo installs" table, and above it its tasks: Terminal,
Start (kept running until Stop; a paused one resumed), Pause (its running services frozen by systemd; WSL itself cannot
pause a distribution), Stop… and Uninstall…. Needs liminal-libs>=1.37.0.

## 0.5.0 (2026-11-08)

Every Gentoo install listed, and a selector for them (the user: "for the WSL plugins, they need to list all the
'operating systems' that are installed under the plugin's regime, like ubuntu shows all ubuntu installs, fedora --
installs, gentoo -- installs"; "also the ability to uninstall and select which one to terminal in to"; "basically a
selector for different installs"), all of it liminal-libs 1.36.0's: the page's "Gentoo installs" table lists every
Gentoo distribution installed for this Windows user from WSL's own record (WSL records its flavor (gentoo), or a name starting Gentoo; Liminal-Gentoo, imported from Gentoo's stage3, by its own name), its state, version, WSL, disk and
whose, none started to look. The one chosen (Liminal-Gentoo unless another is picked) is the one a terminal opens into,
as its default user, and the one Uninstall unregisters (`wsl --unregister`: its disk deleted for good), one of yours only
after a second confirmation. Needs liminal-libs>=1.36.0.

## 0.4.3 (2026-11-08)

The install no longer stops in its docker step with names that cannot be looked up (the user: "gentoo WSL error -
wget: unable to resolve host address 'distfiles.gentoo.org'"). Before, `emerge --sync` could not look up
rsync.gentoo.org, and emerge-webrsync went back a day at a time. Each wget waited its minute (`-T 60`) until the step's
two hours ran out.

The cause: Gentoo's stage3 ships no /etc/machine-id, so the first boot under systemd (the restart after the conf step)
was systemd's "first boot". On that boot, systemd 261 turns on every unit its presets name. That includes
systemd-resolved, whose socket listens from the start of the boot, along with systemd-networkd and others. It also runs
its first-boot wizard. WSL said it could not start root's user session. Gentoo's /etc/nsswitch.conf sends a lookup to
systemd-resolved before /etc/resolv.conf (`hosts: mymachines resolve [!UNAVAIL=return] files myhostname dns`), so each
lookup waited on it, and WSL's own /etc/resolv.conf was never read. That file is a link to /mnt/wsl/resolv.conf, written
at every start; the stage3 ships none, and systemd's rule for one only fills a gap.

Two steps of Gentoo's own now sit around the library's conf step:

- `systemd` runs before the restart into systemd. It uses file operations only, as root, so it works whether systemd
  runs or not:
  - a machine ID is made, or the one a first boot made is kept on disk;
  - systemd-resolved and systemd-networkd are masked, with their enablement removed (WSL gives the network and the DNS
    server);
  - systemd's rule linking /etc/resolv.conf to resolved's stub is turned off;
  - a stale link in /etc/resolv.conf is removed;
  - names are looked up in /etc/hosts, then /etc/resolv.conf (`hosts: files myhostname dns`, with the old line kept as
    a comment).
  The distribution is then restarted.
- `dns` looks up distfiles.gentoo.org inside before anything is downloaded there (twice, 15 s each). When the lookup
  fails, the step says plainly what is wrong: what /etc/resolv.conf is, the DNS server it names, where nsswitch.conf
  sends a lookup, and whether systemd has finished booting.

The docker step's emerge recipe and the packages' update also look up the name first, and stop at once in words when
they cannot. Running the setup again on a half-installed Liminal-Gentoo (the platform's Set up, Everything) finishes it
from where it stopped. The distribution step finds it installed, so the stage3 is not downloaded again.

## 0.4.2 (2026-11-08)

The install no longer stops at a 404 while getting Liminal-Gentoo's root file system (the user: "gentoo wsl install is
reporting a 404 error for the installer"). Gentoo's list of the latest stage3 (latest-stage3-amd64-systemd.txt) is PGP
clear-signed now, and 0.4.1 took its first line that was not a comment, "-----BEGIN PGP SIGNED MESSAGE-----", for the
tarball's path. The entry is now found by its form (`<build>/stage3-....tar.xz <size>`), in the signed list and in the
older plain one; the list is kept 5 minutes (`stage3()`: the tarball's url and size). The stage3 is kept only when its
size is the list's and its SHA-256 the one Gentoo publishes beside it (`<tarball>.sha256`, read before the download:
without it nothing is downloaded); otherwise it is removed, the install stops saying why, and the next install downloads
it again. A file that cannot be read (offline, a 404) now ends the install's step in words, where an HTTPError escaped
the setup bare. The list's PGP signature is not checked: HTTPS to distfiles.gentoo.org and the SHA-256 are the check.

## 0.4.1 (2026-11-08)

Its icon is Gentoo's g, drawn in the library's line (liminal-libs 1.33.0's `gentoo`; the user: "for the icons, WSL, use the distribution's mascot or icon"). Needs liminal-libs>=1.33.0.

## 0.4.0 (2026-11-08)

Its services (the user: "lets have, in the WSL plugins, a breakdown of the major services running, the 'scanning function' should be capable of using openrc or systemd to look for init type and differentiate between somewhat trivial processes and major services that are online"), on liminal-libs 1.28.0: the platform's page shows what runs in Liminal-Gentoo: the
init system found (systemd or OpenRC, or SysV scripts), the major services online with what each is and its memory,
the system's own counted and named in a note; scanned only while the distribution runs, kept 30 s (`services`,
`services(fresh=True)`). A status, the Docker check or the instance list no longer starts a stopped distribution.

## 0.3.0 (2026-11-07)

On liminal-libs 1.26.0 (the user: "each plugin should have a scheme for checking the environment to see if it supports
installing the operating system it has in its name, if the criteria are met according to the O/S, then the install
method should be not locked out, after the install is run a terminal pops up in the plugin and shows the install
progress, after the install is complete, the user can use the plugin to update the environment's packages"; "the plugin
also allows for a user to login through a terminal in to the environment"): `check` (Windows that runs WSL 2, WSL and its
kernel, a WSL that installs under a name of Liminal's, Gentoo's stage3 found on its mirrors, the processor, 20 GB free), the install's output
streamed to the platform's terminal panel, `update_packages` (emerge --sync and an update of @world) and `terminal` (a login shell into it).

## 0.2.0 (2026-11-07)

Its own distribution of Liminal's, Liminal-Gentoo, installed beside the user's own and never taking it (the user:
"there are no WSL-liminally scoped installs, so all three WSL plugins are invalid"); the plugin is valid only with it
installed, and the platform disables it until then (liminal-libs 1.24.0: `valid` and `why` in its status).

## 0.1.0 (2026-11-07)

The first release: Gentoo in WSL 2 set up by the plugin (the library's WslDistribution,
liminal-libs 1.19.0), Docker installed inside by emerge from Docker's own repository, the engine
started and enabled, offered as the Docker instance `wsl-gentoo`.
