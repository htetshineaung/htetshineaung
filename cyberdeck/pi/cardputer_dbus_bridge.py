#!/usr/bin/env python3
"""
Forward desktop notifications (notify-send, browsers, chat apps...) to the Cardputer.

Runs in YOUR desktop session (systemd --user unit), watches the session D-Bus for
org.freedesktop.Notifications.Notify calls with `dbus-monitor`, and relays
app / summary / body to cardputer-statusd over UDP. Your normal notification
popups keep working - this only listens.
"""
import json
import re
import socket
import subprocess

ADDR = ("127.0.0.1", 47800)
MATCH = "type='method_call',interface='org.freedesktop.Notifications',member='Notify'"
STR_RE = re.compile(r'^\s*string "(.*)', re.S)


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    proc = subprocess.Popen(["dbus-monitor", "--session", MATCH],
                            stdout=subprocess.PIPE, text=True, bufsize=1)
    strings, cur, collecting = [], None, False
    for line in proc.stdout:
        if "member=Notify" in line:
            strings, cur, collecting = [], None, True
            continue
        if not collecting:
            continue
        if cur is not None:                      # continuation of a multi-line string
            cur += "\n" + line.rstrip("\n")
            if cur.endswith('"'):
                strings.append(cur[:-1]); cur = None
        else:
            m = STR_RE.match(line.rstrip("\n"))
            if m:
                s = m.group(1)
                if s.endswith('"'):
                    strings.append(s[:-1])
                else:
                    cur = s
        # Notify(app_name, replaces_id, app_icon, summary, body, ...)
        if len(strings) >= 4:
            app, _icon, summary, body = strings[:4]
            sock.sendto(json.dumps({"app": app or "desktop", "summary": summary,
                                    "body": body}).encode(), ADDR)
            collecting = False


if __name__ == "__main__":
    main()
