#!/usr/bin/env bash
# Called by wl-paste --watch with the new clipboard content on stdin.
#
# Content that equals the last known state came from the peer a moment ago. Sending it
# back would start an endless ping-pong between the two machines, so it is skipped.
# The state lives in $XDG_RUNTIME_DIR, which only the user can read: the clipboard
# often holds passwords.
set -euo pipefail

peer=${1:?usage: clipboard-push.sh PEER}
state=${XDG_RUNTIME_DIR:?XDG_RUNTIME_DIR is not set}/clipboard-sync
umask 077
mkdir -p "$state"

new=$(mktemp "$state/new.XXXXXX")
trap 'rm -f "$new"' EXIT
cat >"$new"
[[ -s $new ]] || exit 0
cmp -s "$new" "$state/last" && exit 0

cp "$new" "$state/last"
ssh -o BatchMode=yes -o ConnectTimeout=3 "$peer" \
    "${CLIPBOARD_RECV:-.local/bin/clipboard-recv.sh}" <"$new"
