import asyncio
import logging

import aiohttp
import discord
import feedparser
from discord import app_commands
from discord.ext import commands

from .tarkov_fallback_data import find_fallback_weapon, find_fallback_map, FALLBACK_MAPS

log = logging.getLogger("bot.tarkov")

TARKOV_API_URL = "https://api.tarkov.dev/graphql"
REDDIT_RSS_URL = "https://www.reddit.com/r/EscapefromTarkov/.rss?sort=new"

WEAPON_QUERY = """
query WeaponSearch($name: String!) {
  itemsByName(name: $name) {
    id
    name
    shortName
    wikiLink
    avg24hPrice
    properties {
      ... on ItemPropertiesWeapon {
        caliber
        ergonomics
        recoilVertical
        recoilHorizontal
        fireRate
        defaultPreset {
          name
          containsItems {
            item {
              name
            }
          }
          properties {
            ... on ItemPropertiesPreset {
              ergonomics
              recoilVertical
              recoilHorizontal
            }
          }
        }
      }
    }
  }
}
"""

ITEM_PRICE_QUERY = """
query ItemSearch($name: String!) {
  itemsByName(name: $name) {
    id
    name
    shortName
    avg24hPrice
    low24hPrice
    high24hPrice
    wikiLink
    updated
  }
}
"""

MAPS_QUERY = """
query Maps {
  maps {
    id
    name
    normalizedName
    wiki
    description
    raidDuration
    players
    minPlayerLevel
    maxPlayerLevel
    bosses {
      spawnChance
      boss {
        name
      }
    }
    extracts {
      name
      faction
    }
  }
}
"""


