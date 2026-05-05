# mpris-skip

Watches all MPRIS media players on the D-Bus session bus and calls `Next()` whenever the current track title matches a given regex pattern. Useful for automatically skipping tracks in Spotify's radio and mixtape mode or any other MPRIS-compatible application.

## Usage

```
mpris-skip PATTERN [--dry-run] [--verbose]
```

`PATTERN` is a Python regex matched case-insensitively against the track title.

```bash
# Skip tracks that are part of an "Above & Beyond Group Therapy" or a "A State of Trance" mix set that are often interrupted by the DJ with anouncements.
mpris-skip 'ABGT|ASOT'
```

On startup, all currently playing players are checked immediately. Afterwards, the tool listens for `PropertiesChanged` signals and reacts in real time.

## Installation

### System dependencies

This project requires two system-level libraries that must be installed via your OS package manager, as they bind to C libraries and cannot be installed through pip or uv.

**Fedora / RHEL:**

```bash
sudo dnf install python3-dbus python3-gobject
```

**Debian / Ubuntu:**

```bash
sudo apt install python3-dbus python3-gi
```

**Arch Linux:**

```bash
sudo pacman -S python-dbus python-gobject
```

### Installing mpris-skip

With [uv](https://docs.astral.sh/uv/):

```bash
uv tool install .
```

Or into a virtualenv (make sure the system packages above are visible to it):

```bash
pip install .
```

## Requirements

- Python ≥ 3.14
- A running D-Bus session bus (standard on any Linux desktop)
- An MPRIS-capable media player
