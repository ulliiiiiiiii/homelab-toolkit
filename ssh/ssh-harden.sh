#!/usr/bin/env bash
# Switch sshd to key-only logins, with an automatic rollback.
#
# Usage: sudo ssh-harden.sh [--no-root-login] USER...
#
# Every USER must already have a key in ~/.ssh/authorized_keys, otherwise nothing is
# changed. The new configuration is validated with `sshd -t`, then a transient systemd
# timer is armed that undoes the change after five minutes, and only then is sshd
# reloaded. Open sessions stay connected.
#
# Log in from a second terminal while the first one stays open. If that works, keep the
# change with `systemctl stop ssh-harden-rollback.timer`. If it does not, do nothing and
# the previous configuration comes back on its own.
set -euo pipefail

readonly DROPIN=/etc/ssh/sshd_config.d/10-key-only.conf
readonly BACKUP=$DROPIN.previous
readonly UNIT=ssh-harden-rollback
readonly DELAY=${SSH_HARDEN_ROLLBACK_AFTER:-300}

die() {
    echo "ssh-harden: $*" >&2
    exit 1
}

no_root_login=0
users=()
for arg in "$@"; do
    case $arg in
        --no-root-login) no_root_login=1 ;;
        -h | --help)
            sed -n '2,13s/^# \{0,1\}//p' "$0"
            exit 0
            ;;
        -*) die "unknown option $arg" ;;
        *) users+=("$arg") ;;
    esac
done
((${#users[@]})) || die "name at least one user who has to keep access"
((EUID == 0)) || die "run as root"

for user in "${users[@]}"; do
    home=$(getent passwd "$user" | cut -d: -f6) || die "unknown user $user"
    keys=$(grep -cvE '^[[:space:]]*(#|$)' "$home/.ssh/authorized_keys" 2>/dev/null || true)
    ((${keys:-0} > 0)) || die "$user has no key in $home/.ssh/authorized_keys and would be locked out"
    echo "$user: $keys key(s)"
done

if systemctl is-active --quiet "$UNIT.timer"; then
    die "a rollback is still pending, confirm or wait for it before running this again"
fi
systemctl reset-failed "$UNIT.timer" "$UNIT.service" 2>/dev/null || true

service=ssh
systemctl cat ssh.service >/dev/null 2>&1 || service=sshd

rm -f "$BACKUP"
if [[ -e $DROPIN ]]; then
    cp -p "$DROPIN" "$BACKUP"
fi
undo="if [ -e $BACKUP ]; then mv -f $BACKUP $DROPIN; else rm -f $DROPIN; fi"

{
    echo "# Written by ssh-harden.sh: logins with a key only."
    echo "PasswordAuthentication no"
    echo "KbdInteractiveAuthentication no"
    echo "AuthenticationMethods publickey"
    if ((no_root_login)); then
        echo "PermitRootLogin no"
    fi
} >"$DROPIN"

if ! sshd -t; then
    sh -c "$undo"
    die "sshd rejected the new configuration, nothing changed"
fi
if ! sshd -T | grep -qx 'passwordauthentication no'; then
    sh -c "$undo"
    die "the drop-in has no effect, sshd_config has to include sshd_config.d/*.conf at the top"
fi

# The safety net goes up before the change becomes active. Without it, stop here.
if ! systemd-run --quiet --on-active="$DELAY" --unit="$UNIT" \
    --description="Undo ssh-harden.sh" /bin/sh -c "$undo; systemctl reload $service"; then
    sh -c "$undo"
    die "could not arm the rollback timer, nothing changed"
fi
systemctl reload "$service"

cat <<EOF

Key-only logins are active and undo themselves in $((DELAY / 60)) minutes.
Test a new login from a second terminal now and keep this one open.
  it works:      systemctl stop $UNIT.timer
  it does not:   do nothing, the previous configuration comes back on its own
EOF
