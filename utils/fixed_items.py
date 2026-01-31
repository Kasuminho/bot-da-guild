from discord import app_commands

FIXED_ITEMS = {
    "mysterious essence of magic": {
        "pt": "Essência Misteriosa de Magia",
        "en": "Mysterious Essence of Magic",
    },
    "dazzling mirror of harmony": {
        "pt": "Espelho Deslumbrante da Harmonia",
        "en": "Dazzling Mirror of Harmony",
    },
    "burning eye of chaos": {
        "pt": "Olho Ardente do Caos",
        "en": "Burning Eye of Chaos",
    },
    "strong loop of perseverance": {
        "pt": "Laço Forte da Perseverança",
        "en": "Strong Loop of Perseverance",
    },
    "noble prophet's blood": {
        "pt": "Sangue do Profeta Nobre",
        "en": "Noble Prophet's Blood",
    },
    "shinning ancient tablet": {
        "pt": "Antiga Tábua Reluzente",
        "en": "Shinning Ancient Tablet",
    },
    "heroic weapon crafting blueprint fragment": {
        "pt": "Fragmento de Blueprint de Arma Heroica",
        "en": "Heroic Weapon Crafting Blueprint Fragment",
    },
    "heroic armor crafting blueprint fragment": {
        "pt": "Fragmento de Blueprint de Armadura Heroica",
        "en": "Heroic Armor Crafting Blueprint Fragment",
    },
    "heroic accessory crafting blueprint fragment": {
        "pt": "Fragmento de Blueprint de Acessório Heroico",
        "en": "Heroic Accessory Crafting Blueprint Fragment",
    },
    "heroic skill crafting blueprint fragment": {
        "pt": "Fragmento de Blueprint de Habilidade Heroico",
        "en": "Heroice Skill Book Blueprint Fragment"
    },
    "creature of gaiety": {
        "pt": "Criatura da Felicidade",
        "en": "Creature of Gaiety"
    },
    "elder dragon isteria": {
        "pt": "Dragão Ancião Isteria",
        "en": "Elder Dragon Isteria"
    }
}

ITEM_CHOICES = [
    app_commands.Choice(
        name=f"{v['pt']} / {v['en']}",
        value=k
    )
    for k, v in FIXED_ITEMS.items()
]