class Tarkov(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None

    async def cog_load(self):
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        if self.session:
            await self.session.close()

    async def gql(self, query: str, variables: dict, retries: int = 3) -> dict:
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                async with self.session.post(
                    TARKOV_API_URL, json={"query": query, "variables": variables}, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    data = await resp.json()
            except Exception as e:
                last_error = str(e)
                await asyncio.sleep(1.5 * attempt)
                continue

            if "errors" in data and data["errors"]:
                parts = []
                for e in data["errors"]:
                    parts.append(e.get("message", str(e)) if isinstance(e, dict) else str(e))
                last_error = "; ".join(parts)
                # API tarkov.dev иногда временно недоступен — просто повторяем попытку
                if "unavailable" in last_error.lower() and attempt < retries:
                    log.warning(f"Попытка {attempt}: {last_error}. Повтор через {1.5 * attempt:.1f}с")
                    await asyncio.sleep(1.5 * attempt)
                    continue
                log.error(f"GraphQL error: {last_error}")
                raise RuntimeError(last_error)

            if "data" not in data or data["data"] is None:
                last_error = "Пустой ответ от API"
                await asyncio.sleep(1.5 * attempt)
                continue

            return data["data"]

        raise RuntimeError(last_error or "Не удалось получить ответ от API")

    @app_commands.command(name="tarkovnews", description="Последние новости/посты по Escape from Tarkov")
    async def tarkov_news(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            async with self.session.get(REDDIT_RSS_URL, headers={"User-Agent": "tarkov-discord-bot/1.0"}) as resp:
                raw = await resp.text()
        except Exception as e:
            await interaction.followup.send(f"Не удалось получить новости: {e}")
            return

        feed = feedparser.parse(raw)
        entries = feed.entries[:5]

        if not entries:
            await interaction.followup.send("Новостей не найдено 😕")
            return

        embed = discord.Embed(
            title="📰 Последние новости Escape from Tarkov",
            color=discord.Color.orange(),
            description="Источник: r/EscapefromTarkov",
        )
        for e in entries:
            embed.add_field(name=e.title[:256], value=f"[Ссылка]({e.link})", inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="tarkovweapon", description="Характеристики оружия и его билд по умолчанию")
    @app_commands.describe(name="Название оружия, например: M4A1, AKM, MP5")
    async def tarkov_weapon(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()
        try:
            data = await self.gql(WEAPON_QUERY, {"name": name})
        except Exception as e:
            fallback = find_fallback_weapon(name)
            if fallback:
                embed = discord.Embed(
                    title=f"{fallback['name']} (резервные данные)",
                    url=fallback.get("wiki"),
                    color=discord.Color.dark_grey(),
                    description="⚠️ tarkov.dev сейчас недоступен — показаны сохранённые данные, могут быть неактуальны.",
                )
                embed.add_field(name="Калибр", value=fallback["caliber"], inline=True)
                embed.add_field(name="Эргономика (база)", value=str(fallback["base_ergonomics"]), inline=True)
                embed.add_field(name="Отдача", value=fallback["recoil"], inline=True)
                embed.add_field(
                    name=f"📦 {fallback['build']['title']}",
                    value=f"Обвес: {fallback['build']['mods']}\n{fallback['build']['note']}",
                    inline=False,
                )
                await interaction.followup.send(embed=embed)
                return

            wiki_url = f"https://escapefromtarkov.fandom.com/wiki/{name.replace(' ', '_')}"
            await interaction.followup.send(
                f"⚠️ Сервис tarkov.dev сейчас недоступен ({e}), а в резервной базе такого оружия нет.\n"
                f"Попробуй позже, либо глянь вручную: {wiki_url}"
            )
            return

        items = [i for i in data["itemsByName"] if i["properties"] and i["properties"].get("caliber")]
        if not items:
            await interaction.followup.send(f"Оружие «{name}» не найдено. Проверь название (обычно на английском).")
            return

        item = items[0]
        props = item["properties"]
        preset = props.get("defaultPreset")
        preset_props = preset.get("properties") if preset else None

        embed = discord.Embed(
            title=item["name"],
            url=item.get("wikiLink"),
            color=discord.Color.dark_gold(),
        )
        embed.add_field(name="Калибр", value=props.get("caliber", "—"), inline=True)
        embed.add_field(name="Эргономика (база)", value=str(props.get("ergonomics", "—")), inline=True)
        embed.add_field(
            name="Отдача (верт./гориз.)",
            value=f"{props.get('recoilVertical', '—')} / {props.get('recoilHorizontal', '—')}",
            inline=True,
        )
        if item.get("avg24hPrice"):
            embed.add_field(name="Средняя цена (24ч)", value=f"{item['avg24hPrice']} ₽", inline=True)

        if preset:
            mods = ", ".join(m["item"]["name"] for m in preset["containsItems"][:10]) or "—"
            ergo = preset_props.get("ergonomics", "—") if preset_props else "—"
            rec_v = preset_props.get("recoilVertical", "—") if preset_props else "—"
            rec_h = preset_props.get("recoilHorizontal", "—") if preset_props else "—"
            embed.add_field(
                name=f"📦 Билд по умолчанию: {preset['name']}",
                value=(f"Эргономика: {ergo}, отдача: {rec_v}/{rec_h}\nОбвес: {mods}"),
                inline=False,
            )
        embed.set_footer(text="Данные: api.tarkov.dev")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="tarkovprice", description="Проверить рыночную цену предмета")
    @app_commands.describe(name="Название предмета")
    async def tarkov_price(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()
        try:
            data = await self.gql(ITEM_PRICE_QUERY, {"name": name})
        except Exception as e:
            await interaction.followup.send(
                f"⚠️ Сервис tarkov.dev сейчас недоступен или отвечает с ошибкой ({e}). "
                "Это сторонний сервис, у него бывают временные сбои — попробуй через минуту."
            )
            return

        items = data["itemsByName"]
        if not items:
            await interaction.followup.send(f"Предмет «{name}» не найден.")
            return

        item = items[0]
        embed = discord.Embed(title=item["name"], url=item.get("wikiLink"), color=discord.Color.green())
        embed.add_field(name="Средняя цена (24ч)", value=f"{item.get('avg24hPrice', '—')} ₽")
        embed.add_field(name="Мин / Макс (24ч)", value=f"{item.get('low24hPrice', '—')} / {item.get('high24hPrice', '—')} ₽")
        embed.set_footer(text="Данные: api.tarkov.dev")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="tarkovmap", description="Карта с обозначениями (эвакуации, боссы, лут)")
    @app_commands.describe(name="Название карты, например: Customs, Woods, Reserve, Streets")
    async def tarkov_map(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()

        fallback = find_fallback_map(name)
        if not fallback:
            names = ", ".join(v["name"] for v in FALLBACK_MAPS.values())
            await interaction.followup.send(f"Карта «{name}» не найдена. Доступные карты: {names}")
            return

        embed = discord.Embed(
            title=f"🗺️ {fallback['name']}",
            url=fallback["wiki"],
            color=discord.Color.blurple(),
            description=(
                f"📍 [Карта с обозначениями (вики, эвакуации/лут/ключи)]({fallback['wiki']})\n"
                f"🕹️ [Интерактивная карта (tarkov.dev)]({fallback['interactive']})"
            ),
        )

        # Пытаемся дотянуться до живых данных с API (боссы, эвакуации, длительность рейда).
        # Если API недоступен — просто показываем ссылки выше без этого блока.
        try:
            data = await self.gql(MAPS_QUERY, {}, retries=1)
            maps = data.get("maps", [])
            match = None
            query_key = name.strip().lower()
            for m in maps:
                if query_key in (m.get("normalizedName") or "").lower() or query_key in (m.get("name") or "").lower():
                    match = m
                    break

            if match:
                if match.get("raidDuration"):
                    embed.add_field(name="⏱️ Длительность рейда", value=f"{match['raidDuration']} мин", inline=True)
                if match.get("players"):
                    embed.add_field(name="👥 Игроков", value=match["players"], inline=True)
                lvl_min, lvl_max = match.get("minPlayerLevel"), match.get("maxPlayerLevel")
                if lvl_min or lvl_max:
                    embed.add_field(name="📈 Уровень", value=f"{lvl_min or '?'}–{lvl_max or '?'}", inline=True)

                bosses = match.get("bosses") or []
                if bosses:
                    boss_lines = ", ".join(
                        f"{b['boss']['name']} ({round(b['spawnChance'] * 100)}%)" for b in bosses if b.get("boss")
                    )
                    if boss_lines:
                        embed.add_field(name="👹 Боссы", value=boss_lines, inline=False)

                extracts = match.get("extracts") or []
                if extracts:
                    ex_lines = ", ".join(e["name"] for e in extracts[:15] if e.get("name"))
                    if ex_lines:
                        embed.add_field(name="🚪 Эвакуации", value=ex_lines, inline=False)
        except Exception as e:
            log.warning(f"Не удалось получить доп. данные карты с API: {e}")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="tarkovmaps", description="Список всех карт со ссылками на обозначения")
    async def tarkov_maps_list(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🗺️ Карты Escape from Tarkov",
            color=discord.Color.blurple(),
            description="Нажми на карту, чтобы открыть версию с обозначениями (эвакуации, лут, ключи)",
        )
        for m in FALLBACK_MAPS.values():
            embed.add_field(
                name=m["name"],
                value=f"[Карта с обозначениями]({m['wiki']}) · [Интерактивная]({m['interactive']})",
                inline=False,
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tarkov(bot))
