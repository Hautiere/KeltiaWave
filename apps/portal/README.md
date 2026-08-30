# KeltiaWave Portal

Portail statique autonome du projet KeltiaWave. Il est servi localement sur le
port `4100` par `../../scripts/start-portal.sh` et construit dans Docker par le
service `portal`.

Sur `localhost` ou `127.0.0.1`, les liens ciblent automatiquement les ports
locaux. Sur `staging.keltiawave.com`, ils restent dans les sous-domaines staging.
Sur les domaines publics, ils ouvrent Play, Komz, Library, Record, Transcribe et
Subtitles sur leurs domaines de production respectifs.

Le footer commun reste visible en bas de la vue PC sans nécessiter de défilement
vertical lorsque le contenu tient dans la hauteur disponible.

Le surfeur de la bannière est fourni par
`assets/avatar_Keltiawave_surfer_transparent.png`. Ce fichier est un PNG RGBA à
fond réellement transparent ; il ne faut pas le remplacer par une image dont le
damier de transparence est intégré aux pixels.

Le projet source `portal-standalone` reste indépendant et inchangé.
