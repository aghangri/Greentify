import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import os

# .env dosyasındaki değişkenleri yükle
load_dotenv()

# Spotify API - Authorization Code Flow
auth_manager = SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri="http://127.0.0.1:9090",
    scope="playlist-read-private playlist-read-collaborative",
    open_browser=True,
    cache_path=".spotify_cache"
)
sp = spotipy.Spotify(auth_manager=auth_manager)

DB_NAME = "greenify.db"

# Kullanicinin kendi Spotify playlistleri + resmi Spotify chart listeleri
PLAYLISTS = {
    'Chill Anime Vibes': '4lqibK1dtxdkoW77RbzTMg',
    'Nostalgia': '2iOWICoWBnngvB1U7gfmFO',
    'Top 50 - Global': '37i9dQZEVXbMDoHDwVN2tF',
    'Top 50 - Turkey': '37i9dQZEVXbIVYVov4d9S4'
}

def get_db_connection():
    return sqlite3.connect(DB_NAME)

def fetch_and_store_data():
    conn = get_db_connection()
    cursor = conn.cursor()

    snapshot_date = datetime.now().strftime('%Y-%m-%d')
    stats = {'artists': 0, 'tracks': 0, 'playlists': 0, 'rankings': 0}

    for pl_name, pl_id in PLAYLISTS.items():
        print(f"Cekiliyor: {pl_name}...")
        try:
            pl_data = sp.playlist(pl_id)
            tracks_data = sp.playlist_tracks(pl_id)
        except Exception as e:
            print(f"Hata ({pl_name}): {e}")
            continue

        owner_id = pl_data['owner']['id'] if pl_data.get('owner') else 'unknown'
        description = pl_data.get('description', '') or ''

        # UPSERT: Playlist
        cursor.execute('''
            INSERT INTO dim_playlists (playlist_id, name, owner_id, description)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(playlist_id) DO UPDATE SET
                name=excluded.name,
                owner_id=excluded.owner_id,
                description=excluded.description
        ''', (pl_id, pl_name, owner_id, description))
        stats['playlists'] += 1

        items = tracks_data.get('items', []) if tracks_data else []

        for idx, item in enumerate(items):
            # Spotify API: newer responses use 'item' key, older use 'track'
            track = item.get('track') or item.get('item')

            # Skip non-track entries (episodes, local files, etc.)
            if not track or not track.get('id') or track.get('type') != 'track':
                continue

            track_id    = track['id']
            track_name  = track.get('name', 'Unknown')
            album       = track.get('album') or {}
            album_id    = album.get('id')
            album_name  = album.get('name')
            release_date = album.get('release_date')
            duration_ms = track.get('duration_ms', 0)
            explicit    = bool(track.get('explicit', False))
            position    = idx + 1

            # UPSERT: Track
            cursor.execute('''
                INSERT INTO dim_tracks
                    (track_id, name, album_id, album_name, release_date, duration_ms, explicit)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(track_id) DO UPDATE SET
                    name=excluded.name,
                    album_id=excluded.album_id,
                    album_name=excluded.album_name,
                    release_date=excluded.release_date,
                    duration_ms=excluded.duration_ms,
                    explicit=excluded.explicit
            ''', (track_id, track_name, album_id, album_name,
                  release_date, duration_ms, explicit))
            stats['tracks'] += 1

            # UPSERT artists directly from track data (no extra API call needed)
            artists = track.get('artists') or []
            primary_artist_id = None
            for i, artist in enumerate(artists):
                a_id   = artist.get('id')
                a_name = artist.get('name', 'Unknown')
                if not a_id:
                    continue
                if i == 0:
                    primary_artist_id = a_id
                cursor.execute('''
                    INSERT INTO dim_artists (artist_id, name, genres, popularity)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(artist_id) DO UPDATE SET
                        name=excluded.name
                ''', (a_id, a_name, '', 0))
                stats['artists'] += 1

            # INSERT: Ranking
            cursor.execute('''
                INSERT INTO fact_rankings
                    (playlist_id, track_id, artist_id, position, added_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (pl_id, track_id, primary_artist_id, position, snapshot_date))
            stats['rankings'] += 1

    conn.commit()

    print("\n--- ETL Islemi Basariyla Tamamlandi ---")
    print(f"Islenen Playlist : {stats['playlists']}")
    print(f"Islenen Sanatci  : {stats['artists']}")
    print(f"Islenen Sarki    : {stats['tracks']}")
    print(f"Eklenen Siralama : {stats['rankings']}")

    print("\n--- Veritabanindaki Toplam Kayit Sayilari ---")
    for table in ['dim_playlists', 'dim_artists', 'dim_tracks', 'fact_rankings']:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table}: {cursor.fetchone()[0]} kayit")

    conn.close()

if __name__ == "__main__":
    fetch_and_store_data()
