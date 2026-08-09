import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=commands.DefaultHelpCommand())


@bot.event
async def on_ready():
    log.info(f"Бот запущен как {bot.user} (id={bot.user.id})")

    if not discord.opus.is_loaded():
        try:
            discord.opus.load_opus("libopus.so.0")
            log.info("✅ Opus codec загружен вручную (libopus.so.0)")
        except Exception as e:
            log.error(f"❌ Opus codec НЕ загружен — голос работать не будет: {e!r}")
    else:
        log.info("✅ Opus codec уже загружен")

    try:
        synced = await bot.tree.sync()
        log.info(f"Синхронизировано {len(synced)} slash-команд")
    except Exception as e:
        log.error(f"Ошибка синхронизации команд: {e}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/help"))


async def main():
    if not TOKEN:
        raise RuntimeError("Не найден DISCORD_TOKEN. Добавь его в файл .env (см. .env.example)")

    async with bot:
        for extension in ("cogs.music", "cogs.tarkov"):
            try:
                await bot.load_extension(extension)
                log.info(f"✅ Загружен модуль: {extension}")
            except Exception as e:
                log.error(f"❌ Не удалось загрузить модуль {extension}: {e!r}")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
