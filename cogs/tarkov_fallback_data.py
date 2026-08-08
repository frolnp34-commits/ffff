"""
Резервные данные по популярным оружиям Escape from Tarkov.

Используются, когда внешний API (tarkov.dev) недоступен. Обновляй вручную
при желании — сюда можно добавлять любое оружие по тому же образцу.

Данные приблизительные (актуальны на патч 1.1) и предназначены как запасной
вариант, а не как точная замена живому API.
"""

FALLBACK_WEAPONS = {
    "m4a1": {
        "name": "Colt M4A1",
        "caliber": "5.56x45 NATO",
        "base_ergonomics": 40,
        "recoil": "372 / 130 (верт./гориз., база)",
        "build": {
            "title": "Популярный мета-билд «низкая отдача / высокая эргономика»",
            "mods": (
                "Ствол Daniel Defense 14.5\", компенсатор SureFire SOCOM, "
                "рукоятка Magpul MOE, приклад CTR, коллиматор Aimpoint T-1/Eotech, "
                "ПБС (по желанию), лёгкий цевьё RIS II"
            ),
            "note": "Цель билда — снизить отдачу и повысить эргономику для быстрого прицеливания",
        },
        "wiki": "https://escapefromtarkov.fandom.com/wiki/Colt_M4A1_5.56x45_assault_rifle",
    },
    "akm": {
        "name": "Kalashnikov AKM",
        "caliber": "7.62x39",
        "base_ergonomics": 34,
        "recoil": "425 / 152 (верт./гориз., база)",
        "build": {
            "title": "Бюджетный билд под ранний вайп",
            "mods": (
                "Дульный тормоз-компенсатор, пистолетная рукоятка с лучшей эргономикой, "
                "лёгкий коллиматор (например Kobra), опционально скошенное цевьё"
            ),
            "note": "AKM славится дешевизной и убойностью патрона 7.62x39 даже без дорогого обвеса",
        },
        "wiki": "https://escapefromtarkov.fandom.com/wiki/Kalashnikov_AKM_7.62x39_assault_rifle",
    },
    "ak-74": {
        "name": "Kalashnikov AK-74",
        "caliber": "5.45x39",
        "base_ergonomics": 35,
        "recoil": "312 / 122 (верт./гориз., база)",
        "build": {
            "title": "Классический 5.45 билд",
            "mods": "Дульный тормоз, лёгкое цевьё, вертикальная рукоятка, коллиматор",
            "note": "Хороший баланс отдачи и цены, патрон 5.45 неплохо бронебойный",
        },
        "wiki": "https://escapefromtarkov.fandom.com/wiki/Kalashnikov_AK-74_5.45x39_assault_rifle",
    },
    "mp5": {
        "name": "HK MP5",
        "caliber": "9x19",
        "base_ergonomics": 55,
        "recoil": "165 / 116 (верт./гориз., база)",
        "build": {
            "title": "Билд для ближнего боя / зачистки помещений",
            "mods": "Глушитель, коллиматор с широким полем зрения, лёгкая рукоятка",
            "note": "Очень высокая эргономика и управляемость на близких дистанциях",
        },
        "wiki": "https://escapefromtarkov.fandom.com/wiki/Heckler_%26_Koch_MP5_9x19_submachine_gun",
    },
    "vss": {
        "name": "VSS Vintorez",
        "caliber": "9x39",
        "base_ergonomics": 47,
        "recoil": "82 / 68 (верт./гориз., база)",
        "build": {
            "title": "Билд для скрытной игры",
            "mods": "Штатный интегрированный глушитель, оптика (ПСО-1 или аналог)",
            "note": "Почти бесшумное оружие, отличный выбор для тихих рейдов",
        },
        "wiki": "https://escapefromtarkov.fandom.com/wiki/VSS_Vintorez_9x39_special_sniper_rifle",
    },
}


def find_fallback_weapon(query: str) -> dict | None:
    """Ищет оружие в резервной базе по названию (без учёта регистра, частичное совпадение)."""
    key = query.strip().lower().replace(" ", "").replace("-", "")
    for k, v in FALLBACK_WEAPONS.items():
        normalized_key = k.replace("-", "")
        if key == normalized_key or key in normalized_key or normalized_key in key:
            return v
    return None


# Карты Escape from Tarkov: ссылка на вики-страницу (там есть полное изображение
# карты со всеми обозначениями — эвакуации, лут, ключи и т.д.) и на интерактивную
# версию на tarkov.dev. Эти ссылки не протухают от патчей игры, в отличие от
# захардкоженных характеристик, поэтому их достаточно для команды /tarkovmap
# даже без доступа к API.
FALLBACK_MAPS = {
    "customs": {
        "name": "Customs (Таможня)",
        "wiki": "https://escapefromtarkov.fandom.com/wiki/Customs",
        "interactive": "https://tarkov.dev/map/customs",
    },
    "factory": {
        "name": "Factory (Завод)",
        "wiki": "https://escapefromtarkov.fandom.com/wiki/Factory",
        "interactive": "https://tarkov.dev/map/factory",
    },
    "woods": {
        "name": "Woods (Лес)",
        "wiki": "https://escapefromtarkov.fandom.com/wiki/Woods",
        "interactive": "https://tarkov.dev/map/woods",
    },
    "shoreline": {
        "name": "Shoreline (Берег)",
        "wiki": "https://escapefromtarkov.fandom.com/wiki/Shoreline",
        "interactive": "https://tarkov.dev/map/shoreline",
    },
    "interchange": {
        "name": "Interchange (Развязка)",
        "wiki": "https://escapefromtarkov.fandom.com/wiki/Interchange",
        "interactive": "https://tarkov.dev/map/interchange",
    },
    "reserve": {
        "name": "Reserve (Резерв)",
        "wiki": "https://escapefromtarkov.fandom.com/wiki/Reserve",
        "interactive": "https://tarkov.dev/map/reserve",
    },
    "lighthouse": {
        "name": "Lighthouse (Маяк)",
        "wiki": "https://escapefromtarkov.fandom.com/wiki/Lighthouse",
        "interactive": "https://tarkov.dev/map/lighthouse",
    },
    "streets of tarkov": {
        "name": "Streets of Tarkov (Улицы Таркова)",
        "wiki": "https://escapefromtarkov.fandom.com/wiki/Streets_of_Tarkov",
        "interactive": "https://tarkov.dev/map/streets-of-tarkov",
    },
    "the lab": {
        "name": "The Lab (Лаборатория)",
        "wiki": "https://escapefromtarkov.fandom.com/wiki/The_Lab",
        "interactive": "https://tarkov.dev/map/the-lab",
    },
    "ground zero": {
        "name": "Ground Zero (Нулевой отсчёт)",
        "wiki": "https://escapefromtarkov.fandom.com/wiki/Ground_Zero",
        "interactive": "https://tarkov.dev/map/ground-zero",
    },
    "terminal": {
        "name": "Terminal (Терминал)",
        "wiki": "https://escapefromtarkov.fandom.com/wiki/Terminal",
        "interactive": "https://tarkov.dev/map/terminal",
    },
    "labyrinth": {
        "name": "The Labyrinth (Лабиринт)",
        "wiki": "https://escapefromtarkov.fandom.com/wiki/The_Labyrinth",
        "interactive": "https://tarkov.dev/map/labyrinth",
    },
}


def find_fallback_map(query: str) -> dict | None:
    """Ищет карту в резервной базе по названию (без учёта регистра, частичное совпадение)."""
    key = query.strip().lower()
    for k, v in FALLBACK_MAPS.items():
        if key == k or key in k or k in key:
            return v
    return None
