#!/usr/bin/env bash
# Run a command whenever a GNOME session has been idle for a while.
#
# Usage: idle-watch.sh [-t SECONDS] COMMAND [ARG...]
#
# Asks Mutter's idle monitor every five seconds. The command starts at most once per
# idle period: if it exits without any input (a crash, a stray event), it only starts
# again after the user has been active in between. flock keeps it from running twice.
set -euo pipefail

timeout=1800
while getopts t:h option; do
    case $option in
        t) timeout=$OPTARG ;;
        h)
            sed -n '2,8s/^# \{0,1\}//p' "$0"
            exit 0
            ;;
        *) exit 2 ;;
    esac
done
shift $((OPTIND - 1))
(($#)) || {
    echo "usage: idle-watch.sh [-t SECONDS] COMMAND [ARG...]" >&2
    exit 2
}

lock=${XDG_RUNTIME_DIR:?XDG_RUNTIME_DIR is not set}/idle-watch.lock
armed=1

idle_ms() {
    # The reply looks like "(uint64 305144,)". Take the number after "uint64 ", since a
    # plain [0-9]+ would also match the 64 in the type name.
    gdbus call --session --dest org.gnome.Mutter.IdleMonitor \
        --object-path /org/gnome/Mutter/IdleMonitor/Core \
        --method org.gnome.Mutter.IdleMonitor.GetIdletime 2>/dev/null |
        grep -oP 'uint64 \K[0-9]+' || true
}

while sleep 5; do
    ms=$(idle_ms)
    [[ -n $ms ]] || continue
    if ((ms < timeout * 1000)); then
        armed=1
    elif ((armed)); then
        armed=0
        flock -n "$lock" "$@" || true
    fi
done
