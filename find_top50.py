import spotipy, os
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
load_dotenv()

PLAYLIST_ID = '37i9dQZEVXbMDoHDwVN2tF'

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv('SPOTIPY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
    redirect_uri='http://127.0.0.1:9090',
    scope='playlist-read-private playlist-read-collaborative user-follow-modify user-library-read',
    open_browser=True,
    cache_path='.spotify_cache'
))

# Önce follow et
print("Playlist takip ediliyor...")
try:
    sp.current_user_follow_playlist(PLAYLIST_ID)
    print("Takip edildi!")
except Exception as e:
    print(f"Follow hatasi: {e}")

# Sonra tracks cek
print("Sarkilar cekiliyor...")
try:
    r = sp.playlist_tracks(PLAYLIST_ID, limit=5)
    total = r.get('total', 0)
    items = [i for i in r.get('items', []) if i and (i.get('track') or i.get('item'))]
    print(f"Basarili! Toplam: {total} sarki, Cekilen: {len(items)}")
    for i in items:
        t = i.get('track') or i.get('item')
        if t:
            print(f"  - {t.get('name','?').encode('ascii','replace').decode()}")
except Exception as e:
    print(f"Track cekme hatasi: {e}")
