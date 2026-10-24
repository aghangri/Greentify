import spotipy, sqlite3, os
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

DB_NAME = "greenify.db"
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Veritabanindaki tum artist ID'lerini al
cursor.execute("SELECT artist_id, name FROM dim_artists")
artists = cursor.fetchall()
artist_ids = [a[0] for a in artists]

print(f"Veritabaninda {len(artist_ids)} sanatci bulundu. Genre bilgileri cekiliyor...")

updated = 0
failed = 0

# Spotify'a max 50'lik batch'ler halinde sor
for i in range(0, len(artist_ids), 50):
    batch = artist_ids[i:i+50]
    try:
        resp = sp.artists(batch)
        for a_data in resp['artists']:
            if not a_data:
                continue
            genres    = ', '.join(a_data.get('genres', []))
            popularity = a_data.get('popularity', 0)
            a_id      = a_data['id']
            cursor.execute('''
                UPDATE dim_artists
                SET genres = ?, popularity = ?
                WHERE artist_id = ?
            ''', (genres, popularity, a_id))
            updated += 1
    except Exception as e:
        print(f"Batch {i//50 + 1} hatasi: {str(e)[:80]}")
        failed += len(batch)

conn.commit()

print(f"\nGuncellenen sanatci : {updated}")
print(f"Hata alan           : {failed}")

# Sonucu goster
print("\n--- Genre'si dolu sanatcilar (ilk 10) ---")
cursor.execute("""
    SELECT name, genres, popularity
    FROM dim_artists
    WHERE genres != '' AND genres IS NOT NULL
    ORDER BY popularity DESC
    LIMIT 10
""")
for row in cursor.fetchall():
    name    = str(row[0]).encode('ascii', 'replace').decode()
    genres  = str(row[1]).encode('ascii', 'replace').decode()
    print(f"  {name:<25} | {genres[:50]:<50} | pop={row[2]}")

print("\n--- Genre dagilimi ozeti ---")
cursor.execute("""
    SELECT
        CASE WHEN genres = '' OR genres IS NULL THEN 'Unknown' ELSE 'Dolu' END AS durum,
        COUNT(*) AS sanatci_sayisi
    FROM dim_artists
    GROUP BY durum
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} sanatci")

conn.close()
