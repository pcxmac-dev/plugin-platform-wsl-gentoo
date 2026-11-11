"""What WSL Gentoo attaches to (plugin API 2.2, liminal_libs.sources.apis; the user, 2026-11-11: "each plugin should
reflect the the API its attached to, and present links that provide documentation ... it should also expose more of
what the API is about"): wsl.exe, Gentoo's stage3 releases (Liminal-Gentoo is imported from one), Portage inside, Docker as Gentoo
packages it, and the install's init (systemd). Every address was read on the makers' own pages on 2026-11-11 (`VERIFIED`).

The code that drives them is the library's (liminal_libs.machines.wsl, WslDistribution); the cards are this plugin's:
`facts` says what the plugin kept of them while it ran (asking nothing)."""
from __future__ import annotations

import time

from liminal_libs.sources.apis import Api, Area, Call, Link

VERIFIED = "2026-11-11"
LEARN = "https://learn.microsoft.com/en-us/windows/wsl/"
DOCKER = "https://docs.docker.com/"
SYSTEMD = "https://www.freedesktop.org/software/systemd/man/latest/"
WIKI = "https://wiki.gentoo.org/wiki/"
AUTOBUILDS = "https://distfiles.gentoo.org/releases/amd64/autobuilds/"
MAN7 = "https://man7.org/linux/man-pages/"
KEEP_RUNNING = "wsl -d <distribution> --exec sh -c 'while :; do sleep 3600; done'"

