"""
Skip MPRIS media tracks whose title matches a regex pattern.

Watches D-Bus PropertiesChanged signals from all MPRIS players and calls
Next() whenever the track title matches the given pattern.
"""

import re
import sys
import argparse
import logging

import dbus
import dbus.mainloop.glib
from gi.repository import GLib


log = logging.getLogger(__name__)

MPRIS_PREFIX = "org.mpris.MediaPlayer2."
MPRIS_PATH = "/org/mpris/MediaPlayer2"
MPRIS_PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
PROPS_IFACE = "org.freedesktop.DBus.Properties"


def skip_track(bus: dbus.SessionBus, sender: str, title: str, dry_run: bool) -> None:
    log.info("Title %r matches — skipping", title)
    if dry_run:
        log.info("(dry-run) would call Next() on %s", sender)
        return
    try:
        obj = bus.get_object(sender, MPRIS_PATH)
        player = dbus.Interface(obj, MPRIS_PLAYER_IFACE)
        player.Next()
    except dbus.DBusException as exc:
        log.error("Failed to call Next() on %s: %s", sender, exc)


def check_metadata(
    bus: dbus.SessionBus,
    regex: re.Pattern,
    metadata: dbus.Dictionary,
    sender: str,
    dry_run: bool,
) -> None:
    title = str(metadata.get("xesam:title", ""))
    if not title:
        return
    artists = [str(a) for a in metadata.get("xesam:artist", [])]
    artist_str = ", ".join(artists)
    log.debug("Now playing: %r by %r (from %s)", title, artist_str, sender)
    if regex.search(title):
        skip_track(bus, sender, title, dry_run)


def make_signal_handler(bus: dbus.SessionBus, regex: re.Pattern, dry_run: bool):
    def on_properties_changed(
        interface_name,
        changed_properties,
        invalidated_properties,
        sender=None,
    ):
        if interface_name != MPRIS_PLAYER_IFACE:
            return
        if "Metadata" not in changed_properties:
            return
        check_metadata(bus, regex, changed_properties["Metadata"], sender, dry_run)

    return on_properties_changed


def check_all_current_players(bus: dbus.SessionBus, regex: re.Pattern, dry_run: bool) -> None:
    """Check whatever is already playing when we start up."""
    try:
        dbus_obj = bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus")
        names = dbus_obj.ListNames(dbus_interface="org.freedesktop.DBus")
    except dbus.DBusException as exc:
        log.warning("Could not list bus names: %s", exc)
        return

    for name in names:
        if not str(name).startswith(MPRIS_PREFIX):
            continue
        try:
            obj = bus.get_object(name, MPRIS_PATH)
            props = dbus.Interface(obj, PROPS_IFACE)
            metadata = props.Get(MPRIS_PLAYER_IFACE, "Metadata")
            check_metadata(bus, regex, metadata, str(name), dry_run)
        except dbus.DBusException as exc:
            log.debug("Could not read metadata from %s: %s", name, exc)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Skip MPRIS tracks whose title matches a regex.",
        epilog="Example: mpris-skip 'advertisement|spotify ad'",
    )
    parser.add_argument("pattern", help="Python regex matched against the track title (case-insensitive)")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Log matches but do not call Next()")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show every track change")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        regex = re.compile(args.pattern, re.IGNORECASE)
    except re.error as exc:
        log.error("Invalid regex %r: %s", args.pattern, exc)
        sys.exit(1)

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()

    handler = make_signal_handler(bus, regex, args.dry_run)
    bus.add_signal_receiver(
        handler,
        signal_name="PropertiesChanged",
        dbus_interface=PROPS_IFACE,
        path=MPRIS_PATH,
        sender_keyword="sender",
    )

    log.info("Watching all MPRIS players for titles matching %r%s", args.pattern, "  [dry-run]" if args.dry_run else "")
    check_all_current_players(bus, regex, args.dry_run)

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        log.info("Stopped.")


if __name__ == "__main__":
    main()
