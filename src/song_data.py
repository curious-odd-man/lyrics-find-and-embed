class SongData:
    def __init__(self, tag, artist: str, album: str, title: str, lyrics: str, song_format: str):
        if artist is None or album is None or title is None:
            raise Exception('artist, album and title must be not None')
        self.song_format = song_format
        self.lyrics = lyrics
        self.album = album
        self.title = title
        self.tag = tag
        self.artist = artist

    def __str__(self) -> str:
        return f'{self.artist}-{self.album}-{self.title}'