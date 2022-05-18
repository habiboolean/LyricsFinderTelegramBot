import json
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup


class LyricsForYT:
    _header_musixmatch = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                        "(KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36"}
    _header_youtube = {'Accept-Language': 'en-US,en;q=0.5',
                       'User-Agent': 'bot grabbing authors/song names to find lyrics for it (educational project)'}

    @staticmethod
    def _get_html_page(url, headers=None):
        if headers is None:
            headers = {}

        try:
            result = requests.get(url, headers=headers)
        except requests.exceptions.RequestException as e:
            # print(f'Error: Cant get this URL: {url}')
            return None

        if result.status_code != 200:
            # print(f'{url} response code: {result.status_code}')
            return None

        return result

    @staticmethod
    def _json_get_value_by_key(json_repr, key):
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

    def _get_youtube_metadata(self):
        youtube_html = self._get_html_page(self.youtube_link, headers=self._header_youtube)

        if not youtube_html:
            return None

        try:
            json_var_from_youtube = re.search(r'var ytInitialData = (.*?);</script>', youtube_html.text).group(1)
            json_data: dict = json.loads(json_var_from_youtube)

            json_data = json_data['contents']['twoColumnWatchNextResults']['results']['results']['contents'][1][
                'videoSecondaryInfoRenderer']['metadataRowContainer']['metadataRowContainerRenderer']['rows']
        except Exception as e:
            # print('Error: cant find or load ytInitialData variable from YouTube page')
            return None

        return json_data

    def _get_song_artist(self, youtube_json_data):

        try:
            song = self._json_get_value_by_key(youtube_json_data[3]['metadataRowRenderer']['contents'][0], 'text')
            if not song:
                song = self._json_get_value_by_key(youtube_json_data[3]['metadataRowRenderer']['contents'][0],
                                                   'simpleText')

            artist = self._json_get_value_by_key(youtube_json_data[4]['metadataRowRenderer']['contents'][0], 'text')
            if not artist:
                artist = self._json_get_value_by_key(youtube_json_data[4]['metadataRowRenderer']['contents'][0],
                                                     'simpleText')
        except Exception as e:
            # print('Error: cant retrieve artist/song names from YouTube page')
            return None

        if not artist or not song:
            # print('Error: cant retrieve artist/song names from YouTube page')
            return None

        # excluding (live) (remastered) (feat) etc
        song = re.sub(r'(\(.*?\))|(\{.*?})|(\".*?\")', '', song)

        # just in case, to simplify artist too
        artist = re.sub(r'(\(.*?\))|(\{.*?})|(\".*?\")', '', artist)

        return song, artist

    def _print_error(self, err_message):
        result = f' {self.youtube_link} '.center(80, '=') + \
                 f'\n{err_message}\n' + \
                 f''.center(80, '=') + \
                 '\n\n'
        print(result)

    def get_lyrics(self):

        # get (var ytInitialData) from youtube link
        youtube_metadata = self._get_youtube_metadata()

        if not youtube_metadata:
            self._print_error('Cant get youtube metadata')
            return None

        # try to parse song and artist names from metadata
        self.song, self.artist = self._get_song_artist(youtube_metadata)

        if not self.song or not self.artist:
            self._print_error('Cant extract song/artist names from youtube metadata')
            return None

        # generate search query list for lyrics sources
        search_lyrics_query = self.artist.split() + self.song.split()

        url = None
        match self.lyrics_source:
            case "azlyrics":
                url = f"https://search.azlyrics.com/search.php?q={'+'.join(search_lyrics_query)}"
            case "musixmatch":
                url = f"https://www.musixmatch.com/search/{urllib.parse.quote(' '.join(search_lyrics_query))}"

        html = self._get_html_page(url, self._header_musixmatch)
        if not html:
            self._print_error(f'Cant get html from lyrics search source: {url}')
            return None

        soup = BeautifulSoup(html.content, 'html.parser')

        # get first(top) link as best match in search result page
        match self.lyrics_source:
            case "azlyrics":
                self.link_lyrics = soup.find(class_='table table-condensed').find_next("a")['href']
            case "musixmatch":
                self.link_lyrics = "https://www.musixmatch.com" + soup.find(class_='box-content').find_next("a")['href']

        html = self._get_html_page(self.link_lyrics, self._header_musixmatch)
        if not html:
            self._print_error(f'Cant get html from lyrics source: {self.link_lyrics}')
            return None
        soup = BeautifulSoup(html.text, 'html.parser')

        match self.lyrics_source:
            case "azlyrics":
                lyrics = soup.find(class_='col-xs-12 col-lg-8 text-center').select_one('div:nth-of-type(5)').get_text()
                if lyrics is None:
                    self._print_error(f'Cant parse lyrics from: {self.link_lyrics}')
                    if input(f'Try different source for {self.youtube_link}? y/n --> ') == 'y':
                        LyricsForYT(self.youtube_link, 'musixmatch')
                        return None
                    else:
                        return None
                self.lyrics = lyrics
            case "musixmatch":
                lyrics = soup.find(class_='col-sm-10 col-md-8 col-ml-6 col-lg-6')
                if lyrics is None:
                    self._print_error(f'Cant parse lyrics from: {self.link_lyrics}')
                    if input(f'Try different source for {self.youtube_link}? y/n --> ') == 'y':
                        LyricsForYT(self.youtube_link, 'azlyrics')
                        return None
                    else:
                        return None
                lyrics = lyrics.find_next(class_='mxm-lyrics')
                lyrics = lyrics.find_next('span').get_text()
                self.lyrics = lyrics
        return True

    def __init__(self, youtube_link: str, lyrics_source='musixmatch'):
        yt_link_check = 'https://www.youtube.com/watch?v='
        self.youtube_link = youtube_link
        self.lyrics_source = lyrics_source
        self.link_lyrics = None
        self.artist = None
        self.song = None
        self.lyrics = None

        if not youtube_link or not youtube_link.startswith(yt_link_check):
            self._print_error(f'Please, enter correct YouTube link')
            return

        lyrics_sources = ['azlyrics', 'musixmatch']
        if lyrics_source not in lyrics_sources:
            self._print_error(f'Please, choose lyrics_source parameter between {lyrics_sources}')
            return

        result = self.get_lyrics()
        if result is None:
            return

    def __str__(self):
        if self.lyrics:
            result = f'Song: {self.song} by {self.artist}'.center(80, '=') + \
                     f'\n{self.link_lyrics}\n' + \
                     f'{self.lyrics}\n' + \
                     f''.center(80, '=') + \
                     '\n\n'
            return result
        else:
            return ""
