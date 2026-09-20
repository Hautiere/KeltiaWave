# Comptes et récupération des mots de passe — 20 septembre 2026

- Ajout de comptes par un administrateur, avec rôle, niveau et organisation ; contrôle des doublons et conservation de la session administrateur.
- Affichage/masquage du mot de passe initial pendant la création.
- Changement du mot de passe depuis Mon compte avec confirmation ; ancien mot de passe non demandé à une session authentifiée.
- Bouton compact aligné avec les champs sur ordinateur et délai maximal pour éviter un formulaire bloqué.
- Récupération par email depuis le menu de connexion, y compris l’accès admin.
- Vue de récupération distincte : les formulaires de connexion et de création de compte sont masqués.
- Mot de passe temporaire stocké sous forme de hash, valable 30 minutes. Le mot de passe habituel reste valide jusqu’au remplacement. Les opérations authentifiées sont limitées tant que le changement est requis.
- Paramètres SMTP OVH privés ; activation indépendante par PASSWORD_RESET_EMAIL_ENABLED.
- Ajout automatique de deux colonnes nullable aux comptes existants au démarrage du backend.

Validation : tests backend des comptes, mots de passe, expiration, permissions et erreurs SMTP ; compilation Angular. Aucun email réel n’est envoyé par les tests.

Déploiement prévu : tag annoté `staging-accounts-password-recovery-2026-09-20`, backend et Corpus du staging uniquement. Sauvegarde PostgreSQL et conservation des images précédentes avant activation ; production inchangée.