WSL = Api(
    name="WSL (wsl.exe)",
    maker="Microsoft",
    about=("The Windows Subsystem for Linux: Linux distributions running in a light virtual machine on this Windows PC, "
           "installed, listed, started, stopped and removed with wsl.exe, and set up one by one in their /etc/wsl.conf. "
           "The plugin imports Liminal-Gentoo with it, runs everything inside Liminal-Gentoo through it as root, and "
           "reads WSL's own record of each install to list them without starting one."),
    kind="command",
    base="wsl.exe, windowless (inside a distribution: wsl -d <distribution> --exec ...)",
    version="WSL 2 (a distribution imported as WSL 2: wsl --import ... --version 2)",
    auth=("none asked: wsl runs as the signed-in Windows user, and `wsl -u root` inside needs no password; installing WSL "
          "itself asks Windows to confirm as an administrator (UAC), and may want a restart"),
    limits=("no request limits (a command on this PC); WSL stops a distribution 15 s after its last session ends "
            "(.wslconfig's instanceIdleTimeout), which is why Start keeps a session open"),
    costs="",
    links=(
        Link("WSL documentation", LEARN, "docs"),
        Link("Basic commands for WSL", LEARN + "basic-commands", "reference"),
        Link("Install WSL", LEARN + "install", "guide"),
        Link("Advanced settings: wsl.conf and .wslconfig", LEARN + "wsl-config", "guide"),
        Link("Use systemd to manage Linux services with WSL", LEARN + "systemd", "guide"),
        Link("Import any Linux distribution", LEARN + "use-custom-distro", "guide"),
        Link("Troubleshooting WSL", LEARN + "troubleshooting", "guide"),
        Link("WSL releases", "https://github.com/microsoft/WSL/releases", "changelog"),
        Link("What's new in WSL, November 2024: wsl --install --name and --location",
             "https://devblogs.microsoft.com/commandline/whats-new-in-the-windows-subsystem-for-linux-in-november-2024",
             "changelog"),
        Link("WSL's source", "https://github.com/microsoft/WSL", "source"),
        Link("WSL in the Microsoft Store", "https://apps.microsoft.com/detail/9P9TQF7MRM4R", "tool"),
    ),
    areas=(
        Area("WSL itself", "installing WSL, updating it, its version and its kernel, its status", LEARN + "install",
             covered="installed and updated by the setup; its Linux kernel checked first"),
        Area("Distributions from Microsoft's list", "wsl --list --online, then wsl --install <name>, under a name and in a "
             "folder of its own", LEARN + "basic-commands#install"),
        Area("Installed distributions", "each distribution's state and WSL version, the default one",
             LEARN + "basic-commands#list-installed-linux-distributions",
             covered="every Gentoo install listed in the installs table, Liminal's and yours, none started to look"),
        Area("Running commands inside", "a command in a distribution, as a user or as root, in a folder",
             LEARN + "basic-commands#run-a-specific-linux-distribution-from-powershell-or-cmd",
             covered="scripts as root on standard input, Docker's checks, the run hook, the terminal"),
        Area("Stopping and removing", "terminating one distribution, shutting WSL down, unregistering a distribution (its "
             "disk deleted)", LEARN + "basic-commands#terminate",
             covered="Stop (wsl --terminate) and Uninstall (wsl --unregister) among an install's tasks"),
        Area("Importing and exporting", "a distribution from a tar file or a disk, and back to one", LEARN + "use-custom-distro",
             covered="Liminal-Gentoo imported from Gentoo's stage3 as WSL 2, into the data folder"),
        Area("wsl.conf", "a distribution's own settings: [boot] systemd and command, [user] default, automount, network, "
             "interop", LEARN + "wsl-config#wslconf", covered="systemd on and the default user (liminal), written by the setup"),
        Area(".wslconfig", "WSL's settings for every distribution: memory, processors, networking mode, DNS tunneling, "
             "idle timeouts", LEARN + "wsl-config#wslconfig"),
        Area("systemd", "systemd as a distribution's init, turned on in wsl.conf", LEARN + "systemd",
             covered="turned on by the setup; Pause freezes the running services with systemd's freezer"),
        Area("WSL's record of each distribution", "the registry key WSL keeps for each distribution of this Windows user "
             "(Lxss): its name, flavor, OS version, Store package, folder and disk; Microsoft documents no page for it",
             covered="read for the installs table without starting anything; Rename changes a name in it"),
        Area("Windows files from Linux", "Windows' drives under /mnt (DrvFs), and Linux files from Windows",
             LEARN + "filesystems", covered="Windows paths handed to the Docker instance as /mnt/<drive>/..."),
        Area("Disks", "each distribution's virtual disk, its size and space, physical disks mounted into WSL",
             LEARN + "disk-space", covered="each install's disk and its size shown in the installs table"),
        Area("Networking", "NAT and mirrored modes, localhost forwarding, DNS", LEARN + "networking"),
        Area("WSL 1 and WSL 2", "the two architectures and moving a distribution between them", LEARN + "compare-versions",
             covered="new distributions get WSL 2 (the setup's version step)"),
        Area("Linux GUI apps (WSLg)", "Linux graphical apps in Windows' own windows", LEARN + "tutorials/gui-apps"),
        Area("WSL containers", "containers run by WSL itself (wslc.exe), set up apart from .wslconfig",
             LEARN + "wsl-container-settings"),
        Area("Custom distributions", "a distribution packaged for others to install", LEARN + "build-custom-distro"),
    ),
    calls=(
        Call("wsl --status", "WSL's default distribution and version", "WSL itself",
             used="whether WSL is here: the status, the check, the setup", docs=LEARN + "basic-commands#check-wsl-status"),
        Call("wsl --version", "the versions of WSL and of its Linux kernel", "WSL itself",
             used="the check: WSL 2's Linux kernel", docs=LEARN + "basic-commands#check-wsl-version"),
        Call("wsl --install --no-distribution", "WSL itself, no distribution yet", "WSL itself",
             used="the setup's wsl step (Windows asks; a restart may follow)", docs=LEARN + "basic-commands#install",
             writes=True),
        Call("wsl --update", "WSL brought to its newest release", "WSL itself", used="the setup's update step",
             docs=LEARN + "basic-commands#update-wsl", writes=True),
        Call("wsl --set-default-version 2", "the WSL version new distributions get", "WSL 1 and WSL 2",
             used="the setup's version step", docs=LEARN + "basic-commands#set-default-wsl-version", writes=True),
        Call("wsl --import <distribution> <folder> <file> --version 2", "a distribution from a tar file, as WSL 2",
             "Importing and exporting", used="the setup's distribution step: Liminal-Gentoo from the checked stage3",
             docs=LEARN + "basic-commands#import-a-distribution", writes=True),
        Call("wsl --list --verbose", "each distribution installed, its state and WSL version", "Installed distributions",
             used="Liminal-Gentoo's state, and the installs table", docs=LEARN + "basic-commands#list-installed-linux-distributions"),
        Call("wsl -d <distribution> -u root --exec sh -s", "a shell script run as root, given on standard input",
             "Running commands inside",
             used=("the setup's scripts (its systemd and dns steps, the default user, Docker's build, the engine, the docker "
                   "group), Update packages, the services scan"),
             docs=LEARN + "basic-commands#run-a-specific-linux-distribution-from-powershell-or-cmd", writes=True),
        Call("wsl -d <distribution> -u root --exec sh -c", "a shell command run as root",
             "Running commands inside", used="/etc/wsl.conf written; Pause and the resume after it (systemd's freezer)",
             docs=LEARN + "basic-commands#run-as-a-specific-user", writes=True),
        Call("wsl -d <distribution> --exec docker", "Docker's command line inside, as the default user",
             "Running commands inside",
             used="Docker's version and whether its daemon answers; the Docker instance wsl-gentoo offered to the framework"),
        Call("wsl -d <distribution> --exec <command>", "any command inside, as the default user", "Running commands inside",
             used="the run hook: a command the platform asks for"),
        Call(KEEP_RUNNING, "a windowless session holding a distribution up", "Running commands inside",
             used="Start: the install keeps running until Stop"),
        Call("wsl -d <distribution> --cd ~ --exec sh -c <login shell>", "a login shell in the home folder",
             "Running commands inside", used="Terminal: a login shell in the platform's terminal panel",
             docs=LEARN + "basic-commands#start-wsl-in-user-home-directory"),
        Call("wsl --terminate <distribution>", "a distribution stopped: every program in it ends", "Stopping and removing",
             used="Stop; the restart after /etc/wsl.conf is written; before a rename", docs=LEARN + "basic-commands#terminate",
             writes=True),
        Call("wsl --unregister <distribution>", "a distribution removed with its disk, for good", "Stopping and removing",
             used="Uninstall (one of yours only after a second confirmation)",
             docs=LEARN + "basic-commands#unregister-or-uninstall-a-linux-distribution", writes=True),
        Call(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Lxss (read)", "WSL's record of each distribution",
             "WSL's record of each distribution", used="each install's flavor, OS version, Store package, folder and disk"),
        Call(r"Lxss\{GUID} DistributionName (set)", "a distribution's name in WSL's record", "WSL's record of each distribution",
             used="Rename: WSL has no command for it (the install is stopped first)", writes=True),
        Call("wsl --shutdown", "every distribution and WSL's virtual machine stopped", "Stopping and removing",
             docs=LEARN + "basic-commands#shutdown", writes=True),
        Call("wsl --set-default <distribution>", "the distribution plain wsl commands use", "Installed distributions",
             docs=LEARN + "basic-commands#set-default-linux-distribution", writes=True),
        Call("wsl --set-version <distribution> <1|2>", "a distribution moved between WSL 1 and WSL 2", "WSL 1 and WSL 2",
             docs=LEARN + "basic-commands#set-wsl-version-to-1-or-2", writes=True),
        Call("wsl --list --online", "the distributions wsl --install can fetch (Gentoo is not among them)",
             "Distributions from Microsoft's list", docs=LEARN + "basic-commands#list-available-linux-distributions"),
        Call("wsl --install <distribution> --name <name> --location <folder> --no-launch",
             "a distribution from Microsoft's list, under a name and in a folder of its own", "Distributions from Microsoft's list",
             docs=LEARN + "basic-commands#install", writes=True),
        Call("wsl --install --from-file <file>", "a distribution from a .wsl image file (WSL 2.4.10 and later: Gentoo's stage4)",
             "Importing and exporting", docs=WIKI + "Gentoo_in_WSL#Modern_WSL_.282.4.10_and_later.29", writes=True),
        Call("wsl --export <distribution> <file>", "a distribution saved as a tar file (or a .vhdx with --vhd)",
             "Importing and exporting", docs=LEARN + "basic-commands#export-a-distribution"),
        Call("wsl --mount <disk>", "a physical or virtual disk attached to WSL 2 and mounted", "Disks",
             docs=LEARN + "wsl2-mount-disk", writes=True),
        Call("wsl --list --running", "the distributions running now", "Installed distributions",
             docs=LEARN + "basic-commands#list-installed-linux-distributions"),
        Call("wsl --update --pre-release", "WSL's newest preview", "WSL itself", docs=LEARN + "install", writes=True),
    ),
    verified=VERIFIED,
)

