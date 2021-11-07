import logging
import re
import sys
from typing import Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from build_requests import get_request_headers
from song_data import SongData
from sources.helper import test_lyrics
from sources.lyrics_source import LyricsSource

request_headers = get_request_headers()

regex_non_alphanum = re.compile(r'[^\w\s\-]*', re.UNICODE)
regex_spaces = re.compile(r'[\s]+', re.UNICODE)

log = logging.getLogger("LyricsSource")


class MusixMatch(LyricsSource):

    def __init__(self):
        super().__init__('Musix Match')

    def is_album(self) -> bool:
        return False

    def prepare_request(self, song_data: SongData) -> [Optional[str], Optional[object]]:
        refined_artist = self.__refine_text(song_data.artist)
        refined_title = self.__refine_text(song_data.title)
        url = 'https://www.musixmatch.com/lyrics/%s/%s' % (quote(refined_artist), quote(refined_title))
        return url, request_headers

    @staticmethod
    def __refine_text(raw_string: str) -> str:
        # Replace upper(apostrophe) commas with dashes '-'
        res = raw_string.replace("'", '-')
        # This regex mathches anything other than Alphanumeric, spaces and dashes
        # and removes them.
        # Make regex unicode aware 're.UNICODE' for Python27. It is redundant for Python3.
        res = regex_non_alphanum.sub('', res)
        # Replace spaces with dashes to imporve URL logging.
        res = regex_spaces.sub('-', res)
        if sys.version_info[0] < 3:
            res = res.encode('utf-8')
        return res

    def parse_lyrics(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, 'html.parser')
        lyrics = ''
        all_p_elements = soup.findAll('p', {"class": "mxm-lyrics__content"})
        for p in all_p_elements:
            lyrics += p.get_text().strip()
        if test_lyrics(lyrics):
            return lyrics
        else:
            return None
