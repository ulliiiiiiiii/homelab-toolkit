#!/usr/bin/env bash
# Keep the Wayland clipboards of two machines in sync over SSH.
#
# Usage: clipboard-sync.sh PEER
#
# Run it on both machines, each naming the other. Needs wl-clipboard on both sides,
# key-based SSH in both directions, and clipboard-recv.sh in ~/.local/bin on the peer.
set -euo pipefail

peer=${1:?usage: clipboard-sync.sh PEER}
here=$(dirname "$(readlink -f "$0")")
exec wl-paste --type text --watch "$here/clipboard-push.sh" "$peer"
