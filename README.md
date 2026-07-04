# YouTube & Twitch pinger (Discord)

Ce bot surveille :
- une chaîne YouTube (via son flux RSS) -> envoie un message Discord à chaque nouvelle vidéo,
- une ou plusieurs chaînes Twitch (via l'API Helix) -> envoie un message Discord quand le channel passe en live.

Support Twitch
- Tu peux surveiller plusieurs comptes Twitch en renseignant l'option `TWITCH_USER_LOGINS` dans le fichier `.env`.
  Exemple: `TWITCH_USER_LOGINS=user1,user2,autrecompte`

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
- Twitch: le bot utilise le flux "streams" via un token application (client credentials). Le bot récupère un token d'application et le met en cache en mémoire pendant sa durée de vie pour réduire les appels.
- Pour obtenir des notifications instantanées et scalables, je peux implémenter Twitch EventSub (nécessite une URL publique pour les callbacks).
