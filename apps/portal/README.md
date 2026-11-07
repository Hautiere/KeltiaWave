# KeltiaWave Portal

Portail statique autonome du projet KeltiaWave. Il est servi localement sur le
port `4100` par `../../scripts/start-portal.sh` et construit dans Docker par le
service `portal`.

Deux pages d'accueil peuvent être testées sans remplacer l'historique :

- `index.html` : portail initial, avec toutes les applications et les sélecteurs
  de langue ;
- `portal-simple.html` : proposition simplifiée avec cinq actions principales.
  Le lien « Explorer tous les outils » ramène au portail initial.

En local, ouvrir `http://127.0.0.1:4100/` pour la page initiale ou
`http://127.0.0.1:4100/portal-simple.html` pour la proposition. Les deux pages
sont incluses dans l'image Docker du portail.

Sur `localhost` ou `127.0.0.1`, les liens ciblent automatiquement les ports
locaux. Sur `staging.keltiawave.com`, ils restent dans les sous-domaines staging.
Sur les domaines publics, ils ouvrent Play, Komz, Library, Record, Transcribe et
Subtitles sur leurs domaines de production respectifs.

Le footer commun reste visible en bas de la vue PC sans nécessiter de défilement
vertical lorsque le contenu tient dans la hauteur disponible.

La vue mobile utilise une bannière immersive plus compacte, un surfeur discret,
une légende de lieu secondaire et un lanceur d'applications fixe. Les cartes et
le lanceur suivent l'ordre de parcours : Transcribe, Record, Subtitles, Play,
Komz puis Library.

Le surfeur de la bannière est fourni par
`assets/avatar_Keltiawave_surfer_transparent.png`. Ce fichier est un PNG RGBA à
fond réellement transparent ; il ne faut pas le remplacer par une image dont le
damier de transparence est intégré aux pixels.

Le projet source `portal-standalone` reste indépendant et inchangé.

Live est accessible depuis la grille complète des outils : port local `4800`,
`live.staging.keltiawave.com` en staging et `live.keltiawave.com` en production.
Le drapeau gallois affiche Transcribe, Record, Subtitles et Live.
Live transcrit l’audio d’un onglet partagé en breton via Vosk ou en gallois via
W2V sur le backend.
Voir `../live/README.md` pour les limites de capture et la configuration.
