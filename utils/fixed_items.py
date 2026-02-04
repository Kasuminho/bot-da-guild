from discord import app_commands

FIXED_ITEMS = {
    "mysterious essence of magic": {
        "pt": "Essência Misteriosa de Magia",
        "en": "Mysterious Essence of Magic",
        "category": "relic",
    },
    "dazzling mirror of harmony": {
        "pt": "Espelho Deslumbrante da Harmonia",
        "en": "Dazzling Mirror of Harmony",
        "category": "relic",
    },
    "burning eye of chaos": {
        "pt": "Olho Ardente do Caos",
        "en": "Burning Eye of Chaos",
        "category": "relic",
    },
    "strong loop of perseverance": {
        "pt": "Laço Forte da Perseverança",
        "en": "Strong Loop of Perseverance",
        "category": "relic",
    },
    "noble prophet's blood": {
        "pt": "Sangue do Profeta Nobre",
        "en": "Noble Prophet's Blood",
        "category": "relic",
    },
    "shinning ancient tablet": {
        "pt": "Antiga Tábua Reluzente",
        "en": "Shinning Ancient Tablet",
        "category": "relic",
    },
    "heroic weapon crafting blueprint fragment": {
        "pt": "Fragmento de Blueprint de Arma Heroica",
        "en": "Heroic Weapon Crafting Blueprint Fragment",
        "category": "blueprint",
    },
    "heroic armor crafting blueprint fragment": {
        "pt": "Fragmento de Blueprint de Armadura Heroica",
        "en": "Heroic Armor Crafting Blueprint Fragment",
        "category": "blueprint",
    },
    "heroic accessory crafting blueprint fragment": {
        "pt": "Fragmento de Blueprint de Acessório Heroico",
        "en": "Heroic Accessory Crafting Blueprint Fragment",
        "category": "blueprint",
    },
    "heroic skill crafting blueprint fragment": {
        "pt": "Fragmento de Blueprint de Habilidade Heroico",
        "en": "Heroice Skill Book Blueprint Fragment",
        "category": "blueprint",
    },
    "creature of gaiety": {
        "pt": "Criatura da Felicidade",
        "en": "Creature of Gaiety",
        "category": "creature",
    },
    "elder dragon isteria": {
        "pt": "Dragão Ancião Isteria",
        "en": "Elder Dragon Isteria",
        "category": "creature",
    },
}

ITEM_CATEGORIES = {key: value["category"] for key, value in FIXED_ITEMS.items()}

CATEGORY_LABELS = {
    "relic": {"pt": "Relíquias", "en": "Relics"},
    "blueprint": {"pt": "Blueprints Heroicos", "en": "Heroic Blueprints"},
    "creature": {"pt": "Criaturas", "en": "Creatures"},
}

ITEM_CHOICES = [
    app_commands.Choice(
        name=f"{v['pt']} / {v['en']}",
        value=k
    )
    for k, v in FIXED_ITEMS.items()
]
