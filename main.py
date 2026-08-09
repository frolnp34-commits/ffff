import asyncio
import ctypes.util
import glob
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


def try_load_opus() -> bool:
    """Пытается загрузить libopus всеми возможными путями.

    На некоторых хостингах (например Railway/Nixpacks) apt-пакет физически
    ставится, но не попадает в стандартные пути поиска библиотек — поэтому
    полагаться на одно имя/путь недостаточно, ищем во всей файловой системе.
    """
    if discord.opus.is_loaded():
        return True

    candidates = []

    found = ctypes.util.find_library("opus")
    if found:
        candidates.append(found)

    candidates += [
        "libopus.so.0",
        "libopus.so",
        "/usr/lib/x86_64-linux-gnu/libopus.so.0",
        "/usr/lib/aarch64-linux-gnu/libopus.so.0",
        "/usr/lib/libopus.so.0",
        "/lib/x86_64-linux-gnu/libopus.so.0",
    ]

    # На всякий случай ищем везде, где могла оказаться библиотека
    # (apt, nix store, conda-окружения и т.п.)
    for pattern in ("/usr/lib/**/libopus.so*", "/nix/store/*/lib/libopus.so*", "/lib/**/libopus.so*"):
        candidates += glob.glob(pattern, recursive=True)

    for path in candidates:
        try:
            discord.opus.load_opus(path)
            log.info(f"✅ Opus codec загружен: {path}")
            return True
        except OSError:
            continue

    return False


@bot.event
async def on_ready():
    log.info(f"Бот запущен как {bot.user} (id={bot.user.id})")

    if not try_load_opus():
        log.error(
            "❌ Opus codec НЕ найден нигде на диске — голос работать не будет. "
            "Проверь, что libopus0 реально ставится на этапе сборки (nixpacks.toml)."
        )

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

