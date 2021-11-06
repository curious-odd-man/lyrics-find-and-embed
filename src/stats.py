from typing import Dict


class Status:
    def __init__(self):
        pass


stats: Dict[str, Status] = dict()


def mk_key(artist: str, title: str) -> str:
    return f'{artist}-{title}'


def set_success(artist: str, title: str):
    stats[mk_key(artist, title)]


def set_failed(artist: str, title: str):
    pass


def set_exists(artist: str, title: str):
    pass


def print_stats():
    pass
