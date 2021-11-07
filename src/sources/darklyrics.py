import re
from typing import Optional

from build_requests import get_request_headers
from song_data import SongData
from sources.lyrics_source import LyricsSource

regex_non_alphanumeric = re.compile(r'[^a-z0-9]+')
request_headers = get_request_headers()


class DarkLyrics(LyricsSource):
    def __init__(self):
        super().__init__('Dark_Lyrics')

    def is_album(self) -> bool:
        return True

    def prepare_request(self, song_data: SongData) -> [Optional[str], Optional[object]]:
        artist = regex_non_alphanumeric.sub('', song_data.artist)
        album = regex_non_alphanumeric.sub('', song_data.album)
        return f'http://www.darklyrics.com/lyrics/{artist}/{album}.html', request_headers

    def parse_lyrics(self, html: str) -> Optional[str]:
        pass
