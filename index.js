// index.js
try { require('dotenv').config(); } catch (e) { /* dotenv optional */ }
const axios = require('axios');
const { parseStringPromise } = require('xml2js');
const fs = require('fs');
const path = require('path');

const WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL;
const YT_CHANNEL_ID = process.env.YOUTUBE_CHANNEL_ID;
const TWITCH_CLIENT_ID = process.env.TWITCH_CLIENT_ID;
const TWITCH_CLIENT_SECRET = process.env.TWITCH_CLIENT_SECRET;
// Support multiple Twitch logins (comma separated) e.g. "user1,user2"
const TWITCH_USER_LOGINS = process.env.TWITCH_USER_LOGINS; 
const POLL_INTERVAL_MS = parseInt(process.env.POLL_INTERVAL_MS || '60000', 10); // default 60s

if (!WEBHOOK_URL) {
  console.error('Erreur: DISCORD_WEBHOOK_URL non défini');
  process.exit(1);
}

const DATA_FILE = path.join(__dirname, 'data.json');

let data = { lastVideoId: null, twitch: {} }; // twitch: { login: { live: bool, streamId: string|null } }
try {
  if (fs.existsSync(DATA_FILE)) {
    data = Object.assign(data, JSON.parse(fs.readFileSync(DATA_FILE, 'utf8') || '{}'));
  }
} catch (e) {
  console.warn("Impossible de lire data.json, création d'un nouveau", e.message);
}

function saveData() {
  try {
    fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
  } catch (e) {
    console.error('Erreur en sauvegardant data.json', e.message);
  }
}

async function sendDiscord(content, embed) {
  try {
    const body = { content: content };
    if (embed) body.embeds = [embed];
    await axios.post(WEBHOOK_URL, body);
    console.log('Webhook envoyé :', content.replace(/\n/g, ' | ').slice(0, 120));
  } catch (e) {
    console.error('Échec envoi webhook:', e.response?.data || e.message);
  }
}

async function checkYouTube() {
  if (!YT_CHANNEL_ID) {
    console.log('YOUTUBE_CHANNEL_ID non défini — skip YouTube');
    return;
  }
  try {
    const url = `https://www.youtube.com/feeds/videos.xml?channel_id=${YT_CHANNEL_ID}`;
    const res = await axios.get(url, { timeout: 15000 });
    const xml = res.data;
    const obj = await parseStringPromise(xml);
    const entry = obj.feed && obj.feed.entry && obj.feed.entry[0];
    if (!entry) {
      console.log('Aucune entrée RSS YouTube trouvée');
      return;
    }
    const videoId = entry['yt:videoId'][0];
    const title = entry.title[0];
    const published = entry.published && entry.published[0];
    const link = `https://youtu.be/${videoId}`;

    if (data.lastVideoId !== videoId) {
      const msg = `🎬 Nouvelle vidéo : **${title}**\n${link}\nPublié: ${published || 'unknown'}`;
      const embed = {
        title,
        url: link,
        timestamp: published,
        footer: { text: 'YouTube' }
      };
      await sendDiscord(msg, embed);
      data.lastVideoId = videoId;
      saveData();
    }
  } catch (e) {
    console.error('Erreur checkYouTube:', e.response?.data || e.message);
  }
}

// Twitch token cache in memory
let twitchToken = null;
let twitchTokenExpiresAt = 0;

async function getTwitchAppToken() {
  const now = Date.now();
  if (twitchToken && now < twitchTokenExpiresAt - 5000) {
    return twitchToken; // cached
  }
  const url = `https://id.twitch.tv/oauth2/token`;
  try {
    const resp = await axios.post(url, null, {
      params: {
        client_id: TWITCH_CLIENT_ID,
        client_secret: TWITCH_CLIENT_SECRET,
        grant_type: 'client_credentials'
      },
      timeout: 15000
    });
    twitchToken = resp.data.access_token;
    const expiresIn = resp.data.expires_in || 0;
    twitchTokenExpiresAt = Date.now() + expiresIn * 1000;
    return twitchToken;
  } catch (e) {
    throw new Error('Erreur obtention Twitch token: ' + (e.response?.data?.message || e.message));
  }
}

async function checkTwitch() {
  if (!TWITCH_CLIENT_ID || !TWITCH_CLIENT_SECRET || !TWITCH_USER_LOGINS) {
    console.log('Twitch non configuré (TWITCH_CLIENT_ID/TWITCH_CLIENT_SECRET/TWITCH_USER_LOGINS) — skip Twitch');
    return;
  }
  const logins = TWITCH_USER_LOGINS.split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
  if (logins.length === 0) return;

  try {
    const token = await getTwitchAppToken();
    // build query string with repeated user_login params
    const params = new URLSearchParams();
    for (const l of logins) params.append('user_login', l);
    const url = `https://api.twitch.tv/helix/streams?${params.toString()}`;

    const resp = await axios.get(url, {
      headers: {
        'Client-Id': TWITCH_CLIENT_ID,
        'Authorization': `Bearer ${token}`
      },
      timeout: 15000
    });

    const streams = resp.data && resp.data.data ? resp.data.data : [];
    // map login -> stream
    const liveByLogin = {};
    for (const s of streams) {
      if (s.user_login) liveByLogin[s.user_login.toLowerCase()] = s;
    }

    for (const login of logins) {
      const stream = liveByLogin[login];
      const prev = data.twitch[login] || { live: false, streamId: null };

      if (stream && !prev.live) {
        // went live
        const title = stream.title || 'Live';
        const game = stream.game_name || '';
        const viewers = stream.viewer_count || 0;
        const url = `https://twitch.tv/${login}`;
        const msg = `🔴 ${login} est en direct sur Twitch : **${title}** ${game ? `- ${game}` : ''}\n${url} — ${viewers} viewers`;
        const embed = { title, url, description: `Viewers: ${viewers}`, footer: { text: 'Twitch' } };
        await sendDiscord(msg, embed);
        data.twitch[login] = { live: true, streamId: stream.id };
        saveData();
      } else if (!stream && prev.live) {
        // went offline
        console.log(`${login} est offline maintenant.`);
        data.twitch[login] = { live: false, streamId: null };
        saveData();
      } else if (!data.twitch[login]) {
        // initialize state
        data.twitch[login] = prev;
      }
    }

  } catch (e) {
    console.error('Erreur checkTwitch:', e.response?.data || e.message);
  }
}

async function main() {
  console.log('Démarrage du bot YouTube/Twitch pinger (support multi-Twitch)');
  await checkYouTube();
  await checkTwitch();

  setInterval(() => {
    checkYouTube();
    checkTwitch();
  }, POLL_INTERVAL_MS);
}

main().catch(err => {
  console.error('Erreur fatale:', err);
  process.exit(1);
});
