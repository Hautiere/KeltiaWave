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

Le projet source `portal-standalone` reste indépendant et inchangé.
