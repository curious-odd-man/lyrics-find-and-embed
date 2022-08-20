# Overview

Tool will search for songs recursively in all directories starting with directory you pass as a parameter.
Tool will try several web sites to fetch html documents with lyrics and then try and extract lyrics from those.

It then will create 2 directories:
1. `00_html` - stores all extracted html documents
2. `00_lyrics` - stores all extracted lyrics

Files in those directories are to store intermediate results and do not retry same song several time in the same source.
Meaning you can easily run tool several times with same configuration and it will more or less continue where it left off.

# Notable configurations

In main.py:
1. `HTML_ROOT_DIR` - directory where to store HTML files
2. `LYRICS_ROOT_DIR` - directory wher to store extracted lyrics
3. `ignore_list` - list of artists that should be ignored (for example russian artist could not be found on any of used sites).

# How To Run

Execute `main.py` and pass path to a library directory.

# Note

Tool is not perfect. Some HTMLs could not be parsed. Feel free to make changes and submit PRs.

