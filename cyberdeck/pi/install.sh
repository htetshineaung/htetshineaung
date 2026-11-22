#!/usr/bin/env bash
# Install the Cardputer deck services on Raspberry Pi OS (Bookworm/Trixie).
#   sudo ./install.sh          # USB mode (recommended)
#   sudo ./install.sh --uart   # wired UART mode (Grove <-> Pi 5 UART connector)
set -euo pipefail
cd "$(dirname "$0")"
MODE="${1:-}"

apt-get install -y python3-serial dbus-bin
[ "$MODE" = "--uart" ] && apt-get install -y python3-evdev

install -d /usr/local/lib/cardputer
install -m 755 cardputer_statusd.py cardputer_dbus_bridge.py /usr/local/lib/cardputer/
install -m 755 cardputer-notify /usr/local/bin/cardputer-notify
install -m 644 99-cardputer.rules /etc/udev/rules.d/
udevadm control --reload-rules && udevadm trigger

install -m 644 cardputer-statusd.service /etc/systemd/system/
if [ "$MODE" = "--uart" ]; then
  sed -i 's#cardputer_statusd.py$#cardputer_statusd.py --uart#' /etc/systemd/system/cardputer-statusd.service
  # free the Pi 5 debug UART (ttyAMA10) from the serial console
  sed -i 's/console=serial0,[0-9]* //' /boot/firmware/cmdline.txt
  echo ">> Removed serial console from cmdline.txt - reboot required."
fi
install -m 644 cardputer-dbus-bridge.service /etc/systemd/user/

systemctl daemon-reload
systemctl enable --now cardputer-statusd.service
systemctl --global enable cardputer-dbus-bridge.service
echo ">> Done. Test with:  cardputer-notify 'Hello' 'Deck is alive'"
echo ">> Desktop notification relay starts at your next graphical login."
