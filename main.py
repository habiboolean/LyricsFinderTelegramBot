import os
import re

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.utils import executor

from LyricsForYT import LyricsForYT, LyricsBotExceptions

BOT_TOKEN = str(os.environ.get('TELEGRAM_TOKEN'))

# regex to check if youtube link is valid
ytl_regex = r"^(?:https?:\/\/)?(?:m\.|www\.)?(?:youtu\.be\/|youtube\.com" \
            r"\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))(?:(?:\w|-){11})(?:\S+)?$"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot=bot, storage=MemoryStorage())


class BotStates(StatesGroup):
    youtube_link = State()  # if user sent /lyrics without args we ask to provide link after


def validate_youtube_url(url: str) -> bool:
    """
    Return true if url is youtube link

    :param url: link to validate
    :return: bool
    """
    if re.match(ytl_regex, url):
        return True

    return False


@dp.message_handler(commands=['lyrics'])
async def lyrics_handler(event: types.Message):
    """
    Process /lyric command from telegram
    """
    args = event.get_args()
    if not args:  # if we get no link after command
        await BotStates.youtube_link.set()

        await event.answer(
            'Paste youtube link please',
            parse_mode=types.ParseMode.HTML
        )
    else:  # if we get youtube link after command
        if validate_youtube_url(args):
            await generate_response(event, args)
        else:
            await event.reply(
                'Paste correct link please',
                parse_mode=types.ParseMode.HTML
            )


@dp.message_handler(state=BotStates.youtube_link)
async def lyrics_handler(event: types.Message, state: FSMContext):
    """
    Handles /lyrics command that been passed without args
    """
    link = event.text
    if validate_youtube_url(link):
        await generate_response(event, link)
    else:
        await event.reply(
            'Paste correct link please',
            parse_mode=types.ParseMode.HTML
        )

    await state.finish()


@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Cancelled.', reply_markup=types.ReplyKeyboardRemove())


async def generate_response(event: types.Message, link):
    """
    Sending url to LyricsForYT class and try to get response
    Handle response and catch common exceptions
    If no exceptions, parse returned content and sending it to user
    """
    try:
        lyrics = LyricsForYT(link).get_lyrics()
    except LyricsBotExceptions.CantFindLyrics:
        await event.reply(
            'Error: Cant find lyrics',
            parse_mode=types.ParseMode.HTML
        )
    except LyricsBotExceptions.CantRetrieveArtistOrSongNames:
        await event.reply(
            'Error: Cant parse YouTube link',
            parse_mode=types.ParseMode.HTML
        )
    except LyricsBotExceptions.InitialDataNotFound:
        await event.reply(
            'Error: Cant get YouTube metadata',
            parse_mode=types.ParseMode.HTML
        )
    except LyricsBotExceptions.GetHTMLError:
        await event.reply(
            'Error: Unable to find Lyrics',
            parse_mode=types.ParseMode.HTML
        )
    except LyricsBotExceptions.InvalidLink:
        await event.reply(
            'Error: Invalid link to YouTube',
            parse_mode=types.ParseMode.HTML
        )
    except Exception as e:
        print(e)
        await event.reply(
            'Error: Something went wrong...',
            parse_mode=types.ParseMode.HTML
        )
    else:
        if len(lyrics) > 4096:  # telegram message size limit
            chunk_size = 4096
            lyrics_chunks = [lyrics[i:i + chunk_size] for i in range(0, len(lyrics), chunk_size)]
            for s in lyrics_chunks:
                await event.reply(
                    s,
                    parse_mode=types.ParseMode.HTML
                )
        else:
            await event.reply(
                lyrics,
                parse_mode=types.ParseMode.HTML
            )

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
