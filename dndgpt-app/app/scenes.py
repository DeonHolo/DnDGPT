"""Reading atmospheres and attribution shared by the UI and saved preferences."""

CC_BY = "https://creativecommons.org/licenses/by/4.0/"
CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"


def artwork(id, name, asset, artist, title, source, license, license_url,
            palette="forest", opacity=.62):
    return dict(id=id, name=name, asset=asset, artist=artist, title=title,
                source=source, license=license, license_url=license_url,
                palette=palette, opacity=opacity)


SCENES = (
    dict(id="classic", name="Classic", palette="forest", opacity=0),
    dict(id="quiet", name="Quiet Ink", palette="ink", opacity=0),
    artwork(
        "elderwood", "Oakwood", "elderwood.avif",
        "Caspar David Friedrich", "The Abbey in the Oakwood",
        "https://commons.wikimedia.org/wiki/File:Caspar_David_Friedrich_-_Abtei_im_Eichwald_-_Google_Art_Project.jpg",
        "Public domain", "https://creativecommons.org/publicdomain/mark/1.0/", "forest", 0.42,
    ),
    artwork(
        "moonkeep", "Silent Isle", "moonkeep.avif",
        "Arnold Böcklin", "Isle of the Dead, third version",
        "https://commons.wikimedia.org/wiki/File:Arnold_B%C3%B6cklin_-_Die_Toteninsel_III_(Alte_Nationalgalerie,_Berlin).jpg",
        "Public domain", "https://creativecommons.org/publicdomain/mark/1.0/", "slate", 0.42,
    ),
    artwork(
        "swamp-sunset", "Swamp at Sunset", "swamp-sunset.avif",
        "JAP", "Sunset in the Swamp",
        "https://opengameart.org/content/oil-painting-landscapes",
        "CC0", CC0, "copper", 0.62,
    ),
    artwork(
        "frostpeak", "Frostpeak", "frostpeak.avif",
        "JAP", "Cold Mountain",
        "https://opengameart.org/content/oil-painting-landscapes",
        "CC0", CC0, "slate", 0.72,
    ),
    artwork(
        "desert-skies", "Desert Skies", "desert-skies.avif",
        "JAP", "Clouds in the Desert",
        "https://opengameart.org/content/oil-painting-landscapes",
        "CC0", CC0, "copper", 0.72,
    ),
    artwork(
        "wizard-tower", "Wizard's Tower", "wizard-tower.avif",
        "JAP", "Wizard Tower",
        "https://opengameart.org/content/oil-painting-landscapes",
        "CC0", CC0, "forest", 0.62,
    ),
    artwork(
        "azure-valley", "Azure Valley", "azure-valley.avif",
        "David Revoy", "Fantasy Landscape",
        "https://www.davidrevoy.com/article201/fantasy-landscape",
        "CC BY 4.0", CC_BY, "slate", 0.72,
    ),
    artwork(
        "rendezvous", "The Rendezvous", "rendezvous.avif",
        "David Revoy", "The rendezvous",
        "https://www.davidrevoy.com/article638/illustration-the-rendezvous",
        "CC BY 4.0", CC_BY, "violet", 0.62,
    ),
    artwork(
        "dragonfire", "Dragonfire", "dragonfire.avif",
        "David Revoy", "Confront the Dragon",
        "https://www.davidrevoy.com/article935/confront-the-dragon",
        "CC BY 4.0", CC_BY, "copper", 0.72,
    ),
    artwork(
        "dragon-road", "The Dragon's Road", "dragon-road.avif",
        "David Revoy", "Introduce the Dragon to the Outside World",
        "https://www.davidrevoy.com/article937/introduce-the-dragon-to-the-outside-world",
        "CC BY 4.0", CC_BY, "forest", 0.72,
    ),
    artwork(
        "adventurers", "Adventurers", "adventurers.avif",
        "Albert Weand & Offirmo", "Adventurers",
        "https://www.offirmo.net/open-source/adventurers-fantasy-illustration/",
        "CC BY 4.0", CC_BY, "violet", 0.72,
    ),
    artwork(
        "mooncap-cavern", "Mooncap Cavern", "mooncap-cavern.avif",
        "olracadejup / ulfus", "Mixed Fantasy Backgrounds: d15",
        "https://opengameart.org/content/mixed-fantasy-backgrounds",
        "CC0", CC0, "slate", 0.65,
    ),
    artwork(
        "sky-citadel", "Sky Citadel", "sky-citadel.avif",
        "olracadejup / ulfus", "Mixed Fantasy Backgrounds: d20",
        "https://opengameart.org/content/mixed-fantasy-backgrounds",
        "CC0", CC0, "slate", 0.65,
    ),
    artwork(
        "root-cellar", "Root Cellar", "root-cellar.avif",
        "olracadejup / ulfus", "Mixed Fantasy Backgrounds: d23",
        "https://opengameart.org/content/mixed-fantasy-backgrounds",
        "CC0", CC0, "copper", 0.65,
    ),
    artwork(
        "wind-shrine", "Wind Shrine", "wind-shrine.avif",
        "Crisisworks", "Asian Mountain Forest BG",
        "https://opengameart.org/content/asian-mountain-forest-bg",
        "CC BY 4.0", CC_BY, "forest", 0.65,
    ),
    artwork(
        "floating-sanctuary", "Floating Sanctuary", "floating-sanctuary.avif",
        "Eon Cire", "Floating island city",
        "https://opengameart.org/content/concept-art-studies-bundle-1",
        "CC0", CC0, "forest", 0.65,
    ),
    artwork(
        "stone-cove", "Stone Cove", "stone-cove.avif",
        "Eon Cire", "Island cove",
        "https://opengameart.org/content/concept-art-studies-bundle-1",
        "CC0", CC0, "slate", 0.65,
    ),
    artwork(
        "mountain-shrine", "Mountain Shrine", "mountain-shrine.avif",
        "Eon Cire", "Monkey mountain shrine",
        "https://opengameart.org/content/concept-art-studies-bundle-1",
        "CC0", CC0, "copper", 0.65,
    ),
    artwork(
        "hillfort", "Hillfort", "hillfort.avif",
        "Drummyfish", "Fantasy Concept 3",
        "https://opengameart.org/content/fantasy-concept-3",
        "CC0", CC0, "forest", 0.65,
    ),
    artwork(
        "dusk-mountains", "Dusk Mountains", "dusk-mountains.avif",
        "ansimuz / Luis Zuno", "Mountain at Dusk Background",
        "https://opengameart.org/content/mountain-at-dusk-background",
        "CC0", CC0, "violet", 0.65,
    ),
    artwork(
        "violet-peaks", "Violet Peaks", "violet-peaks.avif",
        "titi_son", "Fantasy Background",
        "https://opengameart.org/content/fantasy-background",
        "CC0", CC0, "violet", 0.65,
    ),
    artwork(
        "forgotten-shrine", "Forgotten Shrine", "forgotten-shrine.avif",
        "zonked", "Broken Statue Shrine",
        "https://opengameart.org/content/broken-statue-shrine",
        "CC0", CC0, "forest", 0.65,
    ),
    artwork(
        "winter-hollow", "Winter Hollow", "winter-hollow.avif",
        "dlsxjvb1", "Dark winter background",
        "https://opengameart.org/content/dark-winter-background",
        "CC0", CC0, "slate", 0.65,
    ),
    artwork(
        "ancient-gate", "Ancient Gate", "ancient-gate.avif",
        "zonked", "Ancient Abandoned Teleporter",
        "https://opengameart.org/content/ancient-abandoned-teleporter",
        "CC0", CC0, "copper", 0.65,
    ),
    artwork(
        "misty-ramparts", "Misty Ramparts", "misty-ramparts.avif",
        "Kutejnikov", "Background with ruins",
        "https://opengameart.org/content/background-with-ruins",
        "CC0", CC0, "slate", 0.65,
    ),
    artwork(
        "lavender-dusk", "Lavender Dusk", "lavender-dusk.avif",
        "heartpunch!", "lavenderfield_dusk.png",
        "https://heartpunchstudio.itch.io/hand-painted-nature-backgrounds-pack",
        "CC0", CC0, "violet", 0.65,
    ),
    artwork(
        "moonlit-meadow", "Moonlit Meadow", "moonlit-meadow.avif",
        "heartpunch!", "flowermeadow_nightmoon.png",
        "https://heartpunchstudio.itch.io/hand-painted-nature-backgrounds-pack",
        "CC0", CC0, "slate", 0.65,
    ),
    artwork(
        "sunset-hills", "Sunset Hills", "sunset-hills.avif",
        "heartpunch!", "hillside_sunset.png",
        "https://heartpunchstudio.itch.io/hand-painted-nature-backgrounds-pack",
        "CC0", CC0, "copper", 0.65,
    ),
    artwork(
        "glowwood", "Glowwood", "glowwood.avif",
        "heartpunch!", "clearing_greenlights.png",
        "https://heartpunchstudio.itch.io/hand-painted-nature-backgrounds-pack",
        "CC0", CC0, "forest", 0.65,
    ),
    artwork(
        "mountain-dawn", "Mountain Dawn", "mountain-dawn.avif",
        "heartpunch!", "mountainpath_sunrise.png",
        "https://heartpunchstudio.itch.io/hand-painted-nature-backgrounds-pack",
        "CC0", CC0, "copper", 0.65,
    ),
    artwork(
        "moonlit-trail", "Moonlit Trail", "moonlit-trail.avif",
        "heartpunch!", "foresstpath_moonnight.png",
        "https://heartpunchstudio.itch.io/hand-painted-nature-backgrounds-pack",
        "CC0", CC0, "slate", 0.65,
    ),
)
SCENE_IDS = frozenset(scene["id"] for scene in SCENES)

# Opaque reading surfaces keep text legible even in the brighter artwork options.
PALETTES = {
    "forest": {},
    "slate": dict(surface="#101419", soft="#1c232b", paper="#171d24", line="#7b8795",
                  muted="#bac4ce", ink="#edf0f2", gold="#c9d4e0", **{"gold-wash": "#28313c"}, accent="#e4aa8e", focus="#c5daeb"),
    "ink": dict(surface="#121416", soft="#202326", paper="#1a1d20", line="#858781",
                muted="#c3c2bb", ink="#eceae1", gold="#d3bd8a", **{"gold-wash": "#302d25"}, accent="#e4aa8e", focus="#e9cd94"),
    "copper": dict(surface="#191310", soft="#2b211a", paper="#211b17", line="#a58b70",
                   muted="#d0baa4", ink="#f4e5d3", gold="#e6bd79", **{"gold-wash": "#3c2c1d"}, accent="#f1a58c", focus="#f4d39b"),
    "violet": dict(surface="#15121c", soft="#272130", paper="#1f1a26", line="#9886a6",
                   muted="#c7b9d1", ink="#f0e7f4", gold="#d9bce6", **{"gold-wash": "#35273f"}, accent="#edaa9e", focus="#e8cdf0"),
}
