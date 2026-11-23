#!/usr/bin/env python3
"""
cardputer-statusd - feeds Raspberry Pi status + notifications to the Cardputer deck screen.

USB mode  (default): Cardputer is a USB HID keyboard (handled by Linux natively) and a
                     CDC serial port (/dev/cardputer via udev rule). We only send status.
UART mode (--uart):  Cardputer is wired to the Pi 5 UART JST (/dev/ttyAMA10). It sends
                     "K|mods|keys" frames and we inject them as a virtual keyboard (uinput).

Notifications in:  UDP 127.0.0.1:47800, payload "app|summary|body" or JSON
                   {"app":..,"summary":..,"body":..}. See `cardputer-notify`.
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import time

import serial  # apt: python3-serial

NOTIFY_ADDR = ("127.0.0.1", 47800)


# ------------------------------------------------------------------ system stats
class Stats:
    def __init__(self):
        self._prev = self._cpu_times()

    @staticmethod
    def _cpu_times():
        with open("/proc/stat") as f:
            vals = [int(v) for v in f.readline().split()[1:]]
        idle = vals[3] + vals[4]  # idle + iowait
        return idle, sum(vals)

    def cpu(self):
        idle, total = self._cpu_times()
        pidle, ptotal = self._prev
        self._prev = (idle, total)
        dt = total - ptotal
        return 0 if dt <= 0 else round(100 * (1 - (idle - pidle) / dt))

    @staticmethod
    def temp():
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                return int(f.read()) / 1000
        except OSError:
            return 0.0

    @staticmethod
    def ram():
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":", 1)
                info[k] = int(v.split()[0])
        return round(100 * (1 - info["MemAvailable"] / info["MemTotal"]))

    @staticmethod
    def disk():
        s = os.statvfs("/")
        return round(100 * (1 - s.f_bavail / s.f_blocks))

    @staticmethod
    def ip():
        try:
            out = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=2).stdout
            return out.split()[0] if out.split() else "offline"
        except Exception:
            return "?"

    @staticmethod
    def uptime():
        with open("/proc/uptime") as f:
            secs = int(float(f.read().split()[0]))
        d, rem = divmod(secs, 86400)
        h, m = divmod(rem // 60, 60)
        return f"{d}d{h:02d}h" if d else f"{h}h{m:02d}m"

    @staticmethod
    def load():
        with open("/proc/loadavg") as f:
            return f.read().split()[0]


def clean(s, limit=120):
    """Strip characters that would break the line protocol."""
    return " ".join(str(s).replace("|", "/").split())[:limit]


def throttled_bits():
    """Pi firmware throttle flags (bit0 undervolt, bit1 freq cap, bit2 throttled, bit3 temp)."""
    try:
        out = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=2).stdout
        return int(out.strip().split("=")[1], 16) & 0xF
    except Exception:
        return 0


# ------------------------------------------------------------------ uinput (UART mode)
class VirtualKeyboard:
    HID_TO_KEY = {}

    def __init__(self):
        from evdev import UInput, ecodes as e  # apt: python3-evdev
        self.e = e
        m = {i + 0x04: getattr(e, f"KEY_{chr(ord('A') + i)}") for i in range(26)}
        m.update({0x1E + i: getattr(e, f"KEY_{i + 1}") for i in range(9)})
        m.update({0x3A + i: getattr(e, f"KEY_F{i + 1}") for i in range(12)})
        names = {0x27: "0", 0x28: "ENTER", 0x29: "ESC", 0x2A: "BACKSPACE", 0x2B: "TAB",
                 0x2C: "SPACE", 0x2D: "MINUS", 0x2E: "EQUAL", 0x2F: "LEFTBRACE",
                 0x30: "RIGHTBRACE", 0x31: "BACKSLASH", 0x33: "SEMICOLON", 0x34: "APOSTROPHE",
                 0x35: "GRAVE", 0x36: "COMMA", 0x37: "DOT", 0x38: "SLASH", 0x39: "CAPSLOCK",
                 0x46: "SYSRQ", 0x49: "INSERT", 0x4A: "HOME", 0x4B: "PAGEUP", 0x4C: "DELETE",
                 0x4D: "END", 0x4E: "PAGEDOWN", 0x4F: "RIGHT", 0x50: "LEFT", 0x51: "DOWN",
                 0x52: "UP"}
        m.update({k: getattr(e, f"KEY_{v}") for k, v in names.items()})
        self.map = m
        self.mods = [e.KEY_LEFTCTRL, e.KEY_LEFTSHIFT, e.KEY_LEFTALT, e.KEY_LEFTMETA,
                     e.KEY_RIGHTCTRL, e.KEY_RIGHTSHIFT, e.KEY_RIGHTALT, e.KEY_RIGHTMETA]
        keys = list(m.values()) + self.mods
        self.ui = UInput({e.EV_KEY: keys}, name="Cardputer Deck Keyboard")
        self.down = set()

    def report(self, mods, hid_keys):
        now = {self.mods[b] for b in range(8) if mods & (1 << b)}
        now |= {self.map[k] for k in hid_keys if k in self.map}
        for k in self.down - now:
            self.ui.write(self.e.EV_KEY, k, 0)
        for k in now - self.down:
            self.ui.write(self.e.EV_KEY, k, 1)
        self.ui.syn()
        self.down = now


# ------------------------------------------------------------------ main loop
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", help="serial port (default /dev/cardputer, or /dev/ttyAMA10 with --uart)")
    ap.add_argument("--uart", action="store_true", help="wired UART mode with uinput keyboard")
    ap.add_argument("--interval", type=float, default=2.0)
    args = ap.parse_args()
    port = args.port or ("/dev/ttyAMA10" if args.uart else "/dev/cardputer")

    kbd = VirtualKeyboard() if args.uart else None
    notify_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    notify_sock.bind(NOTIFY_ADDR)
    notify_sock.setblocking(False)

    stats = Stats()
    host = clean(socket.gethostname(), 16)
    last_throttle = 0
    ser = None
    rx = b""
    next_status = 0.0

    while True:
        if ser is None:
            try:
                ser = serial.Serial(port, 115200, timeout=0.05)
                print(f"connected to {port}", flush=True)
                rx = b""
                next_status = 0.0
            except (serial.SerialException, OSError):
                time.sleep(2)
                continue
        try:
            now = time.monotonic()
            out = []
            if now >= next_status:
                next_status = now + args.interval
                out.append(f"S|{host}|{stats.ip()}|{stats.cpu()}|{stats.temp():.1f}|{stats.ram()}|"
                           f"{stats.disk()}|{stats.uptime()}|{time.strftime('%H:%M')}|{stats.load()}")
                bits = throttled_bits()
                if bits and not last_throttle:
                    why = "Under-voltage! Use a 5V/5A PSU" if bits & 1 else "CPU throttled (heat)"
                    out.append(f"N|system|Power/Thermal|{why}")
                last_throttle = bits

            while True:
                try:
                    data, _ = notify_sock.recvfrom(2048)
                except BlockingIOError:
                    break
                text = data.decode("utf-8", "replace").strip()
                try:
                    j = json.loads(text)
                    app, summ, body = j.get("app", "notify"), j.get("summary", ""), j.get("body", "")
                except (ValueError, AttributeError):
                    parts = (text.split("|", 2) + ["", ""])[:3]
                    app, summ, body = parts
                out.append(f"N|{clean(app, 24)}|{clean(summ, 60)}|{clean(body, 200)}")

            for line in out:
                ser.write((line + "\n").encode("utf-8", "replace"))

            rx += ser.read(256)
            while b"\n" in rx:
                line, rx = rx.split(b"\n", 1)
                line = line.decode("ascii", "ignore").strip()
                if kbd and line.startswith("K|"):
                    _, mods, keys = (line.split("|") + [""])[:3]
                    kbd.report(int(mods, 16), [int(k, 16) for k in keys.split(",") if k])
        except (serial.SerialException, OSError) as exc:
            print(f"link lost: {exc}", file=sys.stderr, flush=True)
            try:
                ser.close()
            except Exception:
                pass
            ser = None
            if kbd:
                kbd.report(0, [])  # release any held keys
            time.sleep(1)


if __name__ == "__main__":
    main()
