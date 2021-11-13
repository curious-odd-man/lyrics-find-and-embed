import logging
import sys
from time import sleep
from typing import List, Optional, Set

import requests

from song_data import SongData
from song_helper import get_song_list, get_song_data, embedd_lyrics_in_song
from sources.LyricsMode import LyricsMode
from sources.darklyrics import DarkLyrics
from sources.lyrics_source import LyricsSource
from sources.musix_match import MusixMatch
from storage import Storage

HTML_ROOT_DIR = r'D:\Programming\git\lyrico\00_html'
LYRICS_ROOT_DIR = r'D:\Programming\git\lyrico\00_lyrics'

EMBED_IN_SONG = True

all_lyrics_sources: List[LyricsSource] = [DarkLyrics(), LyricsMode(), MusixMatch()]

log = logging.getLogger("main")
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s')

html_storage = Storage(HTML_ROOT_DIR)
lyrics_storage = Storage(LYRICS_ROOT_DIR)

ignore_list: Set[str] = {
    'Фридерик Шопен',
    'Ференц Лист',
    'Пётр Ильич Чайковский',
    'Модест Мусоргский',
    'Иоганн Себастьян Бах',
    'Денис Мацуев',
    'Вольфганг Амадей Моцарт',
    'Антонио Вивальди',
    'Эдвард Григ',
    'Apocalyptica',
    'Людвиг Ван Бетховен',
    'Theatrum',
    'Insanity Play',

    # Russian artists
    'Земфира',
    'Кипелов',
    'Александр Васильев',
    'Ария',
    'Сплин',

# Instrumental
    'Avishai Cohen'
}


def shall_be_ignored(song_data: SongData) -> bool:
    return song_data.artist in ignore_list


def main():
    root_dir = sys.argv[1]
    song_list = get_song_list(root_dir)
    log.info(f'{len(song_list)} songs detected.')
    for song_file in song_list:
        log.info("------------------------------")
        log.info(f'Trying file: {song_file}')
        song_data = get_song_data(song_file)
        if shall_be_ignored(song_data):
            log.info(f'[IGNORE] Song is added to manual ignored list: {song_data}')
            continue
        if song_data.lyrics:
            log.info(f"[EXIST] Lyrics already present in {song_data}")
            continue

        if song_data.artist and song_data.title:
            lyrics = get_lyrics(song_data)
            if lyrics:
                if EMBED_IN_SONG:
                    embedd_lyrics_in_song(song_data, lyrics)
                else:
                    log.info('[CFG] Configured to skip embedding lyrics into song.')
            else:
                log.info(f'[ERR] Could not find lyrics for {song_data}')
        else:
            log.error(f'[ERR] No artist or title in song_file: {song_file}')


def find_source_by_name(source_name: str, lyrics_sources: List[LyricsSource]) -> Optional[LyricsSource]:
    temp_list = lyrics_sources.copy()
    while len(temp_list) > 0:
        if temp_list[0].get_name() == source_name:
            return temp_list[0]
        del temp_list[0]

    return None


def get_lyrics(song_data: SongData) -> str:
    log.info(f'Fetching lyrics for {song_data.artist}-{song_data.title}')
    lyrics_sources = all_lyrics_sources.copy()
    lyrics = handle_existing_html(lyrics_sources, song_data)
    if lyrics:
        return lyrics

    # if we still do NOT have a lyrics - try to fetch them from remaining sources
    while len(lyrics_sources) > 0:
        lyrics_source = lyrics_sources[0]
        del lyrics_sources[0]
        try:
            log.info(f'\tTrying source {lyrics_source.get_name()}')
            log.info('\tWait 10 seconds to avoid spamming')
            sleep(10)  # TODO: Avoid spamming to not get detected
            url, headers = lyrics_source.prepare_request(song_data)
            log.info(f'\tULR: {url}\n\t{headers}')
            if not url:
                log.info('\tUrl was not created')
                continue

            result = requests.get(url, headers=headers)
            log.info(str(result))
            result.raise_for_status()
            html_storage.store(lyrics_source.get_name(), song_data, result.text, lyrics_source.is_album())
            html = html_storage.load(lyrics_source.get_name(), song_data, lyrics_source.is_album())
            lyrics = lyrics_source.parse_lyrics(html, song_data.title)
            lyrics_storage.store(lyrics_source.get_name(), song_data, lyrics)
            log.info(f'[OK] successfully parsed lyrics: {len(lyrics)}')
            return lyrics
        except Exception as e:
            log.error(f"Failed extracting song lyrics from {lyrics_source.get_name()}: " + str(e), exc_info=True)


def handle_existing_html(lyrics_sources, song_data) -> Optional[str]:
    # Do we already have a HTML saved?
    list_of_sources: List[str] = html_storage.get_sources(song_data)
    log.info(f"Already have html file for {list_of_sources}")
    lyrics = None
    for source_name in list_of_sources:
        # Get source for existing html
        lyrics_source: LyricsSource = find_source_by_name(source_name, lyrics_sources)
        if lyrics_source:
            lyrics_sources.remove(lyrics_source)
            # Try and parse lyrics for the source
            lyrics_html = html_storage.load(source_name, song_data, lyrics_source.is_album())
            try:
                lyrics = lyrics_source.parse_lyrics(lyrics_html, song_data.title)
                lyrics_storage.store(source_name, song_data, lyrics)
                log.info(f'[OK] successfully parsed lyrics: {len(lyrics) if lyrics else 0}')
                break
            except Exception as e:
                log.error("Failed to parse existing html: " + str(e), exc_info=True)
    return lyrics


if __name__ == '__main__':
    main()
