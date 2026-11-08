# Changelog

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
