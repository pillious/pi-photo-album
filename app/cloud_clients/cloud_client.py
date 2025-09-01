from abc import ABC, abstractmethod, ABCMeta
from typing import List, Tuple

class Singleton(ABCMeta):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class CloudClient(ABC, metaclass=Singleton):
    @abstractmethod
    def list_album(self, album_path: str) -> List[str]:
        """
        List all items in the specified album path including sub-albums.

        Args:
            album_path (str): The relative path of the album.
        Returns:
            List[str]: A list of image paths.
        """
        pass

    @abstractmethod
    def get(self, image_key: str) -> bytes:
        """
        Retrieve an image from the storage by its key.

        Args:
            image_key (str): The relative path of the image to retrieve.
        Returns:
            bytes: The image data as bytes.
        Raises:
            CloudClientException: If image retrieval fails.
        """
        pass

    @abstractmethod
    def insert(self, image_path: str, image_key: str):
        """
        Upload an image.

        Args:
            image_path (str): The local path of the image to upload.
            image_key (str): The key/relative path to assign to the uploaded image.
        Raises:
            CloudClientException: If image upload fails.
        """
        pass

    @abstractmethod
    def move(self, src_key: str, dest_key: str):
        """
        Update the location of an image.

        Args:
            src_key (str): The source relative path of the image.
            dest_key (str): The destination relative path for the image.
        Raises:
            CloudClientException: If image moving fails.
        """
        pass

    @abstractmethod
    def delete(self, image_key: str):
        """
        Delete an image from the storage by its key.

        Args:
            image_key (str): The key/relative path of the image to delete.
        Raises:
            CloudClientException: If image deletion fails.
        """
        pass

    @abstractmethod
    def get_bulk(self, image_paths: List[str], image_keys: List[str]) -> Tuple[List[str], List[str]]:
        """
        Retrieve multiple images in bulk.

        Args:
            image_paths (List[str]): The local paths to save the retrieved images.
            image_keys (List[str]): The keys of the images to retrieve.
        Returns:
            Tuple[List[str], List[str]]: A tuple containing lists of successfully retrieved keys and failed keys.
        """
        pass

    @abstractmethod
    def insert_bulk(self, image_paths: List[str], image_keys: List[str]) -> Tuple[List[str], List[str]]:
        """
        Insert multiple images in bulk.

        Args:
            image_paths (List[str]): The local paths of the images to upload.
            image_keys (List[str]): The keys to assign to the uploaded images.
        Returns:
            Tuple[List[str], List[str]]: A tuple containing lists of successfully inserted keys and failed keys.
        """
        pass

    @abstractmethod
    def move_bulk(self, image_key_pairs: List[Tuple[str, str]]) -> Tuple[List[str], List[str]]:
        """
        Move multiple images in bulk.

        Args:
            image_key_pairs (List[Tuple[str, str]]): A list of tuples containing source and destination keys.
        Returns:
            Tuple[List[str], List[str]]: A tuple containing lists of successfully moved key pairs and failed key pairs.
        """
        pass

    @abstractmethod
    def delete_bulk(self, image_keys: List[str]) -> Tuple[List[str], List[str]]:
        """
        Delete multiple images in bulk.

        Args:
            image_keys (List[str]): The keys of the images to delete.
        Returns:
            Tuple[List[str], List[str]]: A tuple containing lists of successfully deleted keys and failed keys.
        """
        pass

    @abstractmethod
    def insert_queue(self, message: str, message_group_id: str = "default"):
        """
        Insert a message into the event queue.

        Args:
            message (str): The message to insert into the queue.
            message_group_id (str, optional): The group ID for the message.
        Raises:
            CloudClientException: If message insertion fails.
        """
        pass

_CLIENT = None

def init_cloud_client(client: CloudClient):
    global _CLIENT
    if _CLIENT is not None:
        return  # Already initialized
    _CLIENT = client

def cloud_client() -> CloudClient:
    if _CLIENT is None:
        raise RuntimeError("Cloud client not initialized. Call init_cloud_client() first.")
    return _CLIENT