# Envois pédagogiques privés

`/api/practice/*` utilise l’authentification web existante. Les tables additives `practice_classes`, `practice_memberships`, `practice_submissions` sont créées au démarrage avec les tables Corpus ; aucune modification des comptes existants.

- `GET/POST /classes` : classe actuelle et classes du correcteur ; création professeur/admin, code aléatoire 48 bits.
- `POST/DELETE /classes/join` : rejoindre par code / quitter. Une classe courante ; les anciens envois conservent leur destination.
- `GET/POST /submissions` : uniquement les envois de l’utilisateur ; multipart `title`, `transcript`, `file`, audio non vide ≤50 Mo. Sans professeur actif : administration.
- `GET /reviews` : professeur limité à ses classes ; administrateur tous les envois.
- `GET /submissions/{id}/file` : propriétaire/correcteur autorisé, jamais de lien public. Stockage local voisin du répertoire audio public, ou préfixe S3 privé `practice/` ; le bucket doit rester privé.
- `POST /submissions/{id}/review` : `status` (`approved` / `changes_requested`), `feedback` obligatoire. Identité du correcteur calculée côté serveur.

L’approbation pédagogique ne publie pas au catalogue Corpus. Interface dans le compte mobile et `/compte` du Corpus web. Vérification : `backend/.venv/bin/python -m pytest backend/tests/test_practice.py -q`.
