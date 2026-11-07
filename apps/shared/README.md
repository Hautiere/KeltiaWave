# Vues web sur téléphone

Les vues Record, Transcribe, Live et Komz (`/lire`) reprennent les repères du mobile Android pour les écrans de **700 px ou moins** : navigation, icône vague, couleur de chaque outil, langue audio près du drapeau, langue d’interface dans le menu Langues, cartes et actions compactes. Au-delà, les éléments mobiles sont masqués. Live reprend aussi la disposition de Record sur ordinateur ; les autres outils conservent leur disposition ordinateur.

- `mobile-tools.css` : styles communs, importés dans les trois outils autonomes. Komz les reçoit comme asset via `angular.json` et un lien limité aux petits écrans ; ne pas recopier cette feuille dans le corpus.
- Les quatre Dockerfiles copient `apps/shared/` vers `/shared/` pour préserver les mêmes imports quand chaque frontend est construit sous `/app`.
- `mobile-tools.ts` : libellés et liens entre outils, adaptés à localhost, staging et production. Les aperçus locaux sur les ports 14xxx utilisent le même décalage de 10000 pour naviguer entre les quatre outils sans toucher aux services Docker. Aucune dépendance Angular.
- Chaque composant conserve ses actions et ses règles métier. Les en-têtes et aides mobiles portent la classe `kw-mobile-only`.
- L’icône `keltiawave-wave-icon.svg` dans les assets des quatre fronts est le symbole du logo du portail, sans avatar.

La parité est visuelle : le web utilise le serveur et nécessite Internet ; Live web dépend du partage audio offert par le navigateur. Les capacités Android hors ligne et la capture inter-apps ne sont pas annoncées sur le web.

Vérifications : `npm run build:record`, `build:transcribe`, `build:live`, `build:corpus`, `npm --prefix apps/live test`, et `node --test apps/corpus/tests/*.test.mjs`. Comparer les vues à 320/393/640/700 px et les vues existantes à 768/1440 px. Vérifier aussi les menus, les états de résultat et le défilement ; ne pas lancer d’envoi réel pour un simple contrôle visuel.
