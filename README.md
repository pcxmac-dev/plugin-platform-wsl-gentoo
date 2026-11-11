# plugin-platform-wsl-gentoo

WSL Gentoo for Liminal: Gentoo in WSL 2 on this Windows PC, set up by the plugin,
with Docker inside, offered to the framework as the Docker instance `wsl-gentoo`.

The user's words (2026-11-07): "the platform is the interface for the software/hardware which facilitates the
liminal framework"; "the scope of the plugin is setting up WSL/Ubuntu and supporting docker for the
platform"; "the ubuntu plugin needs to be able to install docker (do everything manually) and allow
different docker instances to support the liminal framework"; "then create a gentoo and fedora plugin as
well, same scope/function".

## What it does

A machine plugin of the platform (`liminal_libs.machines.MachinePlugin`, plugin API 2.2), the library's
`WslDistribution` with this distribution's name and family. Its hooks:

- `present()`: whether the distribution is installed in WSL.
- `status()`: WSL itself, the distribution's state and version, the default user, Docker inside (installed,
  its version, the daemon answering).
- `setup()`: everything, step by step, each reported: WSL itself (`wsl --install --no-distribution`; Windows
  asks to confirm with elevation and may want a restart), `wsl --update`, WSL 2 as the default, the
  distribution (imported with `wsl --import Liminal-Gentoo` from the latest amd64 systemd stage3 tarball of Gentoo's own mirrors (downloaded into the data folder's platform/wsl/wsl-gentoo); Docker by emerge (app-containers/docker, docker-cli, docker-buildx, docker-compose), which compiles and takes a while.), its boot under
  systemd set right for WSL (`systemd`: a machine ID, so no boot is systemd's first, which would turn on every preset and
  run its first-boot wizard; systemd-resolved and systemd-networkd masked, since WSL gives the network and the DNS server;
  names looked up in /etc/hosts, then WSL's own /etc/resolv.conf), `/etc/wsl.conf` with systemd on and the default user `liminal`
  (WSL_GENTOO_USER) made when absent, a lookup of distfiles.gentoo.org checked before anything is downloaded inside
  (`dns`: when it fails, what is wrong is said in words), Docker installed, the engine started and enabled (systemd, else
  OpenRC, else `service`), the user in the docker group. Everything inside runs as root through `wsl -u
  root`, so no password is asked. A step can be run alone: `setup docker`. Run again on an installed Liminal-Gentoo, the
  setup finishes it from where it stopped: the distribution step finds it installed and nothing is downloaded again.
- `run(command)`: a command in the distribution.
- `instances()`: the engine as the Docker instance `wsl-gentoo`, reached as `wsl -d Gentoo docker`,
  Windows paths under `/mnt`; a login file's `[server] instance = wsl-gentoo` runs its mail server there, and
  `liminal_libs.docker.instance("wsl-gentoo")` gives any app the engine.

Variables: `WSL_GENTOO_DISTRIBUTION` (the WSL name, `Liminal-Gentoo` unless said), `WSL_GENTOO_USER`.

Its distribution is Liminal's own, installed beside the user's distributions and never taking one of them: the plugin
is valid only with it installed, and the platform disables it until then.

## From the command line

```
python -m plugin_platform_wsl_gentoo status
python -m plugin_platform_wsl_gentoo setup            # everything; or: setup docker engine user
python -m plugin_platform_wsl_gentoo run -- docker ps
python -m plugin_platform_wsl_gentoo instances
```

The platform app drives the same hooks from its page. Nothing here is sent anywhere but Docker's and the
distribution's own download servers, when `setup` installs.

## Its check, its install, its updates, its terminal

`check` says whether this PC can install Liminal-Gentoo: Windows that runs WSL 2, WSL installed with its kernel, Gentoo's stage3 found on its mirrors, a processor it is built for (x86-64), 20 GB free on the data folder's drive. The platform's page shows each
criterion and unlocks the install only when every one is met; the install's output shows in a terminal panel as it
runs. Once installed, `update_packages` brings its packages up to date (emerge --sync and an update of @world) and `terminal` opens a login shell
into it on the page.

## Its services

The user's words (2026-11-08): "lets have, in the WSL plugins, a breakdown of the major services running, the 'scanning function' should be capable of using openrc or systemd to look for init type and differentiate between somewhat trivial processes and major services that are online". `services` scans what runs in Liminal-Gentoo, as root, with one script (liminal-libs'
`machines.services`): which init system runs (systemd or OpenRC, or SysV scripts through the service command) and what
PID 1 is; every service it knows with its state; the processes. The major services (Docker, databases, web, mail and
DNS servers, SSH, VPNs, the firewall, Liminal's own apps) are listed with what each is and its memory; a service not
known here is listed with its own description; the system's own (logging, time, devices, D-Bus, logins, package
daemons, the WSL bridge) are counted and named in a note, with any that failed. The platform's page shows the table;
the scan runs only while the distribution runs and is kept 30 s: a status never starts a stopped distribution.

