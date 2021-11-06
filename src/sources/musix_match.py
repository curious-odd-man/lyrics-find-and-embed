import logging
import re
import sys
from typing import Dict, Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from sources.helper import test_lyrics
from sources.lyrics_source import LyricsSource

regex_non_alphanum = re.compile(r'[^\w\s\-]*', re.UNICODE)
regex_spaces = re.compile(r'[\s]+', re.UNICODE)

log = logging.getLogger("LyricsSource")


class MusixMatch(LyricsSource):

    def __init__(self):
        super().__init__('Musix Match')

    def prepare_request(self, title: str, artist: str) -> [Optional[str], Optional[object]]:
        refined_artist = self.__refine_text(artist)
        refined_title = self.__refine_text(title)

        # It returns 404, though from browser it return 301 (redirect)
        url = 'https://www.musixmatch.com/lyrics/%s/%s' % (quote(refined_artist), quote(refined_title))

        """
        
        REALLY FUNNY ((((
        GET https://www.musixmatch.com/lyrics/Cream/Strange-Brew

HTTP/1.1 200 OK
Connection: keep-alive
Content-Type: text/html; charset=utf-8
ETag: W/"1e004-nDgPa6cIiO97RULis2Sv5U1oycY"
X-Powered-By: Express
Via: 1.1 varnish, 1.1 varnish
Accept-Ranges: bytes
Date: Sun, 31 Oct 2021 16:20:06 GMT
Age: 0
GEOIP_CITY_COUNTRY_CODE: LV
GEOIP_CITY_COUNTRY_NAME: Latvia
GEOIP_CITY: Riga
GEOIP_LATITUDE: 56.950
GEOIP_LONGITUDE: 24.098
GEOIP_REGION: 25
Set-Cookie: mxm_bab=BB; Expires=Wed, 29 Oct 2031 16:20:06 GMT; Path=/
X-Served-By: cache-dca17764-DCA, cache-bma1660-BMA
X-Cache: MISS, MISS
X-Cache-Hits: 0, 0
X-Timer: S1635697206.792030,VS0,VE618
Vary: Accept-Encoding, X-User-Agent, X-User-Agent

<!DOCTYPE html>
        """
        r = requests.head(url)
        log.info(str(r))
        url = r.headers.get('location')
        return url, None

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
        lyric_html = soup.find(id='lyrics-html')
        lyrics = lyric_html.get_text().strip() if lyric_html else None
        if test_lyrics(lyrics):
            return lyrics
        else:
            return None

        # for div in soup.findAll('span'):
        #     if "class" in div:
        #         if 'lyrics__content__ok' in div["class"]:
        #             lyrics = div.get_text().strip()
        #             break
