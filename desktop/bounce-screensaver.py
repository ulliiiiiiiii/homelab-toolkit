#!/usr/bin/env python3
"""Bouncing-image screensaver with one window per monitor.

Usage: bounce-screensaver.py IMAGE [--size PX] [--speed PX] [--dim FACTOR]

Any key, click or real mouse movement on any monitor closes it. Only the area around
the image is redrawn, five times a second, so the load stays negligible.
"""

from __future__ import annotations

import argparse
import os
import time
from typing import Any

FRAME_MS = 200
MOTION_GRACE_S = 0.5


def step(position: float, velocity: float, size: float, limit: float) -> tuple[float, float]:
    """Move along one axis by one frame and bounce off both edges."""
    position += velocity
    if position <= 0 or position + size >= limit:
        velocity = -velocity
        position = max(0.0, min(position, limit - size))
    return position, velocity


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bouncing-image screensaver.")
    parser.add_argument("image")
    parser.add_argument("--size", type=int, default=360, help="image size in pixels")
    parser.add_argument("--speed", type=float, default=2.1, help="pixels per frame")
    parser.add_argument("--dim", type=float, default=0.8, help="image brightness, 0 to 1")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    # Wayland clients cannot place their own windows, and one window per monitor needs
    # exactly that. Through XWayland, GTK can.
    os.environ.setdefault("GDK_BACKEND", "x11")
    import gi

    gi.require_version("Gdk", "3.0")
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

    class Bounce(Gtk.Window):  # type: ignore[misc]
        def __init__(self, index: int, geometry: Any, image: Any) -> None:
            super().__init__()
            self.index = index
            self.set_decorated(False)
            self.set_app_paintable(True)
            self.set_keep_above(True)
            self.move(geometry.x, geometry.y)
            self.set_default_size(geometry.width, geometry.height)
            self.image = image
            self.width, self.height = image.get_width(), image.get_height()
            # every monitor starts at another spot and heads another way
            self.x, self.y = 100.0 + 300 * index, 100.0 + 150 * index
            self.dx, self.dy = (args.speed if index % 2 == 0 else -args.speed), args.speed
            self.mapped_at: float | None = None
            self.connect("map-event", self.on_map)
            self.connect("draw", self.on_draw)
            self.connect("key-press-event", Gtk.main_quit)
            self.connect("button-press-event", Gtk.main_quit)
            self.connect("motion-notify-event", self.on_motion)
            self.add_events(
                Gdk.EventMask.KEY_PRESS_MASK
                | Gdk.EventMask.BUTTON_PRESS_MASK
                | Gdk.EventMask.POINTER_MOTION_MASK
            )

        def on_map(self, *_: object) -> None:
            self.fullscreen_on_monitor(self.get_screen(), self.index)
            if self.mapped_at is None:
                GLib.timeout_add(FRAME_MS, self.tick)
            self.mapped_at = time.monotonic()

        def on_draw(self, _widget: object, cr: Any) -> bool:
            cr.set_source_rgb(0, 0, 0)
            cr.paint()
            Gdk.cairo_set_source_pixbuf(cr, self.image, self.x, self.y)
            cr.paint()
            # a translucent black square over the image is far cheaper than recolouring it
            cr.set_source_rgba(0, 0, 0, 1 - args.dim)
            cr.rectangle(self.x, self.y, self.width, self.height)
            cr.fill()
            return False

        def tick(self) -> bool:
            old_x, old_y = self.x, self.y
            self.x, self.dx = step(self.x, self.dx, self.width, self.get_allocated_width())
            self.y, self.dy = step(self.y, self.dy, self.height, self.get_allocated_height())
            # redraw the old and the new position only, not the whole monitor
            left, top = int(min(old_x, self.x)) - 2, int(min(old_y, self.y)) - 2
            right = int(max(old_x, self.x)) + self.width + 2
            bottom = int(max(old_y, self.y)) + self.height + 2
            self.queue_draw_area(left, top, right - left, bottom - top)
            return True

        def on_motion(self, *_: object) -> None:
            # Mapping a window under the pointer produces a burst of synthetic motion
            # events. Only movement after a short grace period counts as input.
            if self.mapped_at is not None and time.monotonic() - self.mapped_at > MOTION_GRACE_S:
                Gtk.main_quit()

    display = Gdk.Display.get_default()
    image = GdkPixbuf.Pixbuf.new_from_file_at_scale(args.image, args.size, args.size, True)
    windows = [
        Bounce(index, display.get_monitor(index).get_geometry(), image)
        for index in range(display.get_n_monitors())
    ]
    for window in windows:
        window.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
