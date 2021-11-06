from main import html_storage, handle_existing_html
from sources.musix_match import MusixMatch

if __name__ == '__main__':
    mxm = MusixMatch()
    text = handle_existing_html('Paradise Lost', [mxm], 'First Light')
    print(text)
