from abc import ABC, abstractmethod
from typing import List, Tuple


class Adapter(ABC):
    @abstractmethod
    def get_album(self, album_path):
        pass

    @abstractmethod
    def insert(self, image_path: str, image_key: str):
        pass
    
    # Return: Tuple[success, failure]
    @abstractmethod
    def insert_bulk(self, image_paths, image_keys) -> Tuple[List[str], List[str]]:
        pass

    @abstractmethod
    def delete(self, image_key: str):
        pass

    # @abstractmethod
    # def removeBatch(self, images):
    #     pass
