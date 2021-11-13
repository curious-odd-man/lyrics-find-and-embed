import codecs
import logging
import unittest

from sources.darklyrics import DarkLyrics

log = logging.getLogger(__file__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s')

store_song_path = r'D:\Programming\git\lyrico\test_data\storage\Dark_Lyrics'
store_song_path2 = r'D:\Programming\git\lyrico\test_data\storage\Dark_Lyrics_nightfall'


class StorageTests(unittest.TestCase):

    def test_get_sources(self):
        with codecs.open(store_song_path, 'r', encoding='UTF-8') as f:
            lyrics = DarkLyrics().parse_lyrics(f.read(), 'Häxprocess')
            print(lyrics)

    def test_get_nighftfall_sources(self):
        with codecs.open(store_song_path2, 'r', encoding='UTF-8') as f:
            lyrics = DarkLyrics().parse_lyrics(f.read(), 'Codex Gigas')
            print(lyrics)


if __name__ == '__main__':
    unittest.main()
