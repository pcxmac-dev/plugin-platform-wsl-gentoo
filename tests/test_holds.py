"""0.10.0, on liminal-libs 1.96.0: what a container plugin asks of this plugin (hold and let_go, its alone; wsl_network,
anyone's read), the one-engine check, and every change asked from the page alone. Through a stand-in wsl command:
nothing runs here, and a stopped distribution is never started."""
from __future__ import annotations

import pytest

from liminal_libs import internal
from liminal_libs.apps import asking
from liminal_libs.instances import Refusal
from liminal_libs.machines.wsl import Asked, Wsl
from plugin_platform_wsl_gentoo import MACHINE, WslGentooPlugin

from test_plugin import FakeWsl

NAME = "Liminal-Gentoo"


class Session:
    def __init__(self):
        self.ended = False

    def poll(self):
        return None

    def terminate(self):
        self.ended = True


def plugin(state, tmp_path):
    fake = FakeWsl(distributions=[(NAME, state, "2")])
    spawned = []
    p = WslGentooPlugin(wsl=Wsl(runner=fake, registry=lambda: [], spawn=lambda a: spawned.append(Session()) or spawned[-1]),
             data=tmp_path)
    p.WSLCONFIG = tmp_path / ".wslconfig"
    return p, fake, spawned


def test_a_container_plugin_alone_holds_it_and_anyone_reads_wsls_network():
    assert set(internal.plugin_only(MACHINE)) == {"hold", "let_go"}
    assert {"uninstall", "start_install", "stop_install", "update_packages", "rename_install", "pick_install",
            "pause_install", "terminal"} <= set(internal.page_only(MACHINE))
    for who in ("docker", asking.PAGE, None):
        assert asking.refusal(MACHINE, "wsl_network", who) == ""
    assert asking.refusal(MACHINE, "hold", asking.PAGE) != "" and asking.refusal(MACHINE, "uninstall", "docker") != ""
    assert [p for p in internal.problems(MACHINE) if "ONLY_HOOKS" in p] == []


def test_a_hold_never_starts_it(tmp_path):
    p, fake, spawned = plugin("Stopped", tmp_path)
    with asking.asking("docker"), pytest.raises(Refusal, match="never starts"):
        p.hold(NAME)
    assert spawned == [] and not any(c[1] == "-d" for c in fake.calls)
    assert p.wsl_network()["vm_address"] == "" and not any(c[1] == "-d" for c in fake.calls)


def test_one_session_for_its_holders_and_stop_asked_twice_while_held(tmp_path):
    p, fake, spawned = plugin("Running", tmp_path)
    with asking.asking("docker"):
        p.hold(NAME)
    assert len(spawned) == 1 and p.held_by(NAME) == ["docker"]
    with pytest.raises(Asked, match="docker"):
        p.stop_install(NAME)
    with asking.asking("docker"):
        p.let_go(NAME)
    assert spawned[0].ended and p.held_by(NAME) == []


def test_starting_beside_another_engine_is_asked_twice(tmp_path, monkeypatch):
    p, fake, spawned = plugin("Stopped", tmp_path)
    monkeypatch.setattr(p, "engines_elsewhere", lambda: ["Liminal-Other"])
    with pytest.raises(Asked, match="Liminal-Other"):
        p.start_install(NAME)
    assert spawned == []
