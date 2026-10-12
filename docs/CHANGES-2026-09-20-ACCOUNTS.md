# Comptes et récupération des mots de passe — 20 septembre 2026

- Ajout de comptes par un administrateur, avec rôle, niveau et organisation ; contrôle des doublons et conservation de la session administrateur.
- Affichage/masquage du mot de passe initial pendant la création.
- Changement du mot de passe depuis Mon compte avec confirmation ; ancien mot de passe non demandé à une session authentifiée.
- Bouton compact aligné avec les champs sur ordinateur et délai maximal pour éviter un formulaire bloqué.
- Récupération par email depuis le menu de connexion, y compris l’accès admin.
- Vue de récupération distincte : les formulaires de connexion et de création de compte sont masqués.
- Récupération par lien à usage unique, valable 30 minutes, avec page dédiée de choix et confirmation du nouveau mot de passe. Le mot de passe habituel reste valide jusqu’au remplacement ; les sessions précédentes sont alors invalidées.
- Paramètres SMTP OVH privés ; activation indépendante par PASSWORD_RESET_EMAIL_ENABLED.
- Ajout automatique de deux colonnes nullable aux comptes existants au démarrage du backend.

Validation : tests backend des comptes, mots de passe, expiration, permissions et erreurs SMTP ; compilation Angular. Aucun email réel n’est envoyé par les tests.

Déploiement prévu : tag annoté `staging-accounts-password-recovery-2026-09-20`, backend et Corpus du staging uniquement. Sauvegarde PostgreSQL et conservation des images précédentes avant activation ; production inchangée.

## Correction du parcours email

Le lien remplace le mot de passe temporaire après un retour utilisateur signalant un échec de connexion. La présence d’un autre onglet connecté n’est pas une cause établie. Le backend expose `POST /api/auth/reset-password`, indépendant de la session actuelle. `PASSWORD_RESET_URL` fixe le domaine de destination. Les tests couvrent expiration, usage unique, remplacement du lien, validation du mot de passe et révocation des sessions, y compris lorsqu’un autre compte est connecté.

La page de réinitialisation reprend le fond clair plein écran, la typographie et les couleurs de Komz. Le fond photographique historique ne transparaît plus derrière le formulaire, y compris dans les états de confirmation et de lien invalide.
