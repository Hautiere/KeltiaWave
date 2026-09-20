# Récupération du mot de passe

Dans Corpus, Connexion → Mot de passe oublié permet de demander un mot de passe temporaire par email. Il expire après 30 minutes. Le mot de passe habituel reste utilisable tant que l’utilisateur n’a pas choisi son nouveau mot de passe. Après connexion avec le mot de passe temporaire, les opérations authentifiées sont bloquées sauf la consultation du compte et le changement de mot de passe. Le changement supprime le mot de passe temporaire.

Activation locale dans `.env` :

```dotenv
PASSWORD_RESET_EMAIL_ENABLED=true
SMTP_HOST=
SMTP_PORT=465
SMTP_SECURITY=ssl
SMTP_USERNAME=
SMTP_PASSWORD=
```

Renseigner les paramètres SMTP d’un compte autorisé à envoyer depuis `contact@keltiawave.com`, puis recréer le backend Docker. `starttls` est également pris en charge. L’activation est indépendante de l’envoi des transcriptions. Aucun email n’est envoyé tant que cette configuration n’est pas disponible.

La réponse publique ne révèle pas si un compte existe. Les demandes sont limitées par adresse email et adresse IP (une par minute, dix par heure). Cette limite est en mémoire du processus : utiliser un quota partagé avant un déploiement multi-processus. Les mots de passe temporaires ne sont stockés que sous forme de hash ; les emails ne sont pas journalisés. Une erreur SMTP conserve le mot de passe existant et ne crée pas de nouveau mot de passe temporaire.

Les colonnes de récupération sont ajoutées au démarrage via le mécanisme de compatibilité des tables Corpus. Les tests simulent l’envoi SMTP et ne transmettent aucun email réel.

## Écrans utilisateur

Le menu « Se connecter » expose « Mot de passe oublié ? », y compris dans le formulaire admin. Le lien `/compte?auth=forgot` ouvre une vue dédiée : email, envoi et retour à la connexion. Les formulaires de connexion et d’inscription sont masqués pendant la récupération. Après connexion avec un mot de passe temporaire, l’utilisateur reste sur son compte pour le remplacer.

Un utilisateur déjà connecté renseigne uniquement le nouveau mot de passe et sa confirmation. Le bouton retrouve son état normal après succès, erreur ou dépassement du délai d’attente.

## Administration des comptes

Dans Admin → Comptes, « Ajouter un compte » renseigne le nom, l’email, le rôle, le niveau breton, l’organisation et le mot de passe initial. « Afficher / Masquer » permet de vérifier la saisie. La création ne remplace pas la session de l’admin et refuse les emails déjà utilisés. Le changement de mot de passe à la première connexion est demandé par défaut.

## Staging OVH

Utiliser les mêmes variables SMTP dans le fichier privé `shared/.env.staging`, avec `PASSWORD_RESET_EMAIL_ENABLED=true`. Ne jamais versionner ce fichier ni les identifiants SMTP. Le Compose OVH transmet ces variables au backend. L’expéditeur est `contact@keltiawave.com` ; le destinataire reste l’adresse du compte qui demande la récupération.

La mise en service se vérifie d’abord avec les tests automatisés (SMTP simulé), puis avec une authentification SMTP sans envoi. La réception effective doit être validée par une demande utilisateur depuis le staging.
