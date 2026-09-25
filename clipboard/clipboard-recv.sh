#!/usr/bin/env bash
# Receives clipboard content from the peer on stdin.
#
# The content becomes the last known state before it reaches the clipboard, so the
# local watcher recognises it and does not send it back.
set -euo pipefail

state=${XDG_RUNTIME_DIR:?XDG_RUNTIME_DIR is not set}/clipboard-sync
umask 077
mkdir -p "$state"

incoming=$(mktemp "$state/in.XXXXXX")
cat >"$incoming"
mv -f "$incoming" "$state/last"

# wl-copy keeps serving the clipboard in the background. Without the redirections it
# would hold the SSH session open until the clipboard changes again.
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}
wl-copy --type text/plain <"$state/last" >/dev/null 2>&1
