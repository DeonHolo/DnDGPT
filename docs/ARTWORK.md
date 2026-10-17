# Dashboard artwork

Classic Codex is the default: the dark green reading surface with no background image. Quiet Ink is a plain charcoal alternative. Under **View options → Reading atmosphere**, players can also select eleven human-made paintings and fantasy illustrations. Artwork is optional and changes no game state.

| Theme | Artist and work | Source and reuse information |
| --- | --- | --- |
| Oakwood | Caspar David Friedrich, *The Abbey in the Oakwood*, 1809–1810 | [Wikimedia Commons file and public-domain notice](https://commons.wikimedia.org/wiki/File:Caspar_David_Friedrich_-_Abtei_im_Eichwald_-_Google_Art_Project.jpg) |
| Silent Isle | Arnold Böcklin, *Isle of the Dead*, third version, 1883 | [Wikimedia Commons file and public-domain notice](https://commons.wikimedia.org/wiki/File:Arnold_B%C3%B6cklin_-_Die_Toteninsel_III_(Alte_Nationalgalerie,_Berlin).jpg) |
| Quiet Ink | Plain reading surface | No image |
| Swamp at Sunset | JAP, *Sunset in the Swamp* | [OpenGameArt, CC0](https://opengameart.org/content/oil-painting-landscapes) |
| Frostpeak | JAP, *Cold Mountain* | [OpenGameArt, CC0](https://opengameart.org/content/oil-painting-landscapes) |
| Desert Skies | JAP, *Clouds in the Desert* | [OpenGameArt, CC0](https://opengameart.org/content/oil-painting-landscapes) |
| Wizard's Tower | JAP, *Wizard Tower* | [OpenGameArt, CC0](https://opengameart.org/content/oil-painting-landscapes) |
| Azure Valley | David Revoy, *Fantasy Landscape*, 2007 | [Artist's source, CC BY 4.0](https://www.davidrevoy.com/article201/fantasy-landscape) |
| The Rendezvous | David Revoy, *The rendezvous*, 2018 | [Artist's source, CC BY 4.0](https://www.davidrevoy.com/article638/illustration-the-rendezvous) |
| Dragonfire | David Revoy, *Confront the Dragon*, 2022 | [Artist's source, CC BY 4.0](https://www.davidrevoy.com/article935/confront-the-dragon) |
| The Dragon's Road | David Revoy, *Introduce the Dragon to the Outside World*, 2022 | [Artist's source, CC BY 4.0](https://www.davidrevoy.com/article937/introduce-the-dragon-to-the-outside-world) |
| Adventurers | Albert Weand, artist; Offirmo, commissioner and creative input, *Adventurers*, 2022 | [Canonical credit page, CC BY 4.0](https://www.offirmo.net/open-source/adventurers-fantasy-illustration/) |

The first two reproductions are identified by Wikimedia Commons as public-domain two-dimensional artwork. Both paintings are in the Alte Nationalgalerie, Berlin; digital sources are credited on their file pages.

License links: [CC0](https://creativecommons.org/publicdomain/zero/1.0/) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The full CC BY license is included at [LICENSES/CC-BY-4.0.txt](../LICENSES/CC-BY-4.0.txt). Copyright in the modern illustrations remains with their respective artists. These assets are not covered by the software's MIT license.

Images were resized and encoded as WebP; the viewport may crop them to fit. No generative image processing was used. The UI shows the selected work's title, artist, source and license. Each scene's metadata and asset filename are recorded in [app/scenes.py](../dndgpt-app/app/scenes.py). All eleven images are embedded inside the dashboard resource, so opening a campaign sends no image request to third-party art hosts.