PORTAGE = Api(
    name="Portage (Gentoo's emerge)",
    maker="Gentoo",
    about=("Gentoo's package manager: emerge syncs the Gentoo ebuild repository, then builds packages from their sources "
           "and installs them with what they depend on, as the profile and the USE flags say. The plugin runs it as root "
           "inside the install to sync, to bring @world up to date and to build Docker, which takes a while: it compiles."),
    kind="command",
    base="emerge, as root inside the install (through wsl -u root)",
    version="the Portage of the current amd64 systemd stage3",
    auth="root inside the install; Gentoo's repository and its source files are public",
    limits="",
    costs="",
    links=(
        Link("Portage", WIKI + "Portage", "docs"),
        Link("emerge", WIKI + "Emerge", "reference"),
        Link("emerge(1)", "https://dev.gentoo.org/~zmedico/portage/doc/man/emerge.1.html", "reference"),
        Link("Gentoo Handbook: Portage", WIKI + "Handbook:AMD64/Full/Portage", "guide"),
        Link("Upgrading Gentoo", WIKI + "Upgrading_Gentoo", "guide"),
        Link("emerge-webrsync", WIKI + "Emerge-webrsync", "guide"),
        Link("Gentoo's packages", "https://packages.gentoo.org/", "tool"),
        Link("Portage's source", "https://gitweb.gentoo.org/proj/portage.git/", "source"),
        Link("Gentoo's infrastructure status", "https://infra-status.gentoo.org/", "status"),
    ),
    areas=(
        Area("Syncing the repository", "the Gentoo ebuild repository brought up to date, over rsync or a snapshot",
             WIKI + "Ebuild_repository#Repository_synchronization",
             covered="emerge --sync, else emerge-webrsync, before Docker's build and each update"),
        Area("Updating @world", "every package the system wants, rebuilt where its version or USE flags changed",
             WIKI + "Upgrading_Gentoo#Updating_packages", covered="Update packages: @world, deep, with the new USE flags"),
        Area("Installing packages", "packages built from source with their dependencies", WIKI + "Emerge",
             covered="Docker's packages built and installed"),
        Area("Removing packages", "packages unmerged, and those nothing needs any more (depclean)", WIKI + "Emerge"),
        Area("Searching", "packages found by name or description", WIKI + "Emerge"),
        Area("USE flags and profiles", "what each package is built with, and the profile the system follows",
             WIKI + "Handbook:AMD64/Full/Portage", covered="the stage3's systemd profile, as Gentoo ships it"),
        Area("Snapshots", "the repository installed from a snapshot from the web", WIKI + "Emerge-webrsync",
             covered="emerge-webrsync when rsync cannot be reached"),
    ),
    calls=(
        Call("emerge --sync --quiet", "the repository synced over rsync", "Syncing the repository",
             used="before Docker's build; Update packages", docs=WIKI + "Emerge", writes=True),
        Call("emerge-webrsync", "the repository from Gentoo's daily snapshot", "Snapshots",
             used="when emerge --sync fails", docs=WIKI + "Emerge-webrsync", writes=True),
        Call("emerge --update --deep --newuse --quiet-build=y @world", "every package of @world brought up to date",
             "Updating @world", used="Update packages", docs=WIKI + "Upgrading_Gentoo", writes=True),
        Call("emerge --quiet-build=y <packages>", "packages built and installed", "Installing packages",
             used="Docker's packages", docs=WIKI + "Emerge", writes=True),
        Call("emerge --depclean", "packages nothing needs any more removed", "Removing packages", docs=WIKI + "Emerge",
             writes=True),
        Call("emerge --search <words>", "packages found by name", "Searching", docs=WIKI + "Emerge"),
        Call("emerge --ask <packages>", "what would be done, asked before it is", "Installing packages", docs=WIKI + "Emerge"),
    ),
    verified=VERIFIED,
)

