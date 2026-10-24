import spotipy, os, json
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv('SPOTIPY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
    redirect_uri='http://127.0.0.1:9090',
    scope='playlist-read-private playlist-read-collaborative',
    cache_path='.spotify_cache'
))

print("=== Hesabinizdaki Playlistler ===")
r = sp.current_user_playlists(limit=20)
for p in r['items']:
    total = p.get('tracks', {}).get('total', '?') if p.get('tracks') else '?'
    print(f"Ad: {p['name'].encode('ascii','replace').decode()} | ID: {p['id']} | Sarki: {total}")

print("\n=== Erisilen Sarki Testi (ilk playlist) ===")
if r['items']:
    pl_id = r['items'][0]['id']
    try:
        tracks = sp.playlist_tracks(pl_id, limit=3)
        print(f"Basarili! {len(tracks['items'])} sarki cekildi.")
    except Exception as e:
        print(f"Hata: {e}")
