from abc import abstractmethod
from typing import Optional

from song_data import SongData


class LyricsSource:
    def __init__(self, name: str):
        self.name = name

    def is_album(self) -> bool:
        raise NotImplementedError("Please Implement this method")

    @abstractmethod
    def prepare_request(self, song_data: SongData) -> [Optional[str], Optional[object]]:
        raise NotImplementedError("Please Implement this method")

    @abstractmethod
    def parse_lyrics(self, html: str) -> Optional[str]:
        raise NotImplementedError("Please Implement this method")

    def get_name(self) -> str:
        return self.name