STAGE3 = Api(
    name="Gentoo's stage3 releases",
    maker="Gentoo",
    about=("Gentoo's root file systems: a stage3 tarball holds a working base system to start an install from, beside "
           "its checksums and signatures, and a list names the newest of each kind. Gentoo is not on "
           "Microsoft's list, so the plugin downloads the newest amd64 systemd stage3 once, checks it against Gentoo's own "
           "figures and imports it into WSL as Liminal-Gentoo; then makes it boot as WSL needs."),
    kind="feed",
    base=AUTOBUILDS,
    version="the newest amd64 systemd stage3 (latest-stage3-amd64-systemd.txt)",
    auth=("none: public files; each tarball is kept only with the size Gentoo's list gives and the SHA-256 Gentoo "
          "publishes beside it (the PGP signature of the list and of the checksums is not checked: HTTPS and the "
          "SHA-256 are)"),
    limits="",
    costs="",
    links=(
        Link("Gentoo's downloads", "https://www.gentoo.org/downloads/", "docs"),
        Link("Gentoo Handbook: the stage file", WIKI + "Handbook:AMD64/Installation/Stage", "guide"),
        Link("Gentoo in WSL", WIKI + "Gentoo_in_WSL", "guide"),
        Link("systemd on Gentoo", WIKI + "Systemd", "guide"),
        Link("The amd64 autobuilds", AUTOBUILDS, "source"),
        Link("The newest systemd stage3", AUTOBUILDS + "latest-stage3-amd64-systemd.txt", "source"),
        Link("Release media signatures", "https://www.gentoo.org/downloads/signatures/", "auth"),
        Link("Gentoo's mirrors", "https://www.gentoo.org/downloads/mirrors/", "tool"),
        Link("Gentoo's infrastructure status", "https://infra-status.gentoo.org/", "status"),
    ),
    areas=(
        Area("stage3 tarballs", "a base system per architecture, init (OpenRC or systemd) and profile",
             WIKI + "Handbook:AMD64/Installation/Stage",
             covered="the newest amd64 systemd stage3, downloaded once into the data folder and imported"),
        Area("The newest builds' lists", "latest-stage3-*.txt: the newest tarball of each kind and its size",
             AUTOBUILDS, covered="the list read (kept five minutes), its PGP clear-signing read past"),
        Area("Checksums and signatures", "each tarball's .sha256 and .DIGESTS, clear-signed by Gentoo's release keys",
             WIKI + "Handbook:AMD64/Installation/Stage",
             covered="the size and the SHA-256 checked before anything is imported; a tarball that fails is removed"),
        Area("Gentoo in WSL", "Gentoo's own page on WSL: a stage file imported, or its WSL image on WSL 2.4.10 and later",
             WIKI + "Gentoo_in_WSL#Importing_Gentoo_via_stage_file", covered="Liminal-Gentoo imported from the stage file"),
        Area("Gentoo's WSL images", "a stage4 made for WSL (stage4-amd64-wsl-systemd), installed with wsl --install --from-file",
             WIKI + "Gentoo_in_WSL#Modern_WSL_.282.4.10_and_later.29"),
        Area("Booting under systemd in WSL", "a machine ID, so no boot is systemd's first; WSL's own network and DNS",
             WIKI + "Systemd",
             covered=("its systemd step: the machine ID kept or made, systemd-resolved and systemd-networkd masked, names "
                      "looked up through WSL's /etc/resolv.conf")),
        Area("Mirrors", "the mirrors that carry the releases", "https://www.gentoo.org/downloads/mirrors/"),
        Area("Installing by the Handbook", "the Handbook's own install: the stage unpacked, then chrooted into",
             WIKI + "Handbook:AMD64/Installation/Base"),
    ),
    calls=(
        Call("GET latest-stage3-amd64-systemd.txt", "the newest systemd stage3's path and size", "The newest builds' lists",
             used="the check and the install: which tarball, and how big", docs=AUTOBUILDS + "latest-stage3-amd64-systemd.txt"),
        Call("GET <stage3>.tar.xz.sha256", "the tarball's SHA-256, clear-signed", "Checksums and signatures",
             used="read before the download: without it nothing is downloaded or imported",
             docs=WIKI + "Handbook:AMD64/Installation/Stage"),
        Call("GET <stage3>.tar.xz", "the stage3 tarball", "stage3 tarballs",
             used="downloaded once into the data folder, then checked", docs=AUTOBUILDS),
        Call("GET <stage3>.tar.xz.asc", "the tarball's detached PGP signature", "Checksums and signatures",
             docs=WIKI + "Handbook:AMD64/Installation/Stage"),
        Call("GET <stage3>.tar.xz.DIGESTS", "the tarball's checksums in several algorithms", "Checksums and signatures",
             docs=WIKI + "Handbook:AMD64/Installation/Stage"),
        Call("GET latest-stage4-amd64-wsl-systemd.txt", "the newest Gentoo WSL image", "Gentoo's WSL images",
             docs=AUTOBUILDS + "latest-stage4-amd64-wsl-systemd.txt"),
    ),
    verified=VERIFIED,
)

DOCKER_ENGINE = Api(
    name="Docker (Gentoo's packages)",
    maker="Docker, Inc., packaged by Gentoo",
    about=("Docker's container engine for Linux, built by Gentoo from its sources: app-containers/docker (the dockerd "
           "daemon), docker-cli, docker-buildx and docker-compose. Docker publishes no Gentoo page of its own; Gentoo's "
           "wiki is its install guide. The plugin builds it inside Liminal-Gentoo, starts it and offers it to the "
           "framework as the Docker instance wsl-gentoo, reached as `wsl -d Liminal-Gentoo --exec docker`."),
    kind="command",
    base="docker inside Liminal-Gentoo, built by emerge from app-containers/docker and its companions",
    version="Gentoo's app-containers/docker as the ebuild repository gives it when synced",
    auth=("the docker group: its members (the install's default user) reach the daemon without sudo, which is root's "
          "power over the install"),
    limits="",
    costs="",
    links=(
        Link("Docker on Gentoo", WIKI + "Docker", "docs"),
        Link("app-containers/docker", "https://packages.gentoo.org/packages/app-containers/docker", "source"),
        Link("Linux post-installation steps (Docker)", DOCKER + "engine/install/linux-postinstall/", "guide"),
        Link("Docker CLI reference", DOCKER + "reference/cli/docker/", "reference"),
        Link("dockerd reference", DOCKER + "reference/cli/dockerd/", "reference"),
        Link("Docker Engine release notes", DOCKER + "engine/release-notes/", "changelog"),
    ),
    areas=(
        Area("The packages", "app-containers/docker, docker-cli, docker-buildx, docker-compose",
             "https://packages.gentoo.org/packages/app-containers/docker", covered="built and installed by emerge"),
        Area("The kernel and USE flags", "the kernel options Docker needs and the flags it is built with", WIKI + "Docker",
             covered="WSL's own kernel, which carries what Docker needs"),
        Area("The daemon", "dockerd, started by the init and on at boot", DOCKER + "reference/cli/dockerd/",
             covered="started and enabled at boot: systemd, else OpenRC, else the service command"),
        Area("Docker without sudo", "the docker group, whose members reach the daemon",
             DOCKER + "engine/install/linux-postinstall/#manage-docker-as-a-non-root-user",
             covered="the install's default user put in the docker group"),
        Area("The command line", "docker's commands: containers, images, volumes, networks, the system",
             DOCKER + "reference/cli/docker/",
             covered="docker --version and docker info say whether it is installed and running; the Docker plugin drives the rest"),
        Area("Upgrades", "Docker rebuilt with @world when a new version comes", WIKI + "Upgrading_Gentoo",
             covered="with the install's packages (Update packages)"),
        Area("Rootless mode", "the daemon run as an ordinary user", DOCKER + "engine/security/rootless/"),
        Area("Troubleshooting in WSL", "Docker's known faults under WSL, from Gentoo's page",
             WIKI + "Gentoo_in_WSL#Segmentation_fault_in_docker"),
    ),
    calls=(
        Call("emerge --quiet-build=y app-containers/docker app-containers/docker-cli app-containers/docker-buildx "
             "app-containers/docker-compose", "Docker's packages built and installed", "The packages",
             used="the setup's docker step (after a lookup of distfiles.gentoo.org)", docs=WIKI + "Docker", writes=True),
        Call("systemctl enable --now docker", "the daemon started and on at boot (systemd)", "The daemon",
             used="the setup's engine step", docs=WIKI + "Docker", writes=True),
        Call("rc-service docker start", "the daemon started (OpenRC, after rc-update add docker default)", "The daemon",
             used="the engine step, when the install runs OpenRC", docs=WIKI + "Docker", writes=True),
        Call("service docker start", "the daemon started by its init script", "The daemon",
             used="the engine step, when the install runs neither systemd nor OpenRC", writes=True),
        Call("groupadd -f docker", "the docker group, made when absent", "Docker without sudo", used="the setup's user step",
             docs=DOCKER + "engine/install/linux-postinstall/#manage-docker-as-a-non-root-user", writes=True),
        Call("usermod -aG docker <user>", "a user added to the docker group", "Docker without sudo",
             used="the setup's user step", docs=WIKI + "Docker", writes=True),
        Call("docker --version", "the command line's version", "The command line", used="whether Docker is installed",
             docs=DOCKER + "reference/cli/docker/version/"),
        Call("docker info --format {{.ServerVersion}}", "the daemon's version, when it answers", "The command line",
             used="whether the daemon runs", docs=DOCKER + "reference/cli/docker/system/info/"),
        Call("docker run hello-world", "a first container, a check of the install", "The command line", docs=WIKI + "Docker"),
    ),
    verified=VERIFIED,
)

