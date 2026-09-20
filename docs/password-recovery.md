# Récupération du mot de passe

Dans Corpus, Connexion → Mot de passe oublié envoie un lien à usage unique valable 30 minutes. Le lien ouvre `/reinitialiser-mot-de-passe`, une page dédiée où saisir et confirmer le nouveau mot de passe, sans connexion préalable ni création de compte. Une session déjà ouverte dans un autre onglet ne change pas le compte ciblé par le lien.

Le mot de passe habituel reste valable jusqu’à la validation du formulaire. La validation invalide le lien, remplace le mot de passe et révoque les sessions précédentes du compte via `auth_version`. Il faut ensuite se reconnecter. Demander un nouveau lien invalide le précédent. Les anciens mots de passe temporaires ne permettent plus de se connecter.

Activation locale dans `.env` :

```dotenv
PASSWORD_RESET_EMAIL_ENABLED=true
PASSWORD_RESET_URL=http://127.0.0.1:4200/reinitialiser-mot-de-passe
SMTP_HOST=
SMTP_PORT=465
SMTP_SECURITY=ssl
SMTP_USERNAME=
SMTP_PASSWORD=
```

Renseigner les paramètres SMTP d’un compte autorisé à envoyer depuis `contact@keltiawave.com`, puis recréer le backend Docker. `starttls` est également pris en charge. L’activation est indépendante de l’envoi des transcriptions. Aucun email n’est envoyé tant que cette configuration n’est pas disponible.

La réponse publique ne révèle pas si un compte existe. Les demandes sont limitées par adresse email et adresse IP (une par minute, dix par heure). Cette limite est en mémoire du processus : utiliser un quota partagé avant un déploiement multi-processus. Le jeton aléatoire de 256 bits est stocké sous forme de hash SHA-256 dans les colonnes de récupération existantes. Il est transmis dans le fragment du lien (absent des requêtes HTTP de navigation), puis dans le corps du POST de validation. Ne pas journaliser les corps de ces requêtes. Le simple affichage de la page ne consomme pas le lien. Une erreur SMTP conserve les identifiants existants.

Les colonnes de récupération sont ajoutées au démarrage via le mécanisme de compatibilité des tables Corpus. Les tests simulent l’envoi SMTP et ne transmettent aucun email réel.

## Écrans utilisateur

Le menu « Se connecter » expose « Mot de passe oublié ? », y compris dans le formulaire admin. Le lien `/compte?auth=forgot` ouvre une vue dédiée : email, envoi et retour à la connexion. Les formulaires de connexion et d’inscription sont masqués pendant la récupération. La page de choix du mot de passe est indépendante du profil connecté et permet d’afficher ou masquer la saisie.

Un utilisateur déjà connecté renseigne uniquement le nouveau mot de passe et sa confirmation. Le bouton retrouve son état normal après succès, erreur ou dépassement du délai d’attente.

## Administration des comptes

Dans Admin → Comptes, « Ajouter un compte » renseigne le nom, l’email, le rôle, le niveau breton, l’organisation et le mot de passe initial. « Afficher / Masquer » permet de vérifier la saisie. La création ne remplace pas la session de l’admin et refuse les emails déjà utilisés. Le changement de mot de passe à la première connexion est demandé par défaut.

## Staging OVH

Utiliser les mêmes variables SMTP dans le fichier privé `shared/.env.staging`, avec `PASSWORD_RESET_EMAIL_ENABLED=true` et `PASSWORD_RESET_URL=https://komz.staging.keltiawave.com/reinitialiser-mot-de-passe`. Cette URL doit être configurée explicitement pour chaque environnement ; HTTPS est obligatoire hors localhost. Ne jamais versionner ce fichier ni les identifiants SMTP. Le Compose OVH transmet ces variables au backend. L’expéditeur est `contact@keltiawave.com` ; le destinataire reste l’adresse du compte qui demande la récupération.

La mise en service se vérifie d’abord avec les tests automatisés (SMTP simulé), puis avec une authentification SMTP sans envoi. La réception effective doit être validée par une demande utilisateur depuis le staging.
