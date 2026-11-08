# plugin-platform-wsl-gentoo

WSL Gentoo for Liminal: Gentoo in WSL 2 on this Windows PC, set up by the plugin,
with Docker inside, offered to the framework as the Docker instance `wsl-gentoo`.

The user's words (2026-11-07): "the platform is the interface for the software/hardware which facilitates the
liminal framework"; "the scope of the plugin is setting up WSL/Ubuntu and supporting docker for the
platform"; "the ubuntu plugin needs to be able to install docker (do everything manually) and allow
different docker instances to support the liminal framework"; "then create a gentoo and fedora plugin as
well, same scope/function".

## What it does

A machine plugin of the platform (`liminal_libs.machines.MachinePlugin`, plugin API 2.1), the library's
`WslDistribution` with this distribution's name and family. Its hooks:

- `present()`: whether the distribution is installed in WSL.
- `status()`: WSL itself, the distribution's state and version, the default user, Docker inside (installed,
  its version, the daemon answering).
- `setup()`: everything, step by step, each reported: WSL itself (`wsl --install --no-distribution`; Windows
  asks to confirm with elevation and may want a restart), `wsl --update`, WSL 2 as the default, the
  distribution (imported with `wsl --import Gentoo` from the latest amd64 systemd stage3 tarball of Gentoo's own mirrors (downloaded into the data folder's platform/wsl/wsl-gentoo); Docker by emerge (app-containers/docker, docker-cli, docker-buildx, docker-compose), which compiles and takes a while.), `/etc/wsl.conf` with systemd on and the default user `liminal`
  (WSL_GENTOO_USER) made when absent, Docker installed, the engine started and enabled (systemd, else
  OpenRC, else `service`), the user in the docker group. Everything inside runs as root through `wsl -u
  root`, so no password is asked. A step can be run alone: `setup docker`.
- `run(command)`: a command in the distribution.
- `instances()`: the engine as the Docker instance `wsl-gentoo`, reached as `wsl -d Gentoo docker`,
  Windows paths under `/mnt`; a login file's `[server] instance = wsl-gentoo` runs its mail server there, and
  `liminal_libs.docker.instance("wsl-gentoo")` gives any app the engine.

Variables: `WSL_GENTOO_DISTRIBUTION` (the WSL name, `Gentoo` unless said), `WSL_GENTOO_USER`.

## From the command line

```
python -m plugin_platform_wsl_gentoo status
python -m plugin_platform_wsl_gentoo setup            # everything; or: setup docker engine user
python -m plugin_platform_wsl_gentoo run -- docker ps
python -m plugin_platform_wsl_gentoo instances
```

The platform app drives the same hooks from its page. Nothing here is sent anywhere but Docker's and the
distribution's own download servers, when `setup` installs.
