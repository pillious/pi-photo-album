
from cloud_adapters.s3_adapter import S3Adapter
import os
from dotenv import load_dotenv

import slideshow

load_dotenv()

s3 = S3Adapter("pi-photo-album-s3")

image_base_path = "albums"
image_key = "Shared/nature/pexels-philippedonn-1133957.jpg"
image_path = os.path.abspath(f"./{image_base_path}/{image_key}")

# print(image_base_path)
# print(image_key)
# print(image_path)


# print(s3.insert(image_path, image_key))

# s3.remove(image_key)

# obj = s3.get(image_key)
# with open("output.jpg", "wb") as f:
#     f.write(obj)

# slideshow.start_slideshow("albums/nature", 250, 30, True)

s3.insertQueue("TESING")