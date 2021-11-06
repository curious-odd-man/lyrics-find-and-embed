import os

from lyrico.config import Config
ERRORS_TXT_PATH = "errors.txt"

failures = set()


def init():
    with open(os.path.join(Config.lyrics_dir, ERRORS_TXT_PATH), 'r', encoding='utf-8') as f:
        for line in f.readlines():
            line = line.replace("Failed: ", "")
            failures.add(line.split(':')[0])

    print("There are following known failures:")
    for failure in failures:
        print(failure)


def add_error(artist: str, title: str, error: str):
    with open(os.path.join(Config.lyrics_dir, ERRORS_TXT_PATH), 'a', encoding='utf-8') as f:
        f.write("Failed: " + make_name(artist, title) + ": " + error + "\n")


def check(artist: str, title: str) -> bool:
    return make_name(artist, title) in failures


def make_name(artist, title):
    return "[" + artist + " - " + title + "]"
