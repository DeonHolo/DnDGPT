# Dashboard artwork

The dashboard uses human-painted Romantic and Symbolist artwork, downloaded from Wikimedia Commons and resized to WebP. No generated background art is shipped.

| Theme | Artist and work | Source and reuse information |
| --- | --- | --- |
| Oakwood | Caspar David Friedrich, *The Abbey in the Oakwood*, 1809–1810 | [Wikimedia Commons file and public-domain notice](https://commons.wikimedia.org/wiki/File:Caspar_David_Friedrich_-_Abtei_im_Eichwald_-_Google_Art_Project.jpg) |
| Silent Isle | Arnold Böcklin, *Isle of the Dead*, third version, 1883 | [Wikimedia Commons file and public-domain notice](https://commons.wikimedia.org/wiki/File:Arnold_B%C3%B6cklin_-_Die_Toteninsel_III_(Alte_Nationalgalerie,_Berlin).jpg) |
| Quiet Ink | Plain reading surface | No image |

Both reproductions are identified by Wikimedia Commons as public-domain two-dimensional artwork. Paintings are in the Alte Nationalgalerie, Berlin; digital sources are credited on their respective file pages. Asset files are `dndgpt-app/app/assets/oakwood.webp` and `silent-isle.webp`. The app embeds them inside the dashboard resource, so loading a campaign does not send an image request to a third-party host.
