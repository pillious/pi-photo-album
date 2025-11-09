# Installation Guide for Pi Photo Album

This guide assumes you are setting up the Raspberry Pi from a separate computer and will be using SSH to access the Raspberry Pi.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Steps](#installation-steps)
  - [1. Download the app](#1-download-the-app)
  - [2. Run the installation script](#2-run-the-installation-script)
  - [3. Enable Raspberry Pi Auto-login](#3-enable-raspberry-pi-auto-login)
  - [4. Configure Auto-Start on Boot](#4-configure-auto-start-on-boot)
  - [5. Setup Environment Variable File](#5-setup-environment-variable-file)
  - [6. Start the Application](#6-start-the-application)

## Prerequisites

- Raspberry Pi with SSH access
- Internet connection on the Raspberry Pi
- Python 3.13 or higher installed on the Raspberry Pi

## Installation Steps

### 1. Download the app
   https://github.com/pillious/pi-photo-album/releases/
   ```bash
   VERSION=<version> && \
   wget https://github.com/pillious/pi-photo-album/releases/download/v$VERSION/pi_photo_album-$VERSION.tar.gz && \
   sudo rm -rf /usr/local/bin/pi-photo-album && \
   sudo tar -xzf pi_photo_album-$VERSION.tar.gz -C /usr/local/bin && \
   sudo mv /usr/local/bin/pi_photo_album-$VERSION /usr/local/bin/pi-photo-album
   ```
### 2. Run the installation script
   ```bash
   /usr/local/bin/pi-photo-album/install.sh
   ```

   ```
   sudo reboot
   ```
   - Rebooting is only required after the first time running the installation script.

### 3. Enable Raspberry Pi Auto-login

1. Run `sudo raspi-config` to enable Auto-login

2. Choose option: `1 System Options`

3. Choose option: `S5 Boot / Auto Login`

4. Choose option: `B2 Console Autologin`

5. Select Finish, and reboot the Raspberry Pi (`sudo reboot`).

### 4. Configure Auto-Start on Boot

1. [Optional] Enable the service to start on boot:
   ```bash
   sudo systemctl enable pi-photo-album
   ```

### 5. Setup Environment Variable File

1. Create the configuration directory:
   ```bash
   touch ~/.config/pi-photo-album/.env
   ```

3. Add the following environment variables:

   > [!Tip]
   > Follow the [New User Onboarding Guide](admin/aws/onboard.md) to create the AWS related values.

   ```bash
   AWS_ACCESS_KEY_ID=your_access_key_here
   AWS_SECRET_ACCESS_KEY=your_secret_key_here
   AWS_REGION=your_region_here
   USERNAME=your_username_here

   PUSH_QUEUE_URL=your_push_queue_url
   PUSH_QUEUE_ROLE=your_push_queue_role
   RECEIVE_EVENT_QUEUE_URL=your_receive_queue_url

   #
   # Optional configuration:
   #
   API_PORT=5555
   S3_BUCKET_NAME=pi-photo-album-s3
   PHOTO_STORAGE_PATH=$HOME/pi-photo-album
   CONFIG_PATH=$HOME/.config/pi-photo-album
   ```

### 6. Start the Application

1. Start the service:
   ```bash
   sudo systemctl start pi-photo-album
   ```

   OR

   Reboot the Raspberry Pi to start the service automatically:
   ```bash
   sudo reboot
   ```

2. Stopping the service:
   ```bash
   sudo systemctl

3. Troubleshooting:
   ```bash
   sudo systemctl status pi-photo-album
   ```
   ```bash
   journalctl -u pi-photo-album.service
   ```