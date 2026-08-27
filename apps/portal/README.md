# KeltiaWave Portal

Portail statique autonome du projet KeltiaWave. Il est servi localement sur le
port `4100` par `../../scripts/start-portal.sh` et construit dans Docker par le
service `portal`.

Sur `localhost` ou `127.0.0.1`, les liens Corpus, Record, Transcribe et
Subtitles ciblent automatiquement leurs ports locaux. Sur un domaine public,
les URLs de production présentes dans `index.html` sont conservées.

Le projet source `portal-standalone` reste indépendant et inchangé.
