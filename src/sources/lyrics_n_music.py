import json
import json
import logging
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

from build_requests import get_request_headers, get_lnm_api_key
from song_data import SongData
from sources.helper import test_lyrics
from sources.lyrics_source import LyricsSource

request_headers = get_request_headers()
api_key = get_lnm_api_key()
request_headers['Content-type'] = 'application/json'

log = logging.getLogger("LyricsnMusic")


class LyricsnMusic(LyricsSource):

    def __init__(self):
        super().__init__('Lyrics_n_Music')

    def is_album(self) -> bool:
        return False

    def prepare_request(self, song_data: SongData) -> [Optional[str], Optional[object]]:
        data = {
            'api_key': api_key,
            'artist': song_data.artist,
            'track': song_data.title
        }

        request_headers['Content-type'] = 'application/json'
        r_json = requests.get('http://api.lyricsnmusic.com/songs', params=data, headers=request_headers)
        r_json.raise_for_status()
        resp_json = json.loads(r_json.text)
        if not resp_json:
            log.info("Empty response")
            return None, None
        lyrics_url = resp_json[0].get('url')
        if not lyrics_url:
            log.info("No lyrics url returned")
            return None, None

        del request_headers['Content-type']
        return lyrics_url, request_headers

    def parse_lyrics(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, 'html.parser')

        # LYRICSnMUSIC pages hold lyrics in a <pre> tag contained in <div> with id='main'
        main_div = soup.find(id="main")
        if main_div and main_div.pre:
            lyrics = main_div.pre.get_text().strip()

            # remove the superflous '\r' characters. '\n' are already present.
            lyrics = re.sub(r'\r', '', lyrics)
            if test_lyrics(lyrics):
                return lyrics
            else:
                log.info('Failed to verify lyrics contents.')
                return None
        else:
            log.info("Unable to find lyrics on page")
            return None
