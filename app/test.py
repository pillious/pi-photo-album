
from app.cloud_adapters.s3_adapter import S3Adapter
import os
from dotenv import load_dotenv

# import slideshow
# import globals
# import utils

load_dotenv()

s3 = S3Adapter("pi-photo-album-s3")

# # print(s3.list_album("albums/Shared/"))
# # print(s3.list_album("albums/alee1246/"))

# l1 = ['albums/Shared/0eb9fc9e-757b-4c6e-95d5-d7cda4b8e802.webcam-settings.png', 'albums/Shared/123.png', 'albums/Shared/19dfbc98-2a82-43da-802b-8ad5a5b5f32a.webcam-settings.png', 'albums/Shared/2e290df-75e3-49ce-ba0a-4273337e4274.123.png', 'albums/Shared/2eeda593-fb98-4a6b-9a52-41ca44faceb6.webcam-settings.png', 'albums/Shared/4a0983d0-ce2a-4009-a74c-641545d8d14b.webcam-settings.png', 'albums/Shared/615fdba2-72e0-4ffe-8793-83495bc2f159.testimage_-_Copy.png', 'albums/Shared/be9b074b-814e-4aaa-855b-87dce0dd9d1f.webcam-settings.png', 'albums/Shared/c585ecab-59db-450f-abb8-3d76f97bf172.webcam-settings.png', 'albums/Shared/dae13468-65fd-442a-83b9-35ab1194b4c4.webcam-settings.png', 'albums/Shared/ef4b2f52-b960-48d6-8a86-fcb4ac529c7f.testimage_-_Copy.png', 'albums/Shared/test2/11a1d5b2-fa89-4c9a-9ae9-50bf1299ca0e.webcam-settings.png', 'albums/Shared/test2/29c2f73a-0a5f-4d04-a67c-a00440e3b951.randomphoto.png', 'albums/Shared/test2/9ff70ffd-445f-4642-aa7f-3d39e80b0dd5.webcam-settings.png', 'albums/Shared/testing/asdf/09faab5c-9fe5-493a-ba18-e11d58453cd1.testimage_-_Copy.png', 'albums/Shared/testing/asdf/604c9748-3a89-49bd-9be5-3d00d8f3b36c.webcam-settings.png', 'albums/Shared/user1test/288fb391-ea2b-4f3b-90bd-fb400a326309.webcam-settings.png', 'albums/Shared/user1test/3300954b-469e-4c86-84eb-642ce9944f22.randomphoto.png', 'albums/Shared/user1test/3ff97bd5-94e0-4ce6-8cc7-d03bdeac677c.randomphoto.png', 'albums/Shared/user1test/514e05d5-59e4-4163-879c-9895d90089f1.randomphoto.png', 'albums/Shared/user1test/8c5cabbb-3408-4683-8468-99fa92b9a157.randomphoto.png', 'albums/Shared/user1test/b9f0f763-0b59-48d2-bfca-32974415ec76.webcam-settings.png', 'albums/Shared/user1test/bda535ba-3064-42f8-b21d-9e9f6ed17554.testimage_-_Copy.png', 'albums/Shared/user1test/f82db8b0-f7ed-49c6-b0c9-9315a2c1355f.webcam-settings.png', 'albums/Shared/user1test/subfolder1/09dad2ed-adb1-4421-9695-769a2be8a1e9.randomphoto.png', 'albums/Shared/user1test/subfolder1/6eb679c7-9fed-4592-8230-711f5c6e65e5.webcam-settings.png', 'albums/Shared/user1test/subfolder1/6f18a05a-bb79-4856-93f1-2b2ffe035a6c.randomphoto.png', 'albums/Shared/user1test/subfolder1/91040ce0-7cab-4979-8c43-2f81ebb7852e.testimage_-_Copy.png', 'albums/Shared/user1test/subfolder1/ca7e30be-255b-4cb1-9084-e6d0b3c119a5.webcam-settings.png', 'albums/Shared/user1test/test2/4b48e91e-9aba-4cd4-9bbc-98e6cafdf171.webcam-settings.png']
# l2 = ['albums/alee1246/nature/2a2d4c48-d6f5-4b46-869e-648dcf328c3d.testimage_-_Copy.png', 'albums/alee1246/nature/817ec81c-2b93-4fa6-aabf-2a31fa09226a.webcam-settings.png', 'albums/alee1246/nature/955cc36d-910b-49c2-b182-8aa41f335576.webcam-settings.png', 'albums/alee1246/user1test/subfolder1/04747157-9314-4c8d-8f39-41e172e97629.randomphoto.png', 'albums/alee1246/user1test/subfolder1/6808bb8a-6336-4912-9cd6-62db8f6d029a.webcam-settings.png']

# l1 = set(l1)
# l2 = set(l2)

# l3 = l1.union(l2)

# # print(l3)

# a1 = utils.list_files_in_dir(globals.BASE_DIR, ["albums/Shared", "albums/alee1246"])
# a1 = set(a1)

# print(l3.difference(a1))


# print(a1.difference(l3))

# # print(utils.list_files_in_dir(globals.BASE_DIR, ["albums/Shared", "albums/alee1246"]))



# # s3.list_album("albums/alee1246/")

# # image_base_path = "albums"
# # image_key = "Shared/nature/pexels-philippedonn-1133957.jpg"
# # image_path = os.path.abspath(f"./{image_base_path}/{image_key}")

# # # print(image_base_path)
# # # print(image_key)
# # # print(image_path)


# # # print(s3.insert(image_path, image_key))

# # # s3.remove(image_key)

# # # obj = s3.get(image_key)
# # # with open("output.jpg", "wb") as f:
# # #     f.write(obj)

# # # slideshow.start_slideshow("albums/nature", 250, 30, True)

# # s3.insert_queue("TESING")

# # for root, dirs, files in os.walk(f"{globals.BASE_DIR}/albums"):
# #     root = root.replace(f"{globals.BASE_DIR}/", "")
# #     for name in files:
# #         print(os.path.join(root, name))

# import app.utils.offline as offline
# import app.globals as globals

# offline.save_offline_events(globals.OFFLINE_EVENTS_FILE, [
#     "2025-05-13T12:00:00Z,PUT,albums/test/image1.jpg",
#     "2025-05-13T12:05:00Z,MOVE,albums/test/image2.jpg,albums/test/image3.jpg",
#     "2025-05-13T12:10:00Z,DELETE,albums/test/image4.jpg"
# ])

# upload some files to s3 using the s3 adapter

s3.insert("/home/user/pi-photo-album/albums/Shared/123.png", "albums/Shared/image1.jpg")
s3.insert("/home/user/pi-photo-album/albums/Shared/123.png", "albums/Shared/image2.jpg")
s3.insert("/home/user/pi-photo-album/albums/Shared/123.png", "albums/Shared/image3.jpg")
