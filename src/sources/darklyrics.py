import re
from typing import Optional, Dict

from bs4 import BeautifulSoup

from build_requests import get_request_headers
from song_data import SongData
from sources.lyrics_source import LyricsSource

regex_non_alphanumeric = re.compile(r'[^a-z0-9]+')
request_headers = get_request_headers()

starts_with_number_pattern = re.compile(r'^\d+\.\s')


def format_song(current_song):
    lower_case_song_name = current_song.lower()
    no_numbering_name = starts_with_number_pattern.sub('', lower_case_song_name)
    return no_numbering_name


class DarkLyrics(LyricsSource):
    def __init__(self):
        super().__init__('Dark_Lyrics')

    def is_album(self) -> bool:
        return True

    def prepare_request(self, song_data: SongData) -> [Optional[str], Optional[object]]:
        artist = regex_non_alphanumeric.sub('', song_data.artist.lower())
        album = regex_non_alphanumeric.sub('', song_data.album.lower())
        return f'http://www.darklyrics.com/lyrics/{artist}/{album}.html', request_headers

    def parse_lyrics(self, html: str, song_title) -> Optional[str]:
        soup = BeautifulSoup(html, 'html.parser')
        songs_with_lyrics = self.__split_by_songs(soup)
        if not songs_with_lyrics or len(songs_with_lyrics) == 0:
            return None

        song_lyrics = songs_with_lyrics[format_song(song_title)]
        if song_lyrics == '':
            return '[Instrumental]'
        else:
            return song_lyrics

    def __split_by_songs(self, soup) -> Optional[Dict[str, str]]:
        lyrics_div_result = soup.findAll('div', {"class": "lyrics"})
        if not lyrics_div_result:
            return None
        songs_with_lyrics = dict()
        current_song = None
        current_lyrics = ''
        for lyrics_div in lyrics_div_result:
            for element in lyrics_div:
                if element.name == 'h3':
                    if current_song is not None:
                        songs_with_lyrics[format_song(current_song)] = current_lyrics.strip('\n \t')
                    current_song = element.text
                    current_lyrics = ''
                else:
                    current_lyrics += str(element.text)

        if current_song is not None and len(current_lyrics) > 0:
            songs_with_lyrics[format_song(current_song)] = current_lyrics.strip('\n \t')

        return songs_with_lyrics
