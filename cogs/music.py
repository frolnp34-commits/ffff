import asyncio
import logging
import os
import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands
import re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=spotify_client_id,
    client_secret=spotify_client_secret
))

log = logging.getLogger("bot.music")

YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "cookiefile": "cookies.txt",
    "extractor_args": {
        "youtube": {
            "player_client": ["android", "tv", "web"],
        }
    },
}
def get_youtube_query_from_spotify(url: str) -> str:
    if "spotify.com" not in url:
        return url

    try:
        if "playlist/" in url or "album/" in url:
            match = re.search(r"(playlist|album)/([a-zA-Z0-9]+)", url)
            if not match:
                return url
            
            playlist_id = match.group(2)
            if "playlist" in url:
                results = sp.playlist_tracks(playlist_id, limit=1)
                if results['items']:
                    track_info = results['items'][0]['track']
                else:
                    return url
            else:
                results = sp.album_tracks(playlist_id, limit=1)
                if results['items']:
                    track_info = results['items'][0]
                else:
                    return url
            
            artist_name = track_info['artists'][0]['name']
            song_name = track_info['name']
            return f"ytsearch:{artist_name} - {song_name}"

        elif "track/" in url:
            match = re.search(r"track/([a-zA-Z0-9]+)", url)
            if not match:
                return url
            
            track_id = match.group(1)
            track_info = sp.track(track_id)
            artist_name = track_info['artists'][0]['name']
            song_name = track_info['name']
            return f"ytsearch:{artist_name} - {song_name}"

    except Exception as e:
        print(f"Ошибка Spotify: {e}")
        return url

    return url
    
FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


class Track:
    def __init__(self, title: str, url: str, webpage_url: str, duration: int, requester: str):
        self.title = title
        self.url = url  # прямая ссылка на аудио-поток
        self.webpage_url = webpage_url
        self.duration = duration
        self.requester = requester


