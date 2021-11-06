from abc import abstractmethod
from typing import Dict, Optional


class LyricsSource:
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def prepare_request(self, title: str, artist: str) -> [Optional[str], Optional[object]]:
        raise NotImplementedError("Please Implement this method")

    @abstractmethod
    def parse_lyrics(self, html: str) -> Optional[str]:
        raise NotImplementedError("Please Implement this method")

    def get_name(self) -> str:
        return self.name
