import logging
import random
import sys
from typing import List, Optional

import requests
from mutagen.asf import ASFUnicodeAttribute
from mutagen.id3 import USLT

from audio_format_keys import FORMAT_KEYS
from song_helper import get_song_list, get_song_data, SongData
from sources.LyricsMode import LyricsMode
from sources.lyrics_source import LyricsSource
from storage import Storage

HTML_ROOT_DIR = r'D:\Programming\git\lyrico\00_html'
LYRICS_ROOT_DIR = r'D:\Programming\git\lyrico\00_lyrics'

log = logging.getLogger("main")
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s')

html_storage = Storage(HTML_ROOT_DIR)
lyrics_storage = Storage(LYRICS_ROOT_DIR)


def embedd_lyrics_in_song(song_data: SongData, lyrics: str):
    song_format = song_data.song_format
    tag = song_data.tag
    lyrics_key = FORMAT_KEYS[song_format]['lyrics']
    try:
        if song_format == 'mp3':
            # encoding = 3 for UTF-8
            tag.add(USLT(encoding=3, lang=u'eng', desc=u'lyrics.wikia',
                         text=lyrics))

        if song_format == 'm4a' or song_format == 'mp4':
            # lyrics_key = '\xa9lyr'

            if sys.version_info[0] < 3:
                lyrics_key = lyrics_key.encode('latin-1')
            tag[lyrics_key] = lyrics

        # Both flac and ogg/oga(Vorbis & FLAC), are being read/write as Vorbis Comments.
        # Vorbis Comments don't have a standard 'lyrics' tag. The 'LYRICS' tag is
        # most common non-standard tag used for lyrics.
        if song_format == 'flac' or song_format == 'ogg' or song_format == 'oga':
            tag[lyrics_key] = lyrics

        if song_format == 'wma':
            # ASF Format uses ASFUnicodeAttribute objects instead of Python's Unicode
            tag[lyrics_key] = ASFUnicodeAttribute(lyrics)

        tag.save()
    except Exception as e:
        log.error("Failed to save lyrics to file: " + str(e), exc_info=True)


def main():
    root_dir = sys.argv[1]
    song_list = get_song_list(root_dir)
    log.info(f'{len(song_list)} songs detected.')
    for song_file in song_list:
        log.info(f'Trying file: {song_file}')
        song_data = get_song_data(song_file)
        if song_data.lyrics:
            log.info(f"Have a lyrics in {song_data}")
            continue

        if song_data.artist and song_data.title:
            lyrics = get_lyrics(song_data.artist, song_data.title)
            if lyrics:
                embedd_lyrics_in_song(song_data, lyrics)
            else:
                log.info(f'Could not find lyrics for {song_data}')
        else:
            log.error(f'No artist or title in song_file: {song_file}')


def find_source_by_name(source_name: str, lyrics_sources: List[LyricsSource]) -> Optional[LyricsSource]:
    temp_list = lyrics_sources.copy()
    while len(lyrics_sources) > 0:
        if lyrics_sources[0].get_name() == source_name:
            return lyrics_sources[0]
        del temp_list[0]

    return None


def get_lyrics(artist: str, title: str) -> str:
    log.info(f'Fetching lyrics for {artist}-{title}')
    lyrics_sources: List[LyricsSource] = [LyricsMode()]
    random.shuffle(lyrics_sources)
    lyrics = handle_existing_html(artist, lyrics_sources, title)
    if lyrics:
        return lyrics

    # if we still do NOT have a lyrics - try to fetch them from remaining sources
    while len(lyrics_sources) > 0:
        source = lyrics_sources[0]
        del lyrics_sources[0]
        try:
            log.info(f'Trying source {source.get_name()}')
            url, headers = source.prepare_request(title, artist)
            log.info(f'ULR: {url}\n\t{headers}')
            result = requests.get(url, headers=headers)
            log.info(str(result))
            result.raise_for_status()
            html_storage.store(source.get_name(), artist, title, result.text)
            html = html_storage.load(source.get_name(), artist, title)
            lyrics = source.parse_lyrics(html)
            lyrics_storage.store(source.get_name(), artist, title, lyrics)
            log.info(f'successfully parsed lyrics: {len(lyrics)}')
            return lyrics
        except Exception as e:
            log.error(f"Failed extracting song lyrics from {source.get_name()}: " + str(e), exc_info=True)


def handle_existing_html(artist, lyrics_sources, title):
    # Do we already have a HTML saved?
    list_of_sources: List[str] = html_storage.get_sources(artist, title)
    log.info(f"Already have html file for {list_of_sources}")
    lyrics = None
    for source_name in list_of_sources:
        # Get source for existing html
        lyrics_source: LyricsSource = find_source_by_name(source_name, lyrics_sources)
        if lyrics_source:
            lyrics_sources.remove(lyrics_source)
            # Try and parse lyrics for the source
            lyrics_html = html_storage.load(source_name, artist, title)
            try:
                lyrics = lyrics_source.parse_lyrics(lyrics_html)
                lyrics_storage.store(source_name, artist, title, lyrics)
                log.info(f'successfully parsed lyrics: {len(lyrics) if lyrics else 0}')
                break
            except Exception as e:
                log.error("Failed to parse existing html: " + str(e), exc_info=True)
    return lyrics


if __name__ == '__main__':
    main()