class GuildMusicState:
    """Очередь и текущий плеер для одного сервера."""

    def __init__(self, bot: commands.Bot, guild_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.queue: asyncio.Queue[Track] = asyncio.Queue()
        self.voice_client: discord.VoiceClient | None = None
        self.current: Track | None = None
        self.text_channel: discord.abc.Messageable | None = None
        self.play_next_event = asyncio.Event()
        self.player_task = self.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        while True:
            self.play_next_event.clear()
            self.current = await self.queue.get()

            if not self.voice_client or not self.voice_client.is_connected():
                log.warning(f"Трек «{self.current.title}» пропущен: бот не подключён к голосовому каналу")
                if self.text_channel:
                    await self.text_channel.send(
                        f"⚠️ Пропустил **{self.current.title}** — бот не подключён к голосовому каналу (используй `/join`)"
                    )
                continue

            try:
                source = discord.FFmpegPCMAudio(self.current.url, **FFMPEG_OPTS)
                source = discord.PCMVolumeTransformer(source, volume=0.5)
            except Exception as e:
                log.error(f"Не удалось создать аудио-источник для «{self.current.title}»: {e!r}")
                if self.text_channel:
                    await self.text_channel.send(f"❌ Не удалось запустить **{self.current.title}**: {e}")
                continue

            playback_error: Exception | None = None

            def after_play(error):
                nonlocal playback_error
                playback_error = error
                if error:
                    log.error(f"Ошибка воспроизведения «{self.current.title}»: {error!r}")
                self.bot.loop.call_soon_threadsafe(self.play_next_event.set)

            try:
                self.voice_client.play(source, after=after_play)
            except Exception as e:
                log.error(f"voice_client.play() упал для «{self.current.title}»: {e!r}")
                if self.text_channel:
                    await self.text_channel.send(f"❌ Не удалось запустить **{self.current.title}**: {e}")
                continue

            if self.text_channel:
                await self.text_channel.send(f"🎶 Сейчас играет: **{self.current.title}**")

            await self.play_next_event.wait()

            if playback_error and self.text_channel:
                await self.text_channel.send(
                    f"⚠️ Воспроизведение **{self.current.title}** прервалось с ошибкой: {playback_error}"
                )

    def destroy(self):
        if self.player_task:
            self.player_task.cancel()


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.states: dict[int, GuildMusicState] = {}

    def get_state(self, guild_id: int) -> GuildMusicState:
        if guild_id not in self.states:
            self.states[guild_id] = GuildMusicState(self.bot, guild_id)
        return self.states[guild_id]

    async def search(self, query: str) -> Track | None:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
            if "entries" in data:
                data = data["entries"][0]
            return Track(
                title=data.get("title", "Без названия"),
                url=data["url"],
                webpage_url=data.get("webpage_url", ""),
                duration=data.get("duration", 0),
                requester="",
            )

    @app_commands.command(name="join", description="Подключить бота к твоему голосовому каналу")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            await interaction.response.send_message("Сначала зайди в голосовой канал.", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        state = self.get_state(interaction.guild_id)

        if state.voice_client and state.voice_client.is_connected():
            await state.voice_client.move_to(channel)
        else:
            state.voice_client = await channel.connect()

        state.text_channel = interaction.channel
        await interaction.response.send_message(f"Подключился к **{channel.name}** ✅")

    @app_commands.command(name="play", description="Включить трек по названию или ссылке (YouTube)")
    @app_commands.describe(query="Название песни или ссылка на YouTube")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        if not interaction.user.voice:
            await interaction.followup.send("Сначала зайди в голосовой канал.")
            return

        state = self.get_state(interaction.guild_id)
        state.text_channel = interaction.channel

        if not state.voice_client or not state.voice_client.is_connected():
            state.voice_client = await interaction.user.voice.channel.connect()

        try:
            query = get_youtube_query_from_spotify(query)
            track = await self.search(query)
        except Exception as e:
            await interaction.followup.send(f"Не удалось найти трек: {e}")
            return

        track.requester = interaction.user.display_name
        await state.queue.put(track)
        await interaction.followup.send(f"➕ Добавлено в очередь: **{track.title}**")

    @app_commands.command(name="skip", description="Пропустить текущий трек")
    async def skip(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        if state.voice_client and state.voice_client.is_playing():
            state.voice_client.stop()
            await interaction.response.send_message("⏭️ Трек пропущен")
        else:
            await interaction.response.send_message("Сейчас ничего не играет.", ephemeral=True)

    @app_commands.command(name="pause", description="Поставить на паузу")
    async def pause(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        if state.voice_client and state.voice_client.is_playing():
            state.voice_client.pause()
            await interaction.response.send_message("⏸️ Пауза")
        else:
            await interaction.response.send_message("Нечего ставить на паузу.", ephemeral=True)

    @app_commands.command(name="resume", description="Продолжить воспроизведение")
    async def resume(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        if state.voice_client and state.voice_client.is_paused():
            state.voice_client.resume()
            await interaction.response.send_message("▶️ Продолжаю")
        else:
            await interaction.response.send_message("Плеер не на паузе.", ephemeral=True)

    @app_commands.command(name="queue", description="Показать очередь треков")
    async def queue_cmd(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        items = list(state.queue._queue)

        lines = []
        if state.current:
            lines.append(f"▶️ **{state.current.title}** (сейчас играет)")
        for i, t in enumerate(items, 1):
            lines.append(f"{i}. {t.title}")

        if not lines:
            await interaction.response.send_message("Очередь пуста.")
        else:
            await interaction.response.send_message("\n".join(lines))

    @app_commands.command(name="leave", description="Отключить бота от голосового канала")
    async def leave(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        if state.voice_client:
            await state.voice_client.disconnect()
            state.voice_client = None
            await interaction.response.send_message("👋 Отключился")
        else:
            await interaction.response.send_message("Я не в канале.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