## Its API

The user's words (2026-11-11): "each plugin should reflect the the API its attached to, and present links that provide
documentation, the plugin interface should more or less contain what it already has, BUT, it should also expose more of
what the API is about". Since 0.9.0 (plugin API 2.2) the plugin declares what it attaches to (`apis.py`), and the
platform's page draws each card: what the API is, its links, every part of it (those the plugin uses first, the rest
under "more of the API") and every call it makes, with the API's other notable calls beside them.

- **WSL (wsl.exe)**, Microsoft's: [Basic commands](https://learn.microsoft.com/en-us/windows/wsl/basic-commands),
  [Import any Linux distribution](https://learn.microsoft.com/en-us/windows/wsl/use-custom-distro),
  [wsl.conf and .wslconfig](https://learn.microsoft.com/en-us/windows/wsl/wsl-config),
  [systemd in WSL](https://learn.microsoft.com/en-us/windows/wsl/systemd),
  [releases](https://github.com/microsoft/WSL/releases). Gentoo is not on Microsoft's list: Liminal-Gentoo is imported
  (`wsl --import ... --version 2`), and WSL's own record of each install (its Lxss registry key, which Microsoft
  documents no page for) is read to list them, and written only by Rename.
- **Gentoo's stage3 releases**: [downloads](https://www.gentoo.org/downloads/),
  [the Handbook's stage file](https://wiki.gentoo.org/wiki/Handbook:AMD64/Installation/Stage),
  [Gentoo in WSL](https://wiki.gentoo.org/wiki/Gentoo_in_WSL),
  [the amd64 autobuilds](https://distfiles.gentoo.org/releases/amd64/autobuilds/). Gentoo also publishes a WSL image
  (stage4-amd64-wsl-systemd, for `wsl --install --from-file` on WSL 2.4.10 and later), which the plugin does not use.
- **Portage**: [Portage](https://wiki.gentoo.org/wiki/Portage), [emerge](https://wiki.gentoo.org/wiki/Emerge),
  [Upgrading Gentoo](https://wiki.gentoo.org/wiki/Upgrading_Gentoo).
- **Docker**, as Gentoo packages it: [Docker on Gentoo](https://wiki.gentoo.org/wiki/Docker),
  [app-containers/docker](https://packages.gentoo.org/packages/app-containers/docker); Docker publishes no Gentoo page of
  its own.
- **systemd**, the install's init: [systemctl(1)](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html),
  [machine-id(5)](https://www.freedesktop.org/software/systemd/man/latest/machine-id.html): the services scan, Pause
  (systemd's freezer), and the plugin's own systemd and dns steps.

`api_facts()` says what the plugin kept of them while it ran, asking nothing: Gentoo's newest stage3 as last read,
Docker inside as last seen, the init the last services scan found. Every address on the cards was read on 2026-11-11;
the test `test_the_cards_pages_answer` asks each of them again when `LIMINAL_VENDOR_PAGES=1` is set (it is skipped
otherwise).
