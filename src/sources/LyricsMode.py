import logging
import re
from typing import Optional
from string import ascii_lowercase as LOWERCASE_CHARS

from bs4 import BeautifulSoup

from build_requests import get_request_headers
from lyrico.lyrico_sources.lyrics_helper import remove_accents, test_lyrics
from song_data import SongData
from sources.lyrics_source import LyricsSource

request_headers = get_request_headers()
regex_non_alphanumeric = re.compile(r'[^a-z0-9\s\-]+')
regex_underscores = re.compile(r'[\s|\-]+')

log = logging.getLogger("LyricsMode")


class LyricsMode(LyricsSource):
    def __init__(self):
        super().__init__('Lyrics_Mode')

    def is_album(self) -> bool:
        return False

    def prepare_request(self, song_data: SongData) -> [Optional[str], Optional[object]]:
        artist = regex_non_alphanumeric.sub('', remove_accents(song_data.artist).lower())
        title = regex_non_alphanumeric.sub('', song_data.title.lower())
        artist = regex_underscores.sub('_', artist)
        title = regex_underscores.sub('_', title)

        # If the first char of artist is not a alphabet, use '0-9'
        if len(artist) < 1:
            artist = ' '
        first_artist_char = artist[0]
        if first_artist_char not in LOWERCASE_CHARS:
            first_artist_char = '0-9'

        return 'http://www.lyricsmode.com/lyrics/%s/%s/%s.html' % (first_artist_char, artist, title), request_headers

    def parse_lyrics(self, html: str, song_title) -> Optional[str]:
        soup = BeautifulSoup(html, 'html.parser')

        # For lyricsmode, the lyrics are present in a div with id 'lyrics_text'
        lyrics_text = soup.find(id='lyrics_text')
        lyrics = lyrics_text.get_text().strip() if lyrics_text else None
        # Final check

        if test_lyrics(lyrics):
            return lyrics
        else:
            log.info('Failed to verify lyrics')
            return None
