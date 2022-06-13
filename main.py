import asyncio
import os
import re

from aiogram import Bot, Dispatcher, types

from LyricsForYT import LyricsForYT

BOT_TOKEN = str(os.environ.get('TELEGRAM_TOKEN'))


def validate_youtube_url(url: str) -> bool:
    rt = r"^(?:https?:\/\/)?(?:m\.|www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$"
    if re.match(rt, url):
        return True

    return False


async def start_handler(event: types.Message):
    request = event.text.split(" ")
    print(event.text)
    if len(request) == 2:
        cmd = request[0]
        link = request[1]
        if cmd.lower() == '/lyrics' and validate_youtube_url(link):

            await event.reply(
                LyricsForYT(link),
                parse_mode=types.ParseMode.HTML
            )


    await event.answer(
        f"Hello, {event.from_user.get_mention(as_html=True)} 👋!",
        parse_mode=types.ParseMode.HTML,
    )

async def main():
    bot = Bot(token=BOT_TOKEN)
    try:
        disp = Dispatcher(bot=bot)
        disp.register_message_handler(start_handler, commands={"start", "restart", "lyrics"})
        await disp.start_polling()
    finally:
        await bot.close()

asyncio.run(main())

"""from LyricsForYT import LyricsForYT


def main():
    print(LyricsForYT('https://www.youtube.com/watch?v=30w8DyEJ__0'))
    #print(LyricsForYT('https://www.youtube.com/watch?v=tsbg0eiKU1I'))

    #print(LyricsForYT('https://www.youtube.com/watch?v=luwAMFcc2f8'))
    #print(LyricsForYT('hyEJ__0'))
    #print(LyricsForYT('https://www.youtube.com/watch?v=yn22yOik7UI'))


if __name__ == '__main__':
    main()
"""
