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
`killall -15 fbi`
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



#########

Warning: secrets are in the terraform.tfstate file.

[] Save to cloud option
[] What if multiple times logged into same account?
[] Display memory available. (allow set mem limit?)

[] should only be able to access images in user/ and shared/ folders

[] If add file that already exists, add a (1), (2), etc.
[] Test what happens if fbi is running and another image is added to the folder.
[] cp/mv files between folders / renaming files and folders
[] auto converter for heic/heif files

Thoughts on file syncing with cloud:
- local files need some marker whether they are synced or not. 
    - this should probably be json file. This can be sent to the frontend and displayed.
- Only allow usage of shared/ if 'save to cloud' is enabled.
- For shared album, add option to remove from local to save disk space.
- subscribe to messages when something in user/ or shared/ changes.
- For shared albums change messages:
    - If deleted locally, ignore message
    - If deleted locally, but the message deletes the album, then remove album from local state.
    - If new album, add to local state but don't download the images

JSON state:
```
{
    "state": {
        "cloudSync": true,
        "files": { # should mirror the file system structyre
            "alee1246": {
                "albums": {
                    "my_album1": {
                        "images": {
                            "image1.jpg": {
                                "synced": true
                            },
                            "image2.jpg": {
                                "synced": false
                            }
                        }
                    },
                    "my_album2": {
                        "images": {
                            "image3.jpg": {
                                "synced": true
                            }
                        }
                    }
                }
            },
            "shared": {
                "shared_album1": {
                    "synced": false,
                    "images": {
                        "image4.jpg": {
                            "synced": true
                        }
                    }
                }
            }
        }
    }
}
```

albums/
    trash/
    tmp/ # like a staging area for images when added/deleted (might not need?)
        add/
        delete/
    alee1246/
        my_album1/
            image1.jpg
        my_album2/
            image2.jpg
            image3.jpg
    shared/
        shared_album1/
            image4.jpg
            image5.jpg
        shared_album2/
            image6.jpg
            image7.jpg


### Message body from sqs
```
Message Body -> {
  "Type" : "",
  "MessageId" : "",
  "SequenceNumber" : "",
  "TopicArn" : "",
  "Message" : "{\"event\": \"PUT\", \"path\": \"\", \"timestamp\": 1745037960, \"id\": \"\"}",
  "Timestamp" : "",
  "UnsubscribeURL" : "",
  "MessageAttributes" : {
    "messageGroupId" : {"Type":"String","Value":""},
    "sender" : {"Type":"String","Value":""}
  }
}
```

TODO
[] server max payload is 128mb. The client shouldn't try to send more than that.
[] resync after going offline.
[-] server sent events to update client with events.

[-] fix heif upload
[-] fix s3 permissions to user prefix.

[] Uploading file spinner