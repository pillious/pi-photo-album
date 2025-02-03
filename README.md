### Using Python 3.11.2
`pyenv install 3.11.2`
`pyenv shell 3.11.2`

### Check if display is connected to one of the HDMI ports
`kmsprint`

### Display image over SSH
`sudo fbi -d /dev/fb0 -T 1 -a img.png`

` sudo fbi -d /dev/fb0 -T 1 -t 5 -blend 250 -noverbose -readahead -a nature/*`
`-u` to randomize images

### Terminate fbi
`ps aux | grep fbi`
`sig killall -15 fbi`
`sudo chvt 1` 

### Convert heic to jpg/png
`sudo apt install libheif-examples`
`heif-convert image.heic image.jpg`

### Raspberry pi auto login
To enable Auto-login with raspi-config:

Run: sudo raspi-config
Choose option: 1 System Options
Choose option: S5 Boot / Auto Login
Choose option: B2 Console Autologin
Select Finish, and reboot the Raspberry Pi.

### Check CPU temp
`vcgencmd measure_temp`
`watch -c -b -d  -n 1 -- 'vcgencmd measure_temp'`
