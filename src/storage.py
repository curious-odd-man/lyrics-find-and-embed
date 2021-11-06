import codecs
import os.path
from os import walk
from typing import List


class Storage:
    def __init__(self, root_path):
        self.__root_path = root_path
        pass

    def get_sources(self, artist: str, title: str) -> List[str]:
        """
        Return list of sources for which html is available
        """
        for (_, _, filenames) in walk(self.__make_dir_path(artist, title)):
            return filenames
        return []

    def load(self, source: str, artist: str, title: str) -> str:
        dir_path = self.__make_dir_path(artist, title)
        target = os.path.join(dir_path, source)
        os.makedirs(dir_path, exist_ok=True)
        with codecs.open(target, 'r', 'UTF-8') as f:
            return str(f.read())

    def store(self, source: str, artist: str, title: str, text: str):
        if not text:
            raise Exception('Text must not be none')
        dir_path = self.__make_dir_path(artist, title)
        target = os.path.join(dir_path, source)
        os.makedirs(dir_path, exist_ok=True)
        with codecs.open(target, 'w', 'UTF-8') as f:
            f.write(text)
            f.flush()

    def __make_dir_path(self, artist: str, title: str) -> str:
        return os.path.join(self.__root_path, artist, title)
