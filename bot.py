# bot.py
"""
Bot Python qui surveille YouTube (RSS) et plusieurs comptes Twitch (Helix) et envoie des pings vers un webhook Discord.
Usage: remplir un fichier .env à la racine (voir .env.example) puis:
    pip install -r requirements.txt
    python3 bot.py
"""

import os
import time
import json
import requests
import feedparser
from typing import Optional, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional if you run with actual environment variables
    pass

WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
# Backwards-compatible: single or multiple YouTube channel IDs
YT_CHANNEL_ID = os.getenv('YOUTUBE_CHANNEL_ID')
YT_CHANNEL_IDS = os.getenv('YOUTUBE_CHANNEL_IDS', '')  # comma separated

TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')
TWITCH_USER_LOGINS = os.getenv('TWITCH_USER_LOGINS', '')  # comma separated
POLL_INTERVAL_MS = int(os.getenv('POLL_INTERVAL_MS', '60000'))

if not WEBHOOK_URL:
    print('Erreur: DISCORD_WEBHOOK_URL non défini')
    raise SystemExit(1)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')

# état persisted
data = { 'youtube': {}, 'twitch': {} }

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
            # merge to keep backward compatibility
            data = { **data, **existing }
    except Exception as e:
        print("Impossible de lire data.json, création d'un nouveau:", e)


def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print('Erreur en sauvegardant data.json', e)


def send_discord(content: str, embed: Optional[dict] = None):
    payload = { 'content': content }
    if embed:
        payload['embeds'] = [embed]
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=15)
        r.raise_for_status()
        print('Webhook envoyé :', content.replace('\n', ' | ')[:120])
    except Exception as e:
        # show response if available
        resp = getattr(e, 'response', None)
        print('Échec envoi webhook:', getattr(resp, 'text', str(e)))


# -------- YouTube (support multiple channels) --------

def _normalize_channel_list(single: Optional[str], multi: str) -> List[str]:
    ids = []
    if single and single.strip():
        ids.append(single.strip())
    if multi:
        for s in multi.split(','):
            s2 = s.strip()
            if s2:
                ids.append(s2)
    # remove duplicates while preserving order
    seen = set()
    out = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def check_youtube():
    channel_ids = _normalize_channel_list(YT_CHANNEL_ID, YT_CHANNEL_IDS)
    if not channel_ids:
        print('Aucun YOUTUBE_CHANNEL_ID ni YOUTUBE_CHANNEL_IDS défini — skip YouTube')
        return

    for channel_id in channel_ids:
        try:
            url = f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
            feed = feedparser.parse(url)
            if not feed.entries:
                print(f'Aucune entrée RSS pour {channel_id}')
                continue
            entry = feed.entries[0]
            link = entry.get('link', '')
            # video id from link e.g. https://www.youtube.com/watch?v=VIDEOID or https://youtu.be/VIDEOID
            video_id = None
            if 'watch?v=' in link:
                video_id = link.split('watch?v=')[-1].split('&')[0]
            else:
                video_id = link.rstrip('/').split('/')[-1]
            title = entry.get('title', 'Nouvelle vidéo')
            published = entry.get('published', '')
            # try to get author/channel name
            channel_name = entry.get('author') or channel_id

            prev_vid = data.get('youtube', {}).get(channel_id)
            if prev_vid != video_id:
                # message format requested by user:
                # @everyone {user.name} VIENT JUSTE DE METTRE UNE VIDÉO EN LIGNE !!!! :Malin:  {url}
                content = f"@everyone {channel_name} VIENT JUSTE DE METTRE UNE VIDÉO EN LIGNE !!!! :Malin:  {link}"
                # send without embed (the user asked specific text), but also include embed for preview
                embed = { 'title': title, 'url': link, 'timestamp': published, 'footer': { 'text': f'YouTube - {channel_name}' } }
                send_discord(content, embed)
                data.setdefault('youtube', {})[channel_id] = video_id
                save_data()
            else:
                # pas de nouvelle vidéo pour ce channel
                pass
        except Exception as e:
            print(f'Erreur check_youtube pour {channel_id}:', e)


# -------- Twitch --------

_twitch_token = None
_twitch_token_expires_at = 0


def get_twitch_app_token():
    global _twitch_token, _twitch_token_expires_at
    now = int(time.time())
    if _twitch_token and now < _twitch_token_expires_at - 5:
        return _twitch_token
    url = 'https://id.twitch.tv/oauth2/token'
    try:
        r = requests.post(url, params={
            'client_id': TWITCH_CLIENT_ID,
            'client_secret': TWITCH_CLIENT_SECRET,
            'grant_type': 'client_credentials'
        }, timeout=15)
        r.raise_for_status()
        j = r.json()
        _twitch_token = j.get('access_token')
        expires_in = int(j.get('expires_in', 0))
        _twitch_token_expires_at = int(time.time()) + expires_in
        return _twitch_token
    except Exception as e:
        raise RuntimeError('Erreur obtention Twitch token: ' + str(e))


def check_twitch():
    if not (TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET and TWITCH_USER_LOGINS):
        print('Twitch non configuré (TWITCH_CLIENT_ID/TWITCH_CLIENT_SECRET/TWITCH_USER_LOGINS) — skip Twitch')
        return
    logins = [s.strip().lower() for s in TWITCH_USER_LOGINS.split(',') if s.strip()]
    if not logins:
        return
    try:
        token = get_twitch_app_token()
        # Build params: multiple user_login allowed
        params = []
        for l in logins:
            params.append(('user_login', l))
        headers = { 'Client-Id': TWITCH_CLIENT_ID, 'Authorization': f'Bearer {token}' }
        r = requests.get('https://api.twitch.tv/helix/streams', params=params, headers=headers, timeout=15)
        r.raise_for_status()
        j = r.json()
        streams = j.get('data', [])
        live_by_login = { s.get('user_login', '').lower(): s for s in streams }

        for login in logins:
            stream = live_by_login.get(login)
            prev = data.get('twitch', {}).get(login, { 'live': False, 'streamId': None })
            if stream and not prev.get('live'):
                # went live
                # get display name if available
                display = stream.get('user_name') or stream.get('user_login') or login
                title = stream.get('title', 'Live')
                url = f'https://twitch.tv/{login}'
                # message format requested by user:
                # @Notif. Live@Notif. Twitch {user.name} est en live sur Twitch ici : {url}
                # We'll send the literal prefixes as the user specified.
                content = f"@Notif. Live@Notif. Twitch {display} est en live sur Twitch ici : {url}"
                embed = { 'title': title, 'url': url, 'description': f"Stream par {display}", 'footer': { 'text': 'Twitch' } }
                send_discord(content, embed)
                data.setdefault('twitch', {})[login] = { 'live': True, 'streamId': stream.get('id') }
                save_data()
            elif not stream and prev.get('live'):
                # went offline
                print(f"{login} est offline maintenant.")
                data.setdefault('twitch', {})[login] = { 'live': False, 'streamId': None }
                save_data()
            else:
                # initialize state if missing
                if login not in data.get('twitch', {}):
                    data.setdefault('twitch', {})[login] = prev
    except Exception as e:
        print('Erreur check_twitch:', e)


# -------- Main loop --------

def main():
    print('Démarrage du bot YouTube/Twitch pinger (Python)')
    check_youtube()
    check_twitch()
    interval = max(1, POLL_INTERVAL_MS // 1000)
    while True:
        try:
            check_youtube()
            check_twitch()
        except Exception as e:
            print('Erreur dans la boucle principale:', e)
        time.sleep(interval)


if __name__ == '__main__':
    main()
