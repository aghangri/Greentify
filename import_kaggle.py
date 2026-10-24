import sqlite3
import pandas as pd
import ast
import kagglehub
import os

DB_NAME   = "greenify.db"
DATASET_PATH = r"C:\Users\Agha Asgarov\.cache\kagglehub\datasets\rodolfofigueroa\spotify-12m-songs\versions\1\tracks_features.csv"
PLAYLIST_ID   = "kaggle-spotify-12m"
PLAYLIST_NAME = "Spotify 1.2M Songs (Kaggle)"
CHUNK_SIZE = 50000   # Bellek dostu: 50k'lik parcalar halinde yukle

def load_kaggle():
    conn   = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # ── 1. Eski verileri temizle ──────────────────────────────────────────
    print("Eski veriler temizleniyor...")
    cursor.execute("DELETE FROM fact_rankings")
    cursor.execute("DELETE FROM dim_tracks")
    cursor.execute("DELETE FROM dim_artists")
    cursor.execute("DELETE FROM dim_playlists")
    conn.commit()
    print("  Temizlendi.\n")

    # ── 2. Playlist ekle ──────────────────────────────────────────────────
    cursor.execute("""
        INSERT OR REPLACE INTO dim_playlists (playlist_id, name, owner_id, description)
        VALUES (?, ?, ?, ?)
    """, (PLAYLIST_ID, PLAYLIST_NAME, "kaggle", "Spotify 1.2M dataset by rodolfofigueroa"))
    conn.commit()

    # ── 3. CSV'yi chunk'lar halinde oku ve yukle ──────────────────────────
    stats = {"artists": 0, "tracks": 0, "rankings": 0}
    chunk_no = 0
    position = 1   # global sira

    print(f"Dataset yukleniyor: {DATASET_PATH}")
    print(f"Chunk boyutu: {CHUNK_SIZE:,} satir\n")

    for chunk in pd.read_csv(
        DATASET_PATH,
        chunksize=CHUNK_SIZE,
        encoding="utf-8",
        on_bad_lines="skip"
    ):
        chunk_no += 1
        print(f"Chunk {chunk_no} isleniyor ({len(chunk):,} satir)...")

        artist_rows  = []
        track_rows   = []
        ranking_rows = []

        for _, row in chunk.iterrows():
            track_id   = str(row["id"]) if pd.notna(row["id"]) else None
            track_name = str(row["name"]) if pd.notna(row["name"]) else "Unknown"
            if not track_id:
                continue

            # artist_ids listesini parse et: "['id1','id2']" -> ['id1','id2']
            try:
                artist_ids_raw   = ast.literal_eval(str(row["artist_ids"]))
                artist_names_raw = ast.literal_eval(str(row["artists"]))
            except Exception:
                artist_ids_raw   = [str(row["artist_ids"])]
                artist_names_raw = [str(row["artists"])]

            primary_artist_id = str(artist_ids_raw[0]) if artist_ids_raw else "unknown"

            # Sanatcilar
            for a_id, a_name in zip(artist_ids_raw, artist_names_raw):
                artist_rows.append((
                    str(a_id),
                    str(a_name),
                    "",   # genres (API'den gelmediginden bos)
                    0
                ))
                stats["artists"] += 1

            # Sarki
            album_id    = str(row["album_id"])  if pd.notna(row.get("album_id"))  else ""
            album_name  = str(row["album"])     if pd.notna(row.get("album"))     else ""
            release_date= str(row["release_date"]) if pd.notna(row.get("release_date")) else ""
            duration_ms = int(row["duration_ms"]) if pd.notna(row.get("duration_ms")) else 0
            explicit    = 1 if str(row.get("explicit","False")).lower() == "true" else 0

            track_rows.append((
                track_id, track_name,
                album_id, album_name,
                release_date, duration_ms, explicit
            ))
            stats["tracks"] += 1

            # Ranking
            ranking_rows.append((
                PLAYLIST_ID, track_id, primary_artist_id,
                position, str(row.get("year", ""))
            ))
            stats["rankings"] += 1
            position += 1

        # Toplu insert (cok daha hizli)
        cursor.executemany("""
            INSERT OR IGNORE INTO dim_artists (artist_id, name, genres, popularity)
            VALUES (?, ?, ?, ?)
        """, artist_rows)

        cursor.executemany("""
            INSERT OR REPLACE INTO dim_tracks
                (track_id, name, album_id, album_name, release_date, duration_ms, explicit)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, track_rows)

        cursor.executemany("""
            INSERT INTO fact_rankings (playlist_id, track_id, artist_id, position, added_at)
            VALUES (?, ?, ?, ?, ?)
        """, ranking_rows)

        conn.commit()
        print(f"  Chunk {chunk_no} tamamlandi. Toplam sarki: {stats['tracks']:,}")

    # ── 4. Sonuc raporu ───────────────────────────────────────────────────
    print("\n========== Import Tamamlandi ==========")
    print(f"Eklenen Sanatci  : {stats['artists']:,}")
    print(f"Eklenen Sarki    : {stats['tracks']:,}")
    print(f"Eklenen Siralama : {stats['rankings']:,}")

    print("\n--- Veritabanindaki Toplam Kayit Sayilari ---")
    for table in ["dim_playlists", "dim_artists", "dim_tracks", "fact_rankings"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table}: {cursor.fetchone()[0]:,} kayit")

    print("\n--- Ornek Sarkilar ---")
    cursor.execute("""
        SELECT t.name, a.name, t.release_date
        FROM dim_tracks t
        JOIN fact_rankings f ON t.track_id = f.track_id
        JOIN dim_artists a   ON f.artist_id = a.artist_id
        ORDER BY RANDOM()
        LIMIT 5
    """)
    for row in cursor.fetchall():
        track  = str(row[0]).encode("ascii","replace").decode()
        artist = str(row[1]).encode("ascii","replace").decode()
        print(f"  {track:<40} - {artist:<25} ({row[2]})")

    conn.close()

if __name__ == "__main__":
    load_kaggle()
