# Installation Guide for Pi Photo Album

This guide assumes you are setting up the Raspberry Pi from a seperate computer and will be using SSH to access the Raspberry Pi.

## How to Setup?

Open two terminals. One SSH'd into the Raspberry Pi, and the other on your local computer.

### Install Dependencies:
1. Install the required linux dependencies on the Pi:
    ```bash
    sudo apt update
    sudo apt install fbi inotify-tools libheif-examples exiftran
    ```
1. Install python `3.11.2` on the Pi

### Setup Framebuffer Image Viewer (fbi) for non root user:

1. Check if user is in the `tty` and `video` groups:
    ```bash
    groups pi
    ```
    The output should include `tty` and `video`.

    If not, add the user to the `tty` and `video` groups:
    ```bash
    sudo usermod -aG tty pi
    sudo usermod -aG video pi
    ```

1. Allow `fbi` to control TTY without root:
    ```bash
    sudo setcap cap_sys_tty_config+ep $(which fbi)
    ```

1. Reboot the Raspberry Pi:
    ```bash
    sudo reboot
    ```

### Enable Raspberry Pi Auto-login

1. Run `sudo raspi-config` to enable Auto-login

1. Choose option: `1 System Options`

1. Choose option: `S5 Boot / Auto Login`

1. Choose option: `B2 Console Autologin`

1. Select Finish, and reboot the Raspberry Pi (`sudo reboot`).

### Copy App to Raspberry Pi:
1. Create app directory on the Pi:
    ```bash
    mkdir -p /usr/local/bin/pi-photo-album
    ```

1. Give non-root ownership to dir:
    ```bash
    sudo chown -R $USER:$USER /usr/local/bin/pi-photo-album
    ```

1. Copy app to the Pi:
    ```bash
    scp -r app/ pi@<raspberry_pi_ip>:/usr/local/bin/pi-photo-album
    ```

1. Copy startup script to the Pi:
    ```bash
    scp startup.sh pi@<raspberry_pi_ip>:/usr/local/bin/pi-photo-album/
    ```

1. Make the startup script executable:
    ```bash
    chmod +x /usr/local/bin/pi-photo-album/startup.sh
    ```

1. Also make the `display_slideshow.sh` script executable:
    ```bash
    chmod +x /usr/local/bin/pi-photo-album/app/display_slideshow.sh
    ```

### Setup Python Virtual Environment:

1. Create a virtual environment:
    ```bash
    python3 -m venv /usr/local/bin/pi-photo-album/venv
    ```

1. Activate the virtual environment:
    ```bash
    source /usr/local/bin/pi-photo-album/venv/bin/activate
    ```

1. Install the required Python packages:
    ```bash
    pip install -r /usr/local/bin/pi-photo-album/app/requirements.txt
    ```

1. Exit the virtual environment:
    ```bash
    deactivate
    ```

### Configure Auto-Start on Boot:

1. Copy the app's systemd service file to the Pi:
    ```bash
    scp pi-photo-album.service pi@<raspberry_pi_ip>:~
    sudo mv pi-photo-album.service /etc/systemd/system/
    ```

1. Enable the service to start on boot:
    ```bash
    sudo systemctl enable pi-photo-album
    ```

### Setup Environment Variable File:

1. Create env file:
    ```bash
    mkdir -p ~/.config/pi-photo-album
    touch ~/.config/pi-photo-album/.env
    ```

1. Add the following environment variables to the `.env` file:

    > [!Tip]
    > Follow the [New User Onboarding Guide](admin/aws/onboard.md) to create the AWS related values.

    ```bash
    AWS_ACCESS_KEY_ID=
    AWS_SECRET_ACCESS_KEY=
    AWS_REGION=
    USERNAME=

    PUSH_QUEUE_URL=
    PUSH_QUEUE_ROLE=
    RECEIVE_EVENT_QUEUE_URL=

    #
    # Optional configuration:
    #
    API_PORT=<port_number [default: 5555]>
    # S3_BUCKET_NAME must match the one created in `admin/aws/s3.tf`
    S3_BUCKET_NAME=<your_s3_bucket_name [default: pi-photo-album-s3]>
    PHOTO_STORAGE_PATH=<path_to_photo_storage [default: $HOME/pi-photo-album]>
    # CONFIG_PATH should also be set if PHOTO_STORAGE_PATH is set.
    CONFIG_PATH=<path_to_config_folder [default: $HOME/.config/pi-photo-album]> 
    ```

### Start the Application:
1. Start the service:
    ```bash
    sudo systemctl start pi-photo-album
    ```

    OR 
    
    Reboot the Raspberry Pi to start the service automatically:
    ```bash
    sudo reboot
    ```