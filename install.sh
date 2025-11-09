#!/bin/bash
set -euxo pipefail

# Install dependencies
sudo apt update
sudo apt install fbi inotify-tools libheif-examples exiftran

# Add user to tty and video groups
groups $(whoami) | grep -q "tty" || sudo usermod -aG tty $(whoami)
groups $(whoami) | grep -q "video" || sudo usermod -aG video $(whoami)

# Allow fbi to control TTY without root
getcap $(which fbi) | grep -q 'cap_sys_tty_config=ep' || sudo setcap cap_sys_tty_config+ep "$(which fbi)"

# Create app directory
mkdir -p /usr/local/bin/pi-photo-album
sudo chown -R $USER:$USER /usr/local/bin/pi-photo-album

[ -x /usr/local/bin/pi-photo-album/startup.sh ] || chmod +x /usr/local/bin/pi-photo-album/startup.sh
[ -x /usr/local/bin/pi-photo-album/app/display_slideshow.sh ] || chmod +x /usr/local/bin/pi-photo-album/app/display_slideshow.sh

# Create virtual environment
mkdir -p $HOME/.config/pi-photo-album
[ -d $HOME/.config/pi-photo-album/venv ] || python -m venv $HOME/.config/pi-photo-album/venv
source $HOME/.config/pi-photo-album/venv/bin/activate

# Install Python packages
pip install --upgrade pip
pip install /usr/local/bin/pi-photo-album

deactivate

# Setup systemd service file
PYTHON_PATH=$HOME/.config/pi-photo-album/venv/bin/python
sudo sed -i "s|{python_path}|$PYTHON_PATH|g" /usr/local/bin/pi-photo-album/pi-photo-album.service.tmpl
sudo cp /usr/local/bin/pi-photo-album/pi-photo-album.service.tmpl /etc/systemd/system/pi-photo-album.service
sudo systemctl daemon-reload
