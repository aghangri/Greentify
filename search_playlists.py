import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())

# Search for "Top 50 - Global"
results = sp.search(q="Top 50 - Global", type="playlist", limit=5)
for item in results['playlists']['items']:
    print(item['name'], item['id'], item['owner']['id'])

print("---")

results = sp.search(q="Top 50 - Turkey", type="playlist", limit=5)
for item in results['playlists']['items']:
    print(item['name'], item['id'], item['owner']['id'])
