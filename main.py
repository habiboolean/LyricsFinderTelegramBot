import json
import re

import requests
import tqdm as tqdm
from bs4 import BeautifulSoup


def read_json_path(json_data, key) -> str:
    for i in key.split("."):
        if i in json_data:
            json_data = json_data[i]
        elif i.isdigit():
            json_data = json_data[int(i)]
        else:
            return None
    return json_data


def main():
    url = "http://www.ovh.net/files/10Mb.dat"  # big file test
    # Streaming, so we can iterate over the response.
    response = requests.get(url, stream=True)
    total_size_in_bytes = int(response.headers.get('content-length', 0))
    block_size = 1024  # 1 Kibibyte
    progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
    with open('test.dat', 'wb') as file:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            file.write(data)
    progress_bar.close()
    if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
        print("ERROR, something went wrong")

    # 'https://www.youtube.com/watch?v=30w8DyEJ__0'
    url = 'https://www.youtube.com/watch?v=luwAMFcc2f8'
    headers = {"Accept-Language": "en-US,en;q=0.5"}
    r = requests.get(url, headers=headers)
    txt = re.search(r'var ytInitialData = (.*?);</script>', r.text).group(1)

    data = json.loads(txt)

    key_to_song = "contents.twoColumnWatchNextResults.results.results.contents.1" \
                  ".videoSecondaryInfoRenderer.metadataRowContainer.metadataRowContainerRenderer" \
                  ".rows.3.metadataRowRenderer.contents.0.simpleText"

    key_to_artist = "contents.twoColumnWatchNextResults.results.results.contents" \
                    ".1.videoSecondaryInfoRenderer.metadataRowContainer" \
                    ".metadataRowContainerRenderer.rows.4.metadataRowRenderer.contents.0.runs.0.text"

    song = read_json_path(data, key_to_song)
    artist = read_json_path(data, key_to_artist)

    # excluding (live) (remastered) (feat) etc
    song = re.sub(r'(\(.*?\))|(\{.*?})|(\".*?\")', '', song)

    search = [x for x in artist.split()] + [x for x in song.split()]
    url = f"https://search.azlyrics.com/search.php?q={'+'.join(search)}"
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')

    best_match_link = soup.find(class_='table table-condensed').find_next("a")['href']

    """if not best_match_link:
        search = [x for x in artist.split()] + [song.split()[0]]
        url = f"https://search.azlyrics.com/search.php?q={'+'.join(search)}"
        r = requests.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')
        best_match_link = soup.find(class_='table table-condensed').find_next("a")['href']"""

    r = requests.get(best_match_link)
    soup = BeautifulSoup(r.content, 'html.parser')

    result = soup.find(class_='col-xs-12 col-lg-8 text-center').select_one('div:nth-of-type(5)').get_text()
    if result:
        print(f'Song: {song} by {artist}')
        print(result)
    else:
        print('Lyrics not found, im sorry...')
    n = 1


if __name__ == '__main__':
    main()
