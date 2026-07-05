# YouTube & Twitch pinger (Discord) - Python version

Ce repo contient désormais une implémentation Python du bot qui :
- surveille une chaîne YouTube via son flux RSS et envoie un message Discord à chaque nouvelle vidéo,
- surveille une ou plusieurs chaînes Twitch (liste séparée par des virgules) via l'API Helix et envoie un message Discord quand un channel passe en live.

Fichiers principaux
- bot.py : script principal (Python)
- requirements.txt : dépendances Python (requests, python-dotenv, feedparser)
- .env.example : exemple de configuration
- data.json : fichier persistant pour éviter les doublons de notifications

Installation
1. Crée un environnement virtuel (optionnel):
   python3 -m venv venv
   source venv/bin/activate

2. Installer les dépendances:
   pip install -r requirements.txt

3. Copier `.env.example` en `.env` et remplir les clés:
   - DISCORD_WEBHOOK_URL
   - TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET
   - TWITCH_USER_LOGINS (ex: user1,user2)
   - (optionnel) YOUTUBE_CHANNEL_ID

4. Lancer:
   python3 bot.py

Docker
- Un Dockerfile est inclus pour exécuter le bot en conteneur (image python:3.11-slim). Exemple:
  docker build -t yt-pinger-py .
  docker run -d --env-file .env --name yt-pinger-py yt-pinger-py

Notes
- Polling: évite d'abaisser POLL_INTERVAL_MS en dessous de 30–60s pour respecter les limites d'API.
- Pour notifications instantanées et scalables, on peut basculer vers Twitch EventSub (webhooks) et PubSub/Push pour YouTube; cela nécessite une URL publique HTTPS.
