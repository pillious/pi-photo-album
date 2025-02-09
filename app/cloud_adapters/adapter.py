from abc import ABC, abstractmethod


class Adapter(ABC):
    @abstractmethod
    def get_album(self, album_path):
        pass

    @abstractmethod
    def insert(self, image_path: str, image_key: str) -> bool:
        pass
    
    # @abstractmethod
    # def insertBatch(self, images):
    #     pass

    @abstractmethod
    def remove(self, image_key: str) -> bool:
        pass

    # @abstractmethod
    # def removeBatch(self, images):
    #     pass