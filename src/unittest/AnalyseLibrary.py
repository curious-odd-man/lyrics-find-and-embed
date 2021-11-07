import logging
import unittest
from typing import Dict

from main import shall_be_ignored
from song_data import SongData
from song_helper import get_song_list, get_song_data

log = logging.getLogger(__file__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s')

library_path = r'D:\My Music\Music'


def truncate(num, n):
    integer = int(num * (10 ** n)) / (10 ** n)
    return float(integer)


class Song:
    def __init__(self, song_data: SongData):
        self.title = song_data.title
        self.has_lyrics = song_data.lyrics is not None and len(song_data.lyrics) > 0


class Album:
    def __init__(self, name: str):
        self.album = name
        self.songs = []
        self.songs_with_lyrics = None

    def calc_songs_with_lyrics(self) -> None:
        self.songs_with_lyrics = 0
        for song in self.songs:
            if song.has_lyrics:
                self.songs_with_lyrics += 1

    def song_count(self) -> int:
        return len(self.songs)

    def percent_with_lyrics(self) -> float:
        return self.songs_with_lyrics / self.song_count()

    def all_lyrics(self) -> bool:
        return self.song_count() == self.songs_with_lyrics


class Artist:
    def __init__(self):
        self.albums: Dict[str, Album] = dict()

    def add_album(self, name: str):
        if name not in self.albums.keys():
            self.albums[name] = Album(name)

    def add_song_to_album(self, album: str, song: Song):
        self.albums[album].songs.append(song)

    def count_albums(self):
        return len(self.albums)

    def calc_songs_with_lyrics(self):
        for album in self.albums.values():
            album.calc_songs_with_lyrics()

    def song_count(self) -> int:
        count = 0
        for album in self.albums.values():
            count += album.song_count()
        return count

    def all_lyrics(self) -> bool:
        for album in self.albums.values():
            if not album.all_lyrics():
                return False
        return True


artist_to_albums: Dict[str, Artist] = dict()


class AnalyseLybrary(unittest.TestCase):

    def test_overall_stats(self):
        song_list = get_song_list(library_path)
        for song_file in song_list:
            try:
                print('.', end='', flush=True)
                song_data = get_song_data(song_file)
                if shall_be_ignored(song_data):
                    log.info(f'[IGNORE] Song is added to manual ignored list: {song_data}')
                    continue
                song = Song(song_data)

                artist_info = artist_to_albums.setdefault(song_data.artist, Artist())
                artist_info.add_album(song_data.album)
                artist_info.add_song_to_album(song_data.album, song)
            finally:
                log.error(song_file, exc_info=True)

        self.calc_and_print_stats()

    def calc_and_print_stats(self):
        count_artists = len(artist_to_albums.keys())
        print(f'Total artists {count_artists}')
        count_albums = 0
        count_songs = 0
        for artists in artist_to_albums.values():
            for albums in artists.albums.values():
                count_songs += albums.song_count()
                count_albums += 1

        print(f'Total albums {count_albums}')
        print(f'Total songs {count_songs}')
        print('Missing lyrics stats')
        for artist_name, artist in artist_to_albums.items():
            artist.calc_songs_with_lyrics()
            if artist.all_lyrics():
                log.debug(f'\t{artist_name}: [FULL]')
                continue
            print(f'\t{artist_name}:')
            for album in artist.albums.values():
                if album.all_lyrics():
                    log.debug(f'\t\t{album.album}: [FULL]')
                    continue
                print(f'\t\t{album.album}: {truncate(album.percent_with_lyrics() * 100, 0)} %')
                for song in album.songs:
                    if not song.has_lyrics:
                        print(f'\t\t\t{song.title}: [MISSING]')


if __name__ == '__main__':
    unittest.main()

"""
Total artists: xxx
Total albums: xxx
Total songs: xxx
Missing lyrics stats:
   <<<artist>>> (yyy%)
        <<<album>>> (yyy%)
            <<<song1>>>
            <<<song2>>>
"""
