# Nouvelle navigation Komz et retour à l’interface classique

La page `/lire` propose une interface inspirée des maquettes ordinateur et mobile
fournies le 6 novembre 2026 : thèmes illustrés en colonne sur ordinateur, choix
de thème dans le menu sur mobile, bannière, cartes de sous-domaines, niveaux,
liste de phrases et accès à la pratique. Dans Listen, la liste propose aussi la lecture immédiate de la référence.

## Revenir en arrière immédiatement

- Nouvelle interface : menu **··· → Interface classique** sur ordinateur,
  **Langues → Interface classique** sur mobile.
- Lien direct, même si la nouvelle vue rencontre un problème :
  `/lire?interface=classic`.
- Pour réactiver la nouvelle vue : bouton **Nouvelle interface Komz**, ou
  `/lire?interface=modern`.

Le choix est enregistré dans `localStorage` sous `kw-komz-interface`. Le paramètre
explicite d’URL est prioritaire ; le lien de secours fonctionne donc aussi si la
préférence sauvegardée vaut `modern`. Si le stockage est indisponible, le
paramètre d’URL suffit. Le changement conserve les autres paramètres, dont
`phraseId`. Une bascule est bloquée pendant un enregistrement, un envoi ou une
analyse. Elle ne modifie ni phrase, ni audio, ni compte.

Le template classique reste présent dans `v2-record.component.html` ; le nouvel
explorateur a ses composants et styles encapsulés dans le dossier voisin
`explorer/`. Le parcours d’enregistrement, d’analyse, de comparaison et d’envoi
est conservé. Les liens directs vers une phrase ouvrent toujours la pratique.
La version précédente est également conservée dans le tag Git
`web-2026-11-06-production-komz-650`. Ne pas restaurer une base pour revenir à
l’ancienne ergonomie : seul le choix de vue est nécessaire.

## Données et fonctionnement

- Les compteurs proviennent des phrases réelles et des références approuvées
  sélectionnées par le mécanisme commun Komz/Listen, avec leurs attributions.
- Thème, sous-domaine, niveau, recherche et présence d’audio se combinent.
  Les facettes indiquent le nombre compatible avec les autres filtres actifs.
- « Non classées » conserve l’accès aux phrases sans sous-domaine ; « Sans
  niveau » rend visibles les niveaux non renseignés. Aucun classement n’est
  fabriqué et aucune métadonnée n’est modifiée pour reproduire la maquette.
- Les niveaux connus sont proposés en premier dans la liste, puis les phrases
  sans niveau ; le corpus source n’est pas trié ou modifié en place.
- L’affichage de traduction se règle indépendamment de la langue d’interface :
  FR/EN/CY ou « Breton seul ». En interface bretonne, la vue commence sans
  traduction ; le menu permet d’en choisir une explicitement.
- La liste est paginée par 20 phrases. Les filtres et la page sont conservés
  lorsqu’on ouvre une phrase puis revient à la liste.
- En mode Komz, l’explorateur ne contient aucun lecteur de référence. Il invite à pratiquer :
  enregistrement, analyse et score, puis écoute de la référence dans la vue
  de comparaison. Aucun microphone n’est ouvert dans l’explorateur.
- « Progression » reprend les phrases ayant fait l’objet d’un envoi par le compte
  connecté ; un visiteur est invité à se connecter. Ce n’est pas un score inventé.

Les photos et le logo proviennent des assets existants. Les images d’exemple,
les textes et les nombres des maquettes ne deviennent pas des données de test
ou des valeurs codées en dur dans l’application.

## Vérifications

`npm run build:corpus` et `node --test apps/corpus/tests/*.test.mjs`.
La route Komz est chargée à la demande pour conserver les budgets existants ;
le build initial est passé d’environ 1,10 Mo à 1,02 Mo, sans augmenter les seuils.
Les avertissements préexistants de budget souple et d’inlining de la feuille
mobile servie comme asset restent présents.

Les contrôles navigateur couvrent les largeurs 320, 360, 393, 700, 768, 900, 901,
1 024, 1 280 et 1 536 px, les filtres combinés et vides, les traductions, la
pagination, l’aller-retour vers la pratique, les 13 thèmes, l’absence de lecteur
de référence avant la pratique et le retour classique après rechargement.
L’enregistrement réel et l’envoi d’une voix ne sont pas déclenchés par ces tests.
Cette modification front ne requiert aucune migration ou import en base.

L’en-tête compact reprend les repères de Record et Live : marque, couleurs,
navigation entre outils et langue d’interface. Les titres et les phrases utilisent
une typographie plus compacte sur ordinateur et mobile.

La vue explorateur possède son propre défilement vertical dans le conteneur
mobile ; la pagination reste accessible au bas de la liste. L’en-tête utilise
l’avatar KeltiaWave et les cartes mobiles sont compactes.

## Listen : même présentation, écoute en premier

Listen (`/` ou `/home-bibliotheque`) réutilise le même explorateur avec
`experience="listen"` : thèmes illustrés, sous-domaines, niveaux, recherche,
traductions et pagination. Il présente les phrases bretonnes disposant d’une
référence approuvée, avec l’origine de la voix affichée sous chaque phrase.

Le bouton de lecture est disponible immédiatement dans Listen. Après la fin
de l’écoute, « Répéter et comparer » ouvre Komz avec le `phraseId` correspondant.
Changer de filtre ou quitter l’explorateur arrête la lecture. Les références
écoutées sont mémorisées uniquement pendant la vie de cet explorateur.
Komz conserve son ordre : lire et enregistrer, demander l’analyse, puis écouter
la référence dans la comparaison.

Listen conserve son propre choix d’interface (`kw-listen-interface`) et son lien
de secours `/?interface=classic`, indépendamment du choix fait dans Komz.

Vérification ciblée : `node --test apps/corpus/tests/*.test.mjs` et
`npm run build:corpus`. Les tests de l’explorateur vérifient le déblocage après
la fin de lecture, l’arrêt sur filtrage et l’absence de lecture dans Komz ; ils
ne remplacent pas une écoute réelle dans le navigateur.

## Révision Git

Tag de cette mise à niveau : `web-2026-11-07-komz-listen-sous-domaines`.
Il identifie le code et la documentation ; il ne confirme pas un déploiement distant.

## Ajustements mobiles du 7 novembre 2026

Les barres mobiles proposent Listen, Play et Subtitles en plus des outils audio.
Dans l’explorateur Komz/Listen, les onglets défilent horizontalement avec des
flèches selon le débordement ; le compte reste accessible dans la barre du bas.
Les sous-domaines conservent leurs icônes avec des libellés mobiles de quatre
mots maximum, répartis sur deux lignes équilibrées. Le nom complet est conservé
dans le libellé accessible. La bannière, les niveaux et les résultats de
prononciation sont plus compacts pour rendre les premières phrases visibles.
La présentation ordinateur conserve les libellés complets.

Tag prévu pour la livraison : `web-2026-11-07-komz-listen-mobile-compact`.
