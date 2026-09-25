#!/usr/bin/env python3
"""Slide-out button bar on the right screen edge for using an X11 desktop by touch.

Buttons: on-screen keyboard, page up and down (repeat while held), copy, paste and a
right click at the last pointer position outside the bar. The bar never takes the
focus, so every key it sends lands in the window that was active before. Needs
xdotool and, for the keyboard button, onboard.
"""

from __future__ import annotations

import contextlib
import subprocess
from collections.abc import Callable

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

REPEAT_MS = 150
CSS = b"""
window { background-color: rgba(18, 18, 22, 0.92); }
button {
    color: #ffffff; font-size: 16px; font-weight: bold; background-image: none;
    background-color: rgba(74, 74, 86, 0.95); border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 10px; padding: 2px;
}
button:active { background-color: rgba(130, 130, 155, 0.98); }
"""
TOGGLE_KEYBOARD = [
    "dbus-send", "--type=method_call", "--dest=org.onboard.Onboard",
    "/org/onboard/Onboard/Keyboard", "org.onboard.Onboard.Keyboard.ToggleVisible",
]  # fmt: skip
UP, DOWN, SLIDE_IN, SLIDE_OUT = "▲", "▼", "▸", "◂"


def run(command: list[str]) -> None:
    # a missing tool must not take the bar down
    with contextlib.suppress(OSError):
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def key(name: str) -> Callable[[], None]:
    return lambda: run(["xdotool", "key", "--clearmodifiers", name])


# label, tooltip, action, repeat while held
BUTTONS: list[tuple[str, str, Callable[[], None], bool]] = [
    ("Keyboard", "Show or hide the on-screen keyboard", lambda: run(TOGGLE_KEYBOARD), False),
    (UP, "Page up", key("Page_Up"), True),
    (DOWN, "Page down", key("Page_Down"), True),
    ("Copy", "Copy (Ctrl+C)", key("ctrl+c"), False),
    ("Paste", "Paste (Ctrl+V)", key("ctrl+v"), False),
]


class TouchBar(Gtk.Window):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.stick()
        self.repeat_id = 0
        self.pointer: tuple[int, int] | None = None

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        outer.set_border_width(6)
        self.add(outer)
        self.toggle = Gtk.Button(label=SLIDE_IN)
        self.toggle.set_size_request(88, 34)
        self.toggle.set_tooltip_text("Slide the bar in or out")
        self.toggle.connect("clicked", self.on_toggle)
        outer.pack_start(self.toggle, False, False, 0)

        self.buttons = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        outer.pack_start(self.buttons, False, False, 0)
        for label, tooltip, action, repeat in BUTTONS:
            button = self.add_button(label, tooltip)
            if repeat:
                button.connect("button-press-event", self.on_press, action)
                button.connect("button-release-event", self.on_release)
            else:
                button.connect("button-press-event", self.on_tap, action)
        right_click = self.add_button("Right\nclick", "Right click where the pointer was")
        right_click.connect("button-press-event", self.on_right_click)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        GLib.timeout_add(100, self.track_pointer)
        self.connect("destroy", Gtk.main_quit)
        self.connect("size-allocate", lambda *_: self.reposition())

    def add_button(self, label: str, tooltip: str) -> Gtk.Button:
        text = Gtk.Label(label=label)
        text.set_justify(Gtk.Justification.CENTER)
        button = Gtk.Button()
        button.add(text)
        button.set_size_request(88, 74)
        button.set_tooltip_text(tooltip)
        self.buttons.pack_start(button, False, False, 0)
        return button

    def on_tap(self, _button: object, _event: object, action: Callable[[], None]) -> bool:
        action()
        return True

    def on_press(self, _button: object, _event: object, action: Callable[[], None]) -> bool:
        action()
        if self.repeat_id:
            GLib.source_remove(self.repeat_id)
        self.repeat_id = GLib.timeout_add(REPEAT_MS, self.repeat, action)
        return True

    def repeat(self, action: Callable[[], None]) -> bool:
        action()
        return True

    def on_release(self, *_: object) -> bool:
        if self.repeat_id:
            GLib.source_remove(self.repeat_id)
            self.repeat_id = 0
        return True

    def track_pointer(self) -> bool:
        # remember where the pointer was last seen outside the bar, a right click
        # belongs there
        pointer = Gdk.Display.get_default().get_default_seat().get_pointer()
        _screen, x, y = pointer.get_position()
        left, top = self.get_position()
        width, height = self.get_size()
        if not (left - 4 <= x <= left + width + 4 and top - 4 <= y <= top + height + 4):
            self.pointer = (x, y)
        return True

    def on_right_click(self, *_: object) -> bool:
        if self.pointer is None:
            key("Menu")()
        else:
            x, y = self.pointer
            run(["xdotool", "mousemove", "--sync", str(x), str(y), "click", "3"])
        return True

    def on_toggle(self, *_: object) -> None:
        if self.buttons.get_visible():
            self.buttons.hide()
            self.toggle.set_label(SLIDE_OUT)
        else:
            self.buttons.show_all()
            self.toggle.set_label(SLIDE_IN)
        GLib.idle_add(self.reposition)

    def reposition(self) -> bool:
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        area = monitor.get_geometry()
        width, height = self.get_size()
        self.move(area.x + area.width - width, area.y + (area.height - height) // 2)
        return False


if __name__ == "__main__":
    bar = TouchBar()
    bar.show_all()
    bar.reposition()
    Gtk.main()
