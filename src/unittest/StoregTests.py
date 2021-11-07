import logging
import os.path
import shutil
import unittest

from song_data import SongData
from storage import Storage

log = logging.getLogger(__file__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s')

store_song_path = r'D:\Programming\git\lyrico\test_data\storage\store_song'
store_album_path = r'D:\Programming\git\lyrico\test_data\storage\store_album'
existing_sources_path = r'D:\Programming\git\lyrico\test_data\storage\existing_sources'


class StorageTests(unittest.TestCase):

    def tearDown(self) -> None:
        shutil.rmtree(store_song_path, ignore_errors=True)
        shutil.rmtree(store_album_path, ignore_errors=True)
        super().tearDown()

    def test_get_sources(self):
        storage = Storage(existing_sources_path)
        sources = storage.get_sources(SongData(None, 'artist', 'title', 'album', None, None))
        log.info(sources)
        self.assertIn('source1', sources)
        self.assertIn('source2', sources)
        self.assertIn('source3', sources)

    def test_store_song(self):
        os.makedirs(store_song_path, exist_ok=True)
        storage = Storage(store_song_path)
        storage.store('source_x', SongData(None, 'artist', 'title', 'album', None, None), 'dummy_text', False)
        with open(os.path.join(store_song_path, 'artist', 'album', 'title', 'source_x')) as f:
            self.assertEqual('dummy_text', f.read())

    def test_store_album(self):
        os.makedirs(store_album_path, exist_ok=True)
        storage = Storage(store_album_path)
        storage.store('source_x', SongData(None, 'artist', 'title', 'album', None, None), 'dummy_text', True)
        with open(os.path.join(store_album_path, 'artist', 'album', 'source_x')) as f:
            self.assertEqual('dummy_text', f.read())

    def test_load(self):
        storage = Storage(existing_sources_path)
        song3 = storage.load('source3', SongData(None, 'artist', 'title', 'album', None, None), is_album=True)
        song2 = storage.load('source2', SongData(None, 'artist', 'title', 'album', None, None), is_album=False)
        self.assertEqual('source_3_text', song3)
        self.assertEqual('source_2_text', song2)


if __name__ == '__main__':
    unittest.main()