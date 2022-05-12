import json
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup


def read_json_path(json_data, key):
    for i in key.split("."):
        if i in json_data:
            json_data = json_data[i]
        elif i.isdigit():
            json_data = json_data[int(i)]
        else:
            return None
    return json_data


def get_html_page(url, headers={}):
    return requests.get(url, headers=headers)


def json_path_backtrack_by_value(json_dict_or_list, value) -> list:
    """
    Returns json path to the value found
    :param json_dict_or_list: json data
    :param value: value we search for
    :return: list of individual path segments [start, next, ... , final]
    """
    if json_dict_or_list == value:
        return [json_dict_or_list]
    elif isinstance(json_dict_or_list, dict):
        for k, v in json_dict_or_list.items():
            p = json_path_backtrack_by_value(v, value)
            if p:
                return [k] + p
    elif isinstance(json_dict_or_list, list):
        lst = json_dict_or_list
        for i in range(len(lst)):
            p = json_path_backtrack_by_value(lst[i], value)
            if p:
                return [str(i)] + p


def json_path_backtrack_by_key(json_dict_or_list, key) -> list:
    """
    Returns json path to the key found
    :param json_dict_or_list: json data
    :param key: key we search for
    :return: list of individual path segments [start, next, ... , final]
    """
    if json_dict_or_list == key:
        return [json_dict_or_list]
    elif isinstance(json_dict_or_list, dict):
        for k, v in json_dict_or_list.items():
            p = json_path_backtrack_by_key(k, key)
            if p:
                return [k] + p
    elif isinstance(json_dict_or_list, list):
        lst = json_dict_or_list
        for i in range(len(lst)):
            p = json_path_backtrack_by_key(lst[i], key)
            if p:
                return [str(i)] + p


def get_lyrics(url, lyrics_source="azlyrics"):
    sources = ['azlyrics', 'musixmatch']
    if lyrics_source not in sources:
        raise ValueError(f'please choose lyrics_source parameter between {sources}')

    html = get_html_page(url, headers={'Accept-Language': 'en-US,en;q=0.5',
                                       'User-Agent': 'bot grabbing authors of the song'})

    # get json variable from youtube with info about artist and song name (and much more)
    json_var_from_youtube = re.search(r'var ytInitialData = (.*?);</script>', html.text).group(1)
    json_data: dict = json.loads(json_var_from_youtube)

    json_data = json_data['contents']['twoColumnWatchNextResults']['results']['results']['contents'][1][
        'videoSecondaryInfoRenderer']['metadataRowContainer']['metadataRowContainerRenderer']['rows']

    if not json_data:
        raise ValueError('Cant find initial data variable in youtube page...')

    song = json_path_backtrack_by_key(json_data[3]['metadataRowRenderer']['contents'][0], 'text')
    if not song:
        song = json_path_backtrack_by_key(json_data[3]['metadataRowRenderer']['contents'][0], 'simpleText')

    # (json path to variables) youtube change paths, so try different way to get values
    """ 
    key_to_song = "contents.twoColumnWatchNextResults.results.results.contents.1" \
                  ".videoSecondaryInfoRenderer.metadataRowContainer.metadataRowContainerRenderer" \
                  ".rows.3.metadataRowRenderer.contents.0.simpleText"

    "Object.contents.twoColumnWatchNextResults.results.results.contents" \
    "[1].videoSecondaryInfoRenderer.metadataRowContainer" \
    ".metadataRowContainerRenderer.rows[4].metadataRowRenderer.contents[0].simpleText"
    
    key_to_artist = "contents.twoColumnWatchNextResults.results.results.contents" \
                    ".1.videoSecondaryInfoRenderer.metadataRowContainer" \
                    ".metadataRowContainerRenderer.rows.4.metadataRowRenderer.contents.0.runs.0.text"
                    
    """

    # song = read_json_path(json_data, key_to_song)
    # artist = read_json_path(json_data, key_to_artist)

    # k = json_path_backtrack(json_data, 'Artist')[:-3]
    # artist = list(read_json_path(json_data, '.'.join(k) + '.contents')[0].values())[0]
    # k = json_path_backtrack(json_data, 'Song')[:-3]
    # song = list(read_json_path(json_data, '.'.join(k) + '.contents')[0].values())[0]

    k = json_path_backtrack_by_value(json_data, 'Artist')[:-3]
    artist = read_json_path(json_data, '.'.join(k) + '.contents')[0]

    if 'text' in artist.keys():
        artist = artist.get('text')
    elif 'simpleText' in artist.keys():
        artist = artist.get('simpleText')
    else:
        artist = list(artist.values())[0][0]
        raise ValueError('Cant retrieve artist from youtube page')

    k = json_path_backtrack_by_value(json_data, 'Song')[:-3]
    song = read_json_path(json_data, '.'.join(k) + '.contents')[0]
    if 'text' in song.keys():
        song = song.get('text')
    elif 'simpleText' in song.keys():
        song = song.get('simpleText')
    else:
        raise ValueError('Cant retrieve song name from youtube page')

    # excluding (live) (remastered) (feat) etc
    song = re.sub(r'(\(.*?\))|(\{.*?})|(\".*?\")', '', song)

    # just in case, to simplify artist if necessary
    artist = re.sub(r'(\(.*?\))|(\{.*?})|(\".*?\")', '', artist)

    result = ""
    search_lyrics_query = [x for x in artist.split()] + [x for x in song.split()]
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
        result = f'Song: {song} by {artist}\n{best_match_link}\n\n {result.strip().rstrip().lstrip()}'
        return result
    else:
        return None


def main():
    # 'https://www.youtube.com/watch?v=30w8DyEJ__0'
    url = 'https://www.youtube.com/watch?v=luwAMFcc2f8'

    print(get_lyrics('https://www.youtube.com/watch?v=I42-CayHVnA', 'musixmatch'))

    print(get_lyrics('https://www.youtube.com/watch?v=luwAMFcc2f8', 'musixmatch'))

    print(get_lyrics('https://www.youtube.com/watch?v=30w8DyEJ__0', 'musixmatch'))
    n = 1


if __name__ == '__main__':
    main()
