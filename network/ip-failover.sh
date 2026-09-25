#!/usr/bin/env bash
# Keep one IPv4 address reachable when a machine moves between cable and Wi-Fi.
#
# The address normally belongs to the wired interface, for example through a DHCP
# reservation. Without a cable it is added to the wireless interface as a second
# address, and removed from there as soon as the cable is back.
#
# Install it as a NetworkManager dispatcher script. NetworkManager sometimes drops
# addresses it did not configure itself, so run it from a timer as well. Each run
# compares the current state with the wanted one, which makes repeated runs harmless.
#
# Settings in /etc/default/ip-failover:
#   ADDRESS=192.168.1.50/24
#   WIRED=eth0
#   WIRELESS=wlan0
set -euo pipefail

config=${IP_FAILOVER_CONFIG:-/etc/default/ip-failover}
sysfs=${IP_FAILOVER_SYSFS:-/sys/class/net}
# shellcheck source=/dev/null
source "$config"
: "${ADDRESS:?ADDRESS is not set in $config}"
: "${WIRED:?WIRED is not set in $config}"
: "${WIRELESS:?WIRELESS is not set in $config}"

cable_plugged() {
    [[ $(cat "$sysfs/$WIRED/carrier" 2>/dev/null) == 1 ]]
}

on_wireless() {
    ip -4 -o addr show dev "$WIRELESS" 2>/dev/null | grep -qF "inet $ADDRESS "
}

if cable_plugged; then
    if on_wireless; then
        ip addr del "$ADDRESS" dev "$WIRELESS"
        logger -t ip-failover "cable on $WIRED is back, removed $ADDRESS from $WIRELESS"
    fi
elif ! on_wireless; then
    ip addr add "$ADDRESS" dev "$WIRELESS"
    logger -t ip-failover "no cable on $WIRED, added $ADDRESS to $WIRELESS"
fi
