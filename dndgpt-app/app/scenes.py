"""Reading atmospheres and attribution shared by the UI and saved preferences."""

CC_BY = "https://creativecommons.org/licenses/by/4.0/"
CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"
OIL_PAINTINGS = "https://opengameart.org/content/oil-painting-landscapes"
REVOY = "https://www.davidrevoy.com/"


def artwork(id, name, asset, artist, title, source, license, license_url,
            palette="forest", opacity=.62):
    return dict(id=id, name=name, asset=asset, artist=artist, title=title,
                source=source, license=license, license_url=license_url,
                palette=palette, opacity=opacity)


SCENES = (
    dict(id="classic", name="Classic Codex", palette="forest", opacity=0),
    artwork("elderwood", "Oakwood", "oakwood.webp", "Caspar David Friedrich",
            "The Abbey in the Oakwood", "https://commons.wikimedia.org/wiki/File:Caspar_David_Friedrich_-_Abtei_im_Eichwald_-_Google_Art_Project.jpg",
            "Public domain", "https://creativecommons.org/publicdomain/mark/1.0/", opacity=.42),
    artwork("moonkeep", "Silent Isle", "silent-isle.webp", "Arnold Böcklin",
            "Isle of the Dead, third version", "https://commons.wikimedia.org/wiki/File:Arnold_B%C3%B6cklin_-_Die_Toteninsel_III_(Alte_Nationalgalerie,_Berlin).jpg",
            "Public domain", "https://creativecommons.org/publicdomain/mark/1.0/", "slate", .42),
    dict(id="quiet", name="Quiet Ink", palette="ink", opacity=0),
    artwork("swamp-sunset", "Swamp at Sunset", "swamp-sunset.webp", "JAP",
            "Sunset in the Swamp", OIL_PAINTINGS, "CC0", CC0, "copper"),
    artwork("frostpeak", "Frostpeak", "frostpeak.webp", "JAP",
            "Cold Mountain", OIL_PAINTINGS, "CC0", CC0, "slate", .72),
    artwork("desert-skies", "Desert Skies", "desert-skies.webp", "JAP",
            "Clouds in the Desert", OIL_PAINTINGS, "CC0", CC0, "copper", .72),
    artwork("wizard-tower", "Wizard's Tower", "wizard-tower.webp", "JAP",
            "Wizard Tower", OIL_PAINTINGS, "CC0", CC0),
    artwork("azure-valley", "Azure Valley", "azure-valley.webp", "David Revoy",
            "Fantasy Landscape", REVOY + "article201/fantasy-landscape", "CC BY 4.0", CC_BY, "slate", .72),
    artwork("rendezvous", "The Rendezvous", "rendezvous.webp", "David Revoy",
            "The rendezvous", REVOY + "article638/illustration-the-rendezvous", "CC BY 4.0", CC_BY, "violet"),
    artwork("dragonfire", "Dragonfire", "dragonfire.webp", "David Revoy",
            "Confront the Dragon", REVOY + "article935/confront-the-dragon", "CC BY 4.0", CC_BY, "copper", .72),
    artwork("dragon-road", "The Dragon's Road", "dragon-road.webp", "David Revoy",
            "Introduce the Dragon to the Outside World", REVOY + "article937/introduce-the-dragon-to-the-outside-world", "CC BY 4.0", CC_BY, "forest", .72),
    artwork("adventurers", "Adventurers", "adventurers.webp", "Albert Weand & Offirmo",
            "Adventurers", "https://www.offirmo.net/open-source/adventurers-fantasy-illustration/", "CC BY 4.0", CC_BY, "violet", .72),
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
