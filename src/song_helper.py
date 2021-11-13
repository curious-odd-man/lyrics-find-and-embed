# -*- coding: utf-8 -*-

"""
	Contains helper functions specific to instantiate Song class.
"""

from __future__ import print_function
from __future__ import unicode_literals

import logging
import re
import sys
import os
from typing import Optional, List

import glob2
import platform

from mutagen.id3 import ID3, USLT
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.oggflac import OggFLAC
from mutagen.asf import ASF, ASFUnicodeAttribute

from audio_format_keys import FORMAT_KEYS
from song_data import SongData

log = logging.getLogger(__file__)

audio_formats = ['mp3', 'flac', 'm4a', 'mp4', 'ogg', 'oga', 'wma']


def sanitize_data(s):
    """Removes excess white-space from strings"""

    # If string only empty spaces return None
    if not s or s.isspace():
        return None

    # remove any white-space from beginning or end of the string
    s = s.strip()

    # remove double white-spaces or tabs if any
    s = re.sub(r'\s+', ' ', s)

    return s


def get_key(tag, key, format):
    # data stores the result of key lookup from the dictionary like object
    # returned by mutagen. The results of key lookups are lists or None when it does not exist.
    data = None

    # result is the final value returned by get_key function.
    result = None

    if not tag:
        return result

    # extra keys to read from FLAC and ogg formats
    lyrics_keys = ['LYRICS', 'UNSYNCEDLYRICS', 'UNSYNCED LYRICS', 'SYNCED LYRICS']

    if format == 'mp3':
        ## 'get' for mp3 tags is not fetching lyrics(None). Using getall instead.
        data = tag.getall(key)
        if not len(data):
            return result

        # for USLT(lyrics frame) only return lyrics if exist
        if key == 'USLT':
            result = data[0].text if len(data[0].text) else None
        else:
            # for TPE1, TIT2, TALB frames, the text field is a list itself
            # so we look one list deeper
            result = data[0].text[0]

    elif format == 'wma':
        # For ASF Frames key lookups are lists containing ASFUnicodeAttribute type
        # type objects instead of Unicode objects
        data = tag.get(key)

        # Safely extract the Unicode 'value' from ASFUnicodeAttribute object
        result = tag.get(key)[0].value if data else None
    else:
        # mp4, m4a, flac, ogg

        # For all these formats, the data object is a simple dictionary
        # with keys mapping to lists.

        if format == 'm4a' or format == 'mp4':

            # For python27 encoding key(which is a unicode object due to futures import)
            # to 'latin-1' fixes the fetch from dictionary

            # mp4 standard uses latin-1 encoding for these tag names.
            # \xa9 is copyright symbol in that encoding.
            if sys.version_info[0] < 3:
                key = key.encode('latin-1')

            # Python3 is able to handle it internally due to implicit encoding(?)
            data = tag.get(key)

        if format == 'flac' or format == 'ogg' or format == 'oga':

            if key == FORMAT_KEYS[format]['lyrics']:

                # separately treat lookup of lyrics in these formats

                # Loop through different keys to look for lyrics.

                # 'LYRICS' will be used as standard for 'lyrico' for Vorbis Comments
                # This includes .flac, .ogg(Vorbis and FLAC) files
                for lr_key in lyrics_keys:
                    # also try lowercases
                    data = tag.get(lr_key) or tag.get(lr_key.lower())

                    # if we find lyrics, stop looping
                    if data:
                        break
            else:
                # Normal lookup for other properties
                data = tag.get(key)

        # till here the data ( for mp4, m4a, flac, ogg) will be a list
        # containing the value or None. Safely lookup in list
        result = data[0] if data else None

    # return sanitized value of result
    return sanitize_data(result)


def extract_ogg_tag(path):
    """
        Read tags out of .ogg files encoded with different codecs
        Returns a tuple (tag, error)
    """
    ogg_tag = None
    error = None

    # Encapsulate all try except blocks in if statements.
    # Only read for tag if it already does not exist.

    if not ogg_tag:
        try:
            # Try to read ogg-Vorbis files
            ogg_tag = OggVorbis(path)

        except Exception:
            # move to next codec type
            pass

    if not ogg_tag:
        try:
            # Try to read ogg-FLAC files
            ogg_tag = OggFLAC(path)

        except Exception:
            # move to next codec type
            pass

    if not ogg_tag:
        # log error for user to see
        error = 'Unable to read metadata from the .ogg/.oga file. Only Vorbis and FLAC are supported.'

    return (ogg_tag, error)


def get_song_data(path) -> Optional[SongData]:
    """
        Extracts song artist, album, title and lyrics if present
        from audio file.

        This is method is called by constructor of Song class which uses
        the dict returned to instantiate song objects.

        'path' is the absolute path to the audio file.
    """

    tag = None
    artist = None
    title = None
    album = None
    lyrics = None

    lyrics_tag_present = False

    # format will the part of string after last '.' character
    # only use lowercase for formats
    song_format = path[path.rfind('.') + 1:].lower()

    try:
        if song_format == 'mp3':
            tag = ID3(path)
        if song_format == 'mp4' or song_format == 'm4a':
            tag = MP4(path)
        if song_format == 'flac':
            tag = FLAC(path)
        if song_format == 'wma':
            tag = ASF(path)
        if song_format == 'ogg' or song_format == 'oga':
            tag, error = extract_ogg_tag(path)
    except Exception as e:
        log.error("Failed to parse existing html: " + str(e), exc_info=True)
        return None
    else:
        # This only runs if reading tags creates no exceptions
        artist = get_key(tag, FORMAT_KEYS[song_format]['artist'], song_format)
        title = get_key(tag, FORMAT_KEYS[song_format]['title'], song_format)
        album = get_key(tag, FORMAT_KEYS[song_format]['album'], song_format)
        lyrics = get_key(tag, FORMAT_KEYS[song_format]['lyrics'], song_format)

    return SongData(tag, artist, album, title, lyrics, song_format)


def get_song_list(path) -> List[str]:
    """ Return list of paths to all valid audio files in dir located at path.
        Valid audio formats are imported from settings module.
        Also checks for any inner directories."""

    song_list = []

    for ext in audio_formats:
        pattern = '**/*.' + ext
        pattern_uppercase = '**/*.' + ext.upper()

        song_list.extend(glob2.glob(os.path.join(path, pattern)))

        # Windows is case-insensitive towards extensions. So the glob2 module detects
        # ex. .ogg and .OGG as well. But in Linux the extensions are case-sensitive.

        # Add detection for uppercase extensions
        if platform.system() == 'Linux':
            song_list.extend(glob2.glob(os.path.join(path, pattern_uppercase)))

    return song_list


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
