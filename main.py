import json
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup

from LyricsForYT import LyricsForYT

def read_json_path(json_data, key):
    for i in key.split("."):
        if i in json_data:
            json_data = json_data[i]
        elif i.isdigit():
            json_data = json_data[int(i)]
        else:
            return None
    return json_data


def get_html_page(url, headers=None):
    if headers is None:
        headers = {}

    result = requests.get(url, headers=headers)

    if result.status_code != 200:
        raise ConnectionRefusedError(f'{url} response code: {result.status_code}')

    return result


def json_find_value_by_key(json_repr, key):
    results = []

    def _decode_dict(a_dict):
        try:
            results.append(a_dict[key])
        except KeyError:
            pass
        return a_dict

    json.loads(str(json_repr).replace("'", '"'), object_hook=_decode_dict)  # Return value ignored.

    if not results:
        return None
    else:
        return results[0]


def get_json_from_youtube(html):
    # get json variable from YouTube with info about artist and song name (and much more)
    json_var_from_youtube = re.search(r'var ytInitialData = (.*?);</script>', html.text).group(1)
    json_data: dict = json.loads(json_var_from_youtube)

    json_data = json_data['contents']['twoColumnWatchNextResults']['results']['results']['contents'][1][
        'videoSecondaryInfoRenderer']['metadataRowContainer']['metadataRowContainerRenderer']['rows']

    if not json_data:
        raise ValueError('Cant find initial data variable in YouTube page...')

    return json_data


def get_song_artist(youtube_json_data):
    song = json_find_value_by_key(youtube_json_data[3]['metadataRowRenderer']['contents'][0], 'text')
    if not song:
        song = json_find_value_by_key(youtube_json_data[3]['metadataRowRenderer']['contents'][0], 'simpleText')

    artist = json_find_value_by_key(youtube_json_data[4]['metadataRowRenderer']['contents'][0], 'text')
    if not artist:
        artist = json_find_value_by_key(youtube_json_data[4]['metadataRowRenderer']['contents'][0], 'simpleText')

    if not artist or not song:
        raise ValueError('Cant retrieve artist/song names from YouTube page...')

    # excluding (live) (remastered) (feat) etc
    song = re.sub(r'(\(.*?\))|(\{.*?})|(\".*?\")', '', song)

    # just in case, to simplify artist too
    artist = re.sub(r'(\(.*?\))|(\{.*?})|(\".*?\")', '', artist)

    return song, artist


def get_lyrics(url, lyrics_source="azlyrics"):
    sources = ['azlyrics', 'musixmatch']

    if lyrics_source not in sources:
        raise ValueError(f'please choose lyrics_source parameter between {sources}')

    youtube_html = get_html_page(url, headers={'Accept-Language': 'en-US,en;q=0.5',
                                       'User-Agent': 'bot grabbing authors/song names to find lyrics for it'
                                                     ' (educational project)'})
    youtube_json_data = get_json_from_youtube(youtube_html)

    song, artist = get_song_artist(youtube_json_data)

    result = ""

    # generate search query list
    search_lyrics_query = artist.split() + song.split()

    best_match_link = ""
    if lyrics_source == "azlyrics":
        # generate search url string for azlyrics.com
        url = f"https://search.azlyrics.com/search.php?q={'+'.join(search_lyrics_query)}"

        html = get_html_page(url)
        soup = BeautifulSoup(html.content, 'html.parser')

        # get first(top) link as best match in search result page
        best_match_link = soup.find(class_='table table-condensed').find_next("a")['href']

        html = get_html_page(best_match_link)
        soup = BeautifulSoup(html.content, 'html.parser')

        result = soup.find(class_='col-xs-12 col-lg-8 text-center').select_one('div:nth-of-type(5)').get_text()
    elif lyrics_source == "musixmatch":
        url = f"https://www.musixmatch.com/search/{urllib.parse.quote(' '.join(search_lyrics_query))}"
        header = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                "(KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36"}
        html = get_html_page(url, header)
        soup = BeautifulSoup(html.content, 'html.parser')

        # get first(top) link as best match in search result page
        best_match_link = soup.find(class_='box-content').find_next("a")['href']
        best_match_link = f'https://www.musixmatch.com{best_match_link}'
        html = get_html_page(best_match_link, header)
        soup = BeautifulSoup(html.text, 'html.parser')

        result = soup.find(class_='col-sm-10 col-md-8 col-ml-6 col-lg-6')
        result = result.find_next(class_='mxm-lyrics')
        result = result.find_next('span').get_text()

    if result:
        result = f'Song: {song} by {artist}'.center(80, '=') + \
                 f'\n{best_match_link}\n\n' + \
                 f'{result.strip().rstrip().lstrip()}\n\n' + \
                 f''.center(80, '=') + '\n'
        return result
    else:
        return None


def main():
    #l =
    print(LyricsForYT('https://www.youtube.com/watch?v=I42-CayHVnA'))

    #print(get_lyrics('https://www.youtube.com/watch?v=I42-CayHVnA'))

    #print(get_lyrics('https://www.youtube.com/watch?v=luwAMFcc2f8'))

    #print(get_lyrics('https://www.youtube.com/watch?v=30w8DyEJ__0'))


if __name__ == '__main__':
    main()
