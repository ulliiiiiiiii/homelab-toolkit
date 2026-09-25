# homelab-toolkit

[![CI](https://github.com/ulliiiiiiiii/homelab-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/ulliiiiiiiii/homelab-toolkit/actions/workflows/ci.yml)

Small tools from running two Linux machines at home as one setup. Each one solves a single
problem, runs on its own and needs nothing beyond the usual system tools. There is no shared
framework and no config file for everything.

| Tool | What it does |
| --- | --- |
| [`ssh/ssh-harden.sh`](ssh/ssh-harden.sh) | Switches sshd to key-only logins behind a rollback timer, so a mistake cannot lock you out. |
| [`network/ip-failover.sh`](network/ip-failover.sh) | Keeps one IPv4 address reachable while a machine moves between cable and Wi-Fi. |
| [`network/lan-chat.py`](network/lan-chat.py) | Two-way text chat between two machines, peer to peer. |
| [`clipboard/`](clipboard) | Keeps the Wayland clipboards of two machines in sync over SSH. |
| [`desktop/bounce-screensaver.py`](desktop/bounce-screensaver.py) | Bouncing-image screensaver with one window per monitor. |
| [`desktop/idle-watch.sh`](desktop/idle-watch.sh) | Runs a command when a GNOME session has been idle for a while. |
| [`desktop/touch-bar.py`](desktop/touch-bar.py) | Slide-out button bar for using an X11 desktop by touch. |

Most of them follow the same habits: check before changing anything, keep a way back, and
make a second run harmless.

## ssh-harden

Turning off password logins over SSH is one typo away from locking yourself out of a
machine without a screen. `ssh-harden.sh` changes the order of things:

1. It stops unless every user you name already has a key in `authorized_keys`.
2. It writes a drop-in to `/etc/ssh/sshd_config.d/`, validates it with `sshd -t` and checks
   with `sshd -T` that it actually takes effect.
3. It arms a transient systemd timer that undoes the change after five minutes. If the
   timer cannot be armed, nothing is changed.
4. Only then does it reload sshd. Open sessions stay connected.

```sh
sudo ssh/ssh-harden.sh --no-root-login alice
```

Now log in from a second terminal. If that works, keep the change with
`sudo systemctl stop ssh-harden-rollback.timer`. If it does not, wait five minutes.

## ip-failover

A laptop that gets a fixed address through a DHCP reservation on its cable loses that
address when it goes to Wi-Fi. `ip-failover.sh` adds the address to the wireless interface
while the cable is out and removes it again once the cable is back.

```sh
sudo install -m 755 network/ip-failover.sh /usr/local/sbin/ip-failover.sh
sudo ln -s /usr/local/sbin/ip-failover.sh /etc/NetworkManager/dispatcher.d/50-ip-failover
printf 'ADDRESS=192.168.1.50/24\nWIRED=eth0\nWIRELESS=wlan0\n' | sudo tee /etc/default/ip-failover
```

NetworkManager sometimes drops addresses it did not set itself, so the same script also
runs every 30 seconds from `ip-failover.timer`. Copy the timer and its service to
`/etc/systemd/system/` and enable the timer. Every run compares the current state with the
wanted one and changes only what differs.

## Clipboard sync

```sh
cp clipboard/*.sh ~/.local/bin/
clipboard-sync.sh other-machine    # on both machines, each naming the other
```

`wl-paste --watch` hands every clipboard change to `clipboard-push.sh`, which sends it over
SSH to `clipboard-recv.sh` on the other side. The receiving side records the content before
it sets its own clipboard, so the change is not sent back in an endless loop. That state
lives in `$XDG_RUNTIME_DIR` with owner-only permissions, because the clipboard often holds
passwords. Needs `wl-clipboard` and key-based SSH in both directions.

## Screensaver

`bounce-screensaver.py` opens one fullscreen window per monitor with an image drifting
across it, and closes on any key, click or real mouse movement. It redraws only the area
around the image, five times a second. `idle-watch.sh` starts it after a period without
input. The systemd user unit in [`desktop/idle-watch.service`](desktop/idle-watch.service)
runs the watcher with CPU, memory and process limits, so a stuck screensaver cannot slow
down the machine.

```sh
cp desktop/bounce-screensaver.py desktop/idle-watch.sh ~/.local/bin/
cp desktop/idle-watch.service ~/.config/systemd/user/
systemctl --user enable --now idle-watch.service
```

Needs GNOME (the idle time comes from Mutter) and PyGObject with GTK 3.

## Touch bar

A narrow bar on the right edge with buttons for the on-screen keyboard, page up and down,
copy, paste and right click. It never takes the keyboard focus, so every key it sends
goes to the window you were using. Needs X11, `xdotool` and `onboard`.

## lan-chat

```sh
network/lan-chat.py 10.0.0.2
```

It listens only on the interface that leads to the peer. There is no encryption and no
authentication, so it belongs on a direct cable or a network you trust.

## Development

```sh
shellcheck ssh/*.sh network/*.sh clipboard/*.sh desktop/*.sh
pip install pytest ruff
ruff check . && ruff format --check .
pytest
```

The shell scripts are tested against fake `ip`, `ssh` and `wl-copy` commands, so the tests
need neither root nor a network.

## License

[MIT](LICENSE)
