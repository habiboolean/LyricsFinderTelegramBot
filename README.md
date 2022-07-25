
# YouTube Lyrics Finder Telegram Bot :musical_note:

Bot will search for lyrics, using data get from the YouTube page you provide. See demo below.


## What this for?
It's a simple pet project. The idea was to learn to parse HTML with BS, and create Telegram bots. And this project in the end become a good 'teacher'.
- Learned how to use Beautiful Soup
- Learned how to create bot, basic understanding how async/await works
- Used recursion and DFS algorithm to search in JSON data i get from YouTube. It was a though task, because the part i needed is different in most cases, and can't be accessed by same dict keys path  (was a bit hard for me at first)
- Made a custom exception handler for the class

# DEMO

https://user-images.githubusercontent.com/105993976/180872625-f6ba3ea0-8e69-462e-b4c4-8dc20d3003e2.mp4


## Tech Stack
- **Python** 
- [**Beautiful Soup**](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [**Aiogram**](https://github.com/aiogram/aiogram)
- [**Requests**](https://github.com/psf/requests)

## Features:
- Searching lyrics for music by YouTube link in two sources (more can be added): [musixmatch](https://musixmatch.com) and [azlyrics](https://azlyrics.com)
- If lyrics not found in first source, it goes to next one, until its found or fail.

## TODO:
- Cover with tests (pytest)
- Find some API for lyrics, instead of parsing websites
- Modify parser for YouTube, and try to search for lyrics by only video name if album and artist not provided with dictionary inside YouTube HTML
- Search lyrics not only by YouTube link, but any data user provide, i.e. song name or some lyrics in song. It's not in idea of pet project, because it is too simple, but in general it's good idea

## Quick Start

- Fork and Clone the repository using:
```
git clone https://github.com/habiboolean/LyricsFinderTelegramBot.git
```
- Install dependencies using:
```
pip install -r requirements.txt
```
- provide Telegram Bot Token in main.py:
```
line 13 - BOT_TOKEN
```
- Run main.py:
```
python main.py
```
>![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)

