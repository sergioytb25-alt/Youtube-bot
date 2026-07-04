# YouTube & Twitch pinger (Discord)

Ce bot surveille :
- une chaîne YouTube (via son flux RSS) -> envoie un message Discord à chaque nouvelle vidéo,
- une chaîne Twitch (via l'API Helix) -> envoie un message Discord quand le channel passe en live.

Installation rapide
1. Copier les fichiers dans le repo (index.js, package.json déjà présent, etc.).
2. Créer un webhook Discord et récupérer l'URL.
3. Récupérer l'ID de la chaîne YouTube (format UC...).
4. Créer une application Twitch pour obtenir `client_id` et `client_secret` (Developer Console).
5. Créer un fichier `.env` à la racine en copiant `.env.example` et en remplissant les valeurs.
6. Installer les dépendances :

```
npm install
```
7. Lancer :

```
node index.js
```

Exécution en production
- Utilise PM2, systemd ou Docker (Dockerfile fourni) pour garder le process actif.
- Ajuste `POLL_INTERVAL_MS` si tu veux moins/more de polling (en ms).

Notes
- YouTube: utilisation du flux RSS (pas besoin d'API key).
- Twitch: le bot utilise le flux "streams" via un token application (client credentials). Si tu veux vérifier plusieurs utilisateurs, adapte `checkTwitch` pour itérer plusieurs user_login.
