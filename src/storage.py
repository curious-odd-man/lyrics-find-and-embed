import codecs
import os.path
from os import walk
from typing import List

from song_data import SongData


class Storage:
    def __init__(self, root_path):
        self.__root_path = root_path
        pass

    def get_sources(self, song_data: SongData) -> List[str]:
        """
        Return list of sources for which html is available
        """
        result = []
        for (_, _, filenames) in walk(self.__make_dir_path_album(song_data)):
            result.extend(filenames)
        return result

    def load(self, source: str, song_data: SongData, is_album=False) -> str:
        if is_album:
            dir_path = self.__make_dir_path_album(song_data)
        else:
            dir_path = self.__make_dir_path(song_data)
        target = os.path.join(dir_path, source)
        os.makedirs(dir_path, exist_ok=True)
        with codecs.open(target, 'r', 'UTF-8') as f:
            return str(f.read())

    def store(self, source: str, song_data: SongData, text: str, is_album=False):
        if not text:
            raise Exception('Text must not be none')
        if is_album:
            dir_path = self.__make_dir_path_album(song_data)
        else:
            dir_path = self.__make_dir_path(song_data)
        target = os.path.join(dir_path, source)
        os.makedirs(dir_path, exist_ok=True)
        with codecs.open(target, 'w', 'UTF-8') as f:
            f.write(text)
            f.flush()

    def __make_dir_path_album(self, song_data: SongData) -> str:
        return os.path.join(self.__root_path, song_data.artist, song_data.album)

    def __make_dir_path(self, song_data: SongData) -> str:
        return os.path.join(self.__root_path, song_data.artist, song_data.album, song_data.title)
