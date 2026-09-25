import pytest

SCRIPT = "network/ip-failover.sh"
ADDRESS_LINE = "3: wlan0    inet 192.168.1.50/24 brd 192.168.1.255 scope global secondary wlan0"


@pytest.fixture
def network(sandbox):
    config = sandbox.root / "ip-failover"
    config.write_text("ADDRESS=192.168.1.50/24\nWIRED=eth0\nWIRELESS=wlan0\n")
    sysfs = sandbox.root / "sys"
    (sysfs / "eth0").mkdir(parents=True)
    sandbox.fake(
        "ip",
        'echo "$*" >> "$LOG/ip"\n'
        f'if [ "$4" = show ] && [ -n "$ON_WIRELESS" ]; then echo "{ADDRESS_LINE}"; fi',
    )
    sandbox.fake("logger", 'echo "$*" >> "$LOG/logger"')

    def run(carrier, on_wireless):
        if carrier is not None:
            (sysfs / "eth0" / "carrier").write_text(f"{carrier}\n")
        result = sandbox.run(
            SCRIPT,
            IP_FAILOVER_CONFIG=str(config),
            IP_FAILOVER_SYSFS=str(sysfs),
            ON_WIRELESS="1" if on_wireless else "",
        )
        assert result.returncode == 0, result.stderr
        calls = (sandbox.log / "ip").read_text().splitlines()
        return [call for call in calls if " show " not in f" {call} "]

    return run


@pytest.mark.parametrize(
    ("carrier", "on_wireless", "changes"),
    [
        (1, True, ["addr del 192.168.1.50/24 dev wlan0"]),
        (1, False, []),
        (0, False, ["addr add 192.168.1.50/24 dev wlan0"]),
        (0, True, []),
        (None, False, ["addr add 192.168.1.50/24 dev wlan0"]),
    ],
    ids=["cable back", "cable in", "cable out", "already moved", "no wired interface"],
)
def test_moves_the_address_only_when_needed(network, carrier, on_wireless, changes):
    assert network(carrier, on_wireless) == changes


def test_missing_settings_stop_the_script(sandbox):
    config = sandbox.root / "ip-failover"
    config.write_text("ADDRESS=192.168.1.50/24\n")
    result = sandbox.run(SCRIPT, IP_FAILOVER_CONFIG=str(config))
    assert result.returncode != 0
    assert "WIRED is not set" in result.stderr