INIT = Api(
    name="systemd (the install's init)",
    maker="the systemd project",
    about=("systemd, the init and service manager the install runs as PID 1 once /etc/wsl.conf turns it on: it starts "
           "the services, lists them with their state and memory, and can freeze a service's processes and thaw them. "
           "Gentoo's stage3 ships no machine ID and turns systemd-resolved on, so the plugin's own systemd step makes the "
           "install boot as WSL needs before the restart into systemd, and its dns step checks a lookup after it. The "
           "services scan reads systemd (or OpenRC's or SysV's, when an install runs those), and Pause is systemd's freezer."),
    kind="command",
    base="systemctl, as root inside the install (through wsl -u root)",
    version="systemd 246 or later for the freezer (cgroup v2, which WSL mounts by default)",
    auth="root inside the install",
    limits="",
    costs="",
    links=(
        Link("systemctl(1)", SYSTEMD + "systemctl.html", "reference"),
        Link("systemd's manual pages", SYSTEMD, "docs"),
        Link("Use systemd to manage Linux services with WSL", LEARN + "systemd", "guide"),
        Link("systemd's news", "https://github.com/systemd/systemd/blob/main/NEWS", "changelog"),
        Link("systemd's source", "https://github.com/systemd/systemd", "source"),
    ),
    areas=(
        Area("Units and their state", "every service unit, loaded or not, active or failed", SYSTEMD + "systemctl.html",
             covered="the services scan: each service's state, the running ones' memory"),
        Area("Freezing", "a unit's processes suspended in their cgroup, and thawed", SYSTEMD + "systemctl.html",
             covered="Pause freezes each running service but the system's own plumbing; Start thaws them"),
        Area("Starting and stopping", "units started, stopped, restarted, enabled at boot", SYSTEMD + "systemctl.html",
             covered="Docker's daemon enabled and started (the Docker Engine card)"),
        Area("The journal", "the services' logs", SYSTEMD + "journalctl.html"),
        Area("Unit files", "how a service is described: what it runs, when, as whom", SYSTEMD + "systemd.unit.html"),
        Area("Other inits", "OpenRC (rc-status) and SysV scripts (service), for an install that runs those",
             "https://github.com/OpenRC/openrc/blob/master/man/rc-status.8",
             covered="the services scan reads them the same way when the install's init is one of them"),
        Area("Processes", "every process with its memory, as ps lists them", "https://man7.org/linux/man-pages/man1/ps.1.html",
             covered="the services scan counts them beside the units"),
        Area("The machine ID and the first boot", "/etc/machine-id: without one a boot is systemd's first, which turns on "
             "every unit its presets name", SYSTEMD + "machine-id.html",
             covered="its systemd step keeps a first boot's machine ID, or makes one"),
        Area("Name lookups", "systemd-resolved, /etc/resolv.conf and /etc/nsswitch.conf: where a name is looked up",
             SYSTEMD + "systemd-resolved.service.html",
             covered=("systemd-resolved and systemd-networkd masked (WSL gives the network and the DNS server); names "
                      "looked up in /etc/hosts, then WSL's /etc/resolv.conf; a lookup checked before any download")),
    ),
    calls=(
        Call("systemctl list-units --type=service", "the service units and their states", "Units and their state",
             used="the services scan; Pause's list of the running services", docs=SYSTEMD + "systemctl.html"),
        Call("systemctl show -p Id -p MainPID -p MemoryCurrent <units>", "properties of the running services",
             "Units and their state", used="the services scan: each running service's process and memory",
             docs=SYSTEMD + "systemctl.html"),
        Call("systemctl freeze <unit>", "a unit's processes frozen", "Freezing", used="Pause", docs=SYSTEMD + "systemctl.html",
             writes=True),
        Call("systemctl thaw <unit>", "a frozen unit's processes thawed", "Freezing", used="Start after Pause",
             docs=SYSTEMD + "systemctl.html", writes=True),
        Call("systemctl show -p Id -p FreezerState --type=service '*'", "which services are frozen", "Freezing",
             used="the resume: any service still frozen is thawed too", docs=SYSTEMD + "systemctl.html"),
        Call("rc-status --all", "OpenRC's services and their states", "Other inits",
             used="the services scan, when the install runs OpenRC", docs="https://github.com/OpenRC/openrc/blob/master/man/rc-status.8"),
        Call("service --status-all", "the SysV scripts' states", "Other inits",
             used="the services scan, when the install runs neither"),
        Call("systemd-machine-id-setup --commit", "a first boot's transient machine ID written to disk",
             "The machine ID and the first boot", used="its systemd step", docs=SYSTEMD + "systemd-machine-id-setup.html",
             writes=True),
        Call("ln -sfn /dev/null <unit>", "a unit masked in /etc/systemd/system: nothing can start it (what systemctl mask writes)",
             "Name lookups", used="its systemd step: systemd-resolved and systemd-networkd masked", docs=SYSTEMD + "systemctl.html",
             writes=True),
        Call("systemctl is-system-running", "how far systemd has got with its boot", "Units and their state",
             used="its dns step: whether systemd has finished booting", docs=SYSTEMD + "systemctl.html"),
        Call("getent ahosts <name>", "a name looked up as programs look it up (/etc/nsswitch.conf)", "Name lookups",
             used="its dns step, and before Docker's build and each update: distfiles.gentoo.org", docs=MAN7 + "man1/getent.1.html"),
        Call("systemctl mask <unit>", "a unit masked by systemd itself", "Starting and stopping", docs=SYSTEMD + "systemctl.html",
             writes=True),
        Call("ps -eo pid=,rss=,comm=,args=", "every process, its memory and command", "Processes",
             used="the services scan: the processes and their memory", docs="https://man7.org/linux/man-pages/man1/ps.1.html"),
        Call("systemctl restart <unit>", "a unit stopped and started", "Starting and stopping", docs=SYSTEMD + "systemctl.html",
             writes=True),
        Call("journalctl -u <unit>", "a unit's log", "The journal", docs=SYSTEMD + "journalctl.html"),
    ),
    verified=VERIFIED,
)

