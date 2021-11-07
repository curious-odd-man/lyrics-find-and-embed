class SongData:
    def __init__(self, tag, artist: str, title: str, album: str, lyrics: str, song_format: str):
        self.song_format = song_format
        self.lyrics = lyrics
        self.album = album
        self.title = title
        self.tag = tag
        self.artist = artist

    def __str__(self) -> str:
        return f'{self.artist}-{self.album}-{self.title}'