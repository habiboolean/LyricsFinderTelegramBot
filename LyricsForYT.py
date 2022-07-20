import json
import re
import urllib.parse
from typing import Any

import requests
from bs4 import BeautifulSoup


class LyricsBotExceptions:
    class Error(Exception):
        """Base class for exceptions"""
        pass

    class GetHTMLError(Error):
        """Page unavailable, etc..."""
        pass

    class CantRetrieveArtistOrSongNames(Error):
        """Initial data was found, but cant parse youtube page and get artist or song names from it"""
        pass

    class InitialDataNotFound(Error):
        """
        Cant find metadata - var ytInitialData in youtube page
        Possibly not valid page, video was deleted, etc..
        """
        pass

    class CantFindLyrics(Error):
        """
        Sources of lyrics not found any lyrics for search query.
        Or beautiful soup cant parse page.
        """
        pass

    class InvalidLink(Error):
        """Provided link didnt pass validation"""
        pass


class LyricsForYT:
    # headers for requests
    _header_musixmatch = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                        "(KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36"}
    # using en-US version of youtube, because we search Artist and Song in json in eng
    _header_youtube = {'Accept-Language': 'en-US,en;q=0.5',
                       'User-Agent': 'bot grabbing authors/song names to find response for it (educational project)'}

    @staticmethod
    def _get_html_page(url, headers=None) -> requests.Response:
        """
        Return Response object if no exceptions raised

        :param url: link to page we need HTML
        :param headers: headers for get request
        :raises LyricsBotExceptions.GetHTMLError:
        :return: requests.Response object
        """
        if headers is None:
            headers = {}

        try:
            result = requests.get(url, headers=headers)
        except requests.exceptions.RequestException:
            raise LyricsBotExceptions.GetHTMLError

        if result.status_code != 200:
            # just in case to see if youtube ban ip for too many requests
            print(f'{url} response code: {result.status_code}')
            raise LyricsBotExceptions.GetHTMLError

        return result

    def _get_youtube_metadata(self) -> dict:
        """
        Get dict with ytInitialData and keep only part with song/artist info

        :raises LyricsBotExceptions.InitialDataNotFound:
        :return: dict
        """
        youtube_html = self._get_html_page(self.youtube_link, headers=self._header_youtube)
        #['contents']['twoColumnWatchNextResults']['results']['results']['contents'][1]['videoSecondaryInfoRenderer']['metadataRowContainer']['metadataRowContainerRenderer']['rows']
        #x.engagementPanels[1].engagementPanelSectionListRenderer.content.structuredDescriptionContentRenderer.items[1].videoDescriptionMusicSectionRenderer.carouselLockups[0].carouselLockupRenderer.infoRows
        try:
            json_var_from_youtube = re.search(r'var ytInitialData = (.*?);</script>', youtube_html.text).group(1)
            json_data: dict = json.loads(json_var_from_youtube)
            # take only part we need to extract song/artist names
            json_data = json_data['engagementPanels'][1]['engagementPanelSectionListRenderer']['content']['structuredDescriptionContentRenderer']['items'][1]['videoDescriptionMusicSectionRenderer']['carouselLockups'][0]['carouselLockupRenderer']['infoRows']
        except Exception:
            raise LyricsBotExceptions.InitialDataNotFound

        return json_data

    def _json_get_value_by_first_found_key(self, json_data, key: tuple) -> (bool, Any):
        """
        Search through json data, looking for a keys.
        Returns status of operation and value of first found key
        Depth search through tree dict/list

        :param json_data: dict or list tree
        :param key: keys to find in dict
        :return: tuple(bool, Any)
        """
        if isinstance(json_data, list):
            for v in json_data:
                if isinstance(v, (dict, list)):
                    result = self._json_get_value_by_first_found_key(v, key)
                    if result:
                        return result
        elif isinstance(json_data, dict):
            for k, v in json_data.items():
                if isinstance(v, (dict, list)):

                    result = self._json_get_value_by_first_found_key(v, key)
                    if result:
                        return result
                elif k in key:

                    return True, v

        return False, None

    def _json_find_path_by_value(self, json_data, value, path: list) -> (bool, list):
        """
        Search through json data, looking for a provided value.
        Returns status(bool) of search and path(list) to found key.

        :param json_data: tree structure to search in (i.e. dict or list)
        :param value: value to search for
        :param path: path to value
        :return: tuple(status(bool), path(list))
        """
        def check_for_value(key, val):
            """
            Checks if we found value we search for.
            Just to reduce duplication of code.
            """
            if isinstance(val, (dict, list)):
                p = path.copy()  # copy path to pass it clean, without adding all with for loop below
                p.append(key)
                status, result = self._json_find_path_by_value(val, value, p)
                if status:
                    return status, result
            elif val == value:
                path.append(key)
                return True, path

        if isinstance(json_data, list):
            for k, v in enumerate(json_data):
                temp = check_for_value(k, v)
                if temp:
                    return temp
        elif isinstance(json_data, dict):
            for k, v in json_data.items():
                temp = check_for_value(k, v)
                if temp:
                    return temp

        return False, []

    def _get_song_artist(self, youtube_json_data) -> (str, str):
        """
        Try to retrieve info about song name and artist name for search query in lyrics sources

        :param youtube_json_data: metadata from youtube
        :return: tuple(Song, Artist)
        :raises LyricsBotExceptions.CantRetrieveArtistOrSongNames:
        """
        song = None
        artist = None

        # possible names for keys that can contain Artist or Song
        key_names_for_search = ('text', 'simpleText')

        status, artist_path = self._json_find_path_by_value(youtube_json_data, 'ARTIST', [])
        if status:
            artist_dict = youtube_json_data[artist_path[0]][artist_path[1]]['defaultMetadata']
            s, artist = self._json_get_value_by_first_found_key(artist_dict, key_names_for_search)
            if not s:
                s, artist = self._json_get_value_by_first_found_key(artist_dict, key_names_for_search)

        status, song_path = self._json_find_path_by_value(youtube_json_data, 'SONG', [])
        if status:
            song_dict = youtube_json_data[song_path[0]][song_path[1]]['defaultMetadata']
            s, song = self._json_get_value_by_first_found_key(song_dict, key_names_for_search)
            if not s:
                s, song = self._json_get_value_by_first_found_key(song_dict, key_names_for_search)

        if not artist or not song:
            raise LyricsBotExceptions.CantRetrieveArtistOrSongNames

        # excluding (live) (remastered) (feat) etc
        song = re.sub(r'(\(.*?\))|(\{.*?})|(\".*?\")', '', song)

        # just in case, to simplify artist too
        artist = re.sub(r'(\(.*?\))|(\{.*?})|(\".*?\")', '', artist)

        song = song.replace('/', '-')

        artist = artist.replace('/', '-')

        return song, artist

    def _search_in_azlyrics(self, search_lyrics_query) -> (str, str):
        """
        Lyrics provider - azlyrics.com
        Search in for a song/author

        :param search_lyrics_query:
        :raises LyricsBotExceptions.CantFindLyrics:
        :return: tuple(LinkToLyrics, LyricsText) if found. If nothing found, return - None
        """
        url = f"https://search.azlyrics.com/search.php?q={'+'.join(search_lyrics_query)}"
        html = self._get_html_page(url, self._header_musixmatch)
        soup = BeautifulSoup(html.content, 'html.parser')
        link = soup.find(class_='table table-condensed')
        if not link:
            raise LyricsBotExceptions.CantFindLyrics

        link_lyrics = link.find_next("a")['href']

        html = self._get_html_page(link_lyrics, self._header_musixmatch)
        soup = BeautifulSoup(html.text, 'html.parser')
        lyrics = soup.find(class_='col-xs-12 col-lg-8 text-center').select_one('div:nth-of-type(5)').get_text()
        if lyrics is None:
            return None
        return link_lyrics, lyrics

    def _search_in_musixmatch(self, search_lyrics_query) -> (str, str):
        """
        Lyrics provider - musixmatch.com
        Searching for a song/author

        :param search_lyrics_query:
        :raises LyricsBotExceptions.CantFindLyrics:
        :return: tuple(LinkToLyrics, LyricsText) if found. If nothing found, return - None
        """
        url = f"https://www.musixmatch.com/search/{urllib.parse.quote(' '.join(search_lyrics_query))}"
        html = self._get_html_page(url, self._header_musixmatch)
        soup = BeautifulSoup(html.content, 'html.parser')
        link = soup.find(class_='box-content')
        if not link:
            raise LyricsBotExceptions.CantFindLyrics

        link_lyrics = "https://www.musixmatch.com" + link.find_next("a")['href']

        html = self._get_html_page(link_lyrics, self._header_musixmatch)
        soup = BeautifulSoup(html.text, 'html.parser')
        lyrics = soup.find(class_='col-sm-10 col-md-8 col-ml-6 col-lg-6').find_next('span').get_text()

        if lyrics is None:
            return LyricsBotExceptions.CantFindLyrics

        return link_lyrics, lyrics

    def get_lyrics(self) -> str:
        """
        Main function. Collects all necessary data.
        Tries to find lyrics in lyrics websites one by one.
        If found, returns str.
        If nothing found, raises exception.

        :raises LyricsBotExceptions.CantFindLyrics: If none of sources returned lyrics
        :return: str. Lyrics formatted for telegram(for now)
        """
        # get (var ytInitialData) from youtube link
        youtube_metadata = self._get_youtube_metadata()

        # try to parse song and artist names from metadata
        self.song, self.artist = self._get_song_artist(youtube_metadata)

        # generate search query list for response sources
        search_lyrics_query = self.artist.split() + self.song.split()

        """
        Trying to get lyrics one by one, if we get response from source, return it immediately
        If no response, going through sources.
        If no response from any of them, raise exception
        """
        try:
            link_lyrics, lyrics = self._search_in_musixmatch(search_lyrics_query)
        except Exception:
            pass
        else:
            self.link_lyrics = link_lyrics
            self.raw_lyrics = lyrics
            return self.__format_lyrics_for_telegram()

        try:
            link_lyrics, lyrics = self._search_in_azlyrics(search_lyrics_query)
        except Exception:
            pass
        else:
            self.link_lyrics = link_lyrics
            self.raw_lyrics = lyrics
            return self.__format_lyrics_for_telegram()

        raise LyricsBotExceptions.CantFindLyrics

    def __format_lyrics_for_telegram(self) -> str:
        """Return formatted string for telegram with song name, artist name, link to lyrics found and lyrics"""
        if self.raw_lyrics:
            result = f'<b>Song: {self.song} by {self.artist}</b>' + \
                     f'\n\n{self.link_lyrics}\n\n' + \
                     f'{self.raw_lyrics}'
            return result

        return ""

    def __init__(self, youtube_link: str):
        """

        :param str youtube_link: self-explanatory
        """

        ytl_regex = r"^(?:https?:\/\/)?(?:m\.|www\.)?(?:youtu\.be\/|youtube\.com" \
                    r"\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))(?:(?:\w|-){11})(?:\S+)?$"

        if not youtube_link or not re.match(ytl_regex, youtube_link):
            raise LyricsBotExceptions.InvalidLink

        self.youtube_link = youtube_link  # link to youtube video we try to get lyrics for
        self.link_lyrics = None  # link to lyrics source was found or None
        self.artist = None  # name of band/artist/singer if found in youtube page
        self.song = None  # name of song if found in youtube page
        self.raw_lyrics = None  # lyrics that was extracted from lyrics source or None

    def __len__(self):
        return len(self.__format_lyrics_for_telegram())

    def __str__(self):
        return self.__format_lyrics_for_telegram()