APIS = (WSL, STAGE3, PORTAGE, DOCKER_ENGINE, INIT)


def ago(when: float, now: float | None = None) -> str:
    """A time on the monotonic clock, said as how long ago: "40 s ago", "3 min ago", "2 h ago"."""
    s = max(0.0, (time.monotonic() if now is None else now) - when)
    return f"{s:.0f} s ago" if s < 90 else f"{s / 60:.0f} min ago" if s < 5400 else f"{s / 3600:.0f} h ago"


def count(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def facts(plugin) -> dict[str, dict[str, str]]:
    """What the plugin kept of its APIs while it ran (asking nothing): Gentoo's newest stage3 as last read, Docker
    inside as last seen, the init the last services scan found."""
    out: dict[str, dict[str, str]] = {}
    stage3 = getattr(plugin, "_stage3", None)  # (when, (url, size)): Gentoo's list of the latest stage3, kept five minutes
    if stage3:
        at, (url, size) = stage3
        out[STAGE3.name] = {"Newest systemd stage3": f"{url.rsplit('/', 1)[-1]}, {size / 2**20:.0f} MB, read {ago(at)}"}
    seen = getattr(plugin, "_engine_seen", None)  # docker --version and docker info, as last seen while it ran
    if seen:
        out[DOCKER_ENGINE.name] = {"Docker inside": (f"{seen.get('version') or 'installed'}, its daemon "
                                                     + ("answering" if seen.get("running") else "not answering")
                                                     if seen.get("installed") else "not installed") + " (as last seen)"}
    kept = getattr(plugin, "_scan", None)  # (when, Scan): the last services scan
    if kept:
        at, scan = kept
        words = scan.problem or f"{count(len(scan.major), 'service')} of note, {len(scan.system)} of the system's own running"
        out[INIT.name] = {"Init": scan.init + (f" (PID 1: {scan.pid1})" if scan.pid1 else ""),
                          "Last scan": f"{words}, {ago(at)}"}
    return out
