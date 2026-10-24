"""
Spotify OAuth Token Kurulum Scripti
------------------------------------
Bu scripti bir kez kendi terminalinizde calistirin:
    .\\venv\\Scripts\\python auth_setup.py

Tarayici acilacak -> Spotify hesabinizla giris yapin -> Kabul Et
Token .spotify_cache dosyasina kaydolacak.
Bir daha calistirmaniza gerek kalmayacak.
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os

load_dotenv()

print("Spotify OAuth baslatiliyor...")
print("Tarayici acilacak, lutfen Spotify hesabinizla giris yapip izin verin.\n")

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri="http://127.0.0.1:9090",
    scope="playlist-read-private playlist-read-collaborative",
    open_browser=True,
    cache_path=".spotify_cache"
))

# Token'i test et
user = sp.current_user()
print(f"Basarili! Giris yapilan hesap: {user['display_name']} ({user['id']})")
print("Token '.spotify_cache' dosyasina kaydedildi.")
print("\nArtik 'python fetch_spotify_data.py' komutunu calistirabilirsiniz!")
