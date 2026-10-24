import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME   = "greenify.db"
CSV_FILE  = "regional-global-weekly-2026-09-24.csv"
PLAYLIST_ID   = "spotify-charts-global-weekly"
PLAYLIST_NAME = "Top 50 - Global (Charts)"
SNAPSHOT_DATE = "2026-09-24"

def load_csv():
    conn   = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # ── 1. Eski verileri temizle ────────────────────────────────────────────
    print("Eski veriler siliniyor...")
    cursor.execute("DELETE FROM fact_rankings")
    cursor.execute("DELETE FROM dim_tracks")
    cursor.execute("DELETE FROM dim_artists")
    cursor.execute("DELETE FROM dim_playlists")
    print("  Tum tablolar temizlendi.")

    # ── 2. CSV'yi oku ───────────────────────────────────────────────────────
    df = pd.read_csv(CSV_FILE, encoding="utf-8", on_bad_lines="skip")
    print(f"\nCSV yuklendi: {len(df)} satir, kolonlar: {df.columns.tolist()}")

    # track_id'yi URI'dan cikart  (spotify:track:XXXXXX -> XXXXXX)
    df["track_id"] = df["uri"].str.split(":").str[-1]

    # ── 3. Playlist ekle ────────────────────────────────────────────────────
    cursor.execute("""
        INSERT OR REPLACE INTO dim_playlists (playlist_id, name, owner_id, description)
        VALUES (?, ?, ?, ?)
    """, (PLAYLIST_ID, PLAYLIST_NAME, "spotify", "Spotify Global Weekly Top 50 - " + SNAPSHOT_DATE))
    print(f"\nPlaylist eklendi: {PLAYLIST_NAME}")

    # ── 4. Sanatci & Sarki & Ranking ekle ──────────────────────────────────
    stats = {"artists": 0, "tracks": 0, "rankings": 0}

    for _, row in df.iterrows():
        track_id   = row["track_id"]
        track_name = row["track_name"]
        position   = int(row["rank"])
        streams    = int(str(row["streams"]).replace(",", "")) if pd.notna(row["streams"]) else 0

        # artist_names virgülle ayrılmış olabilir; ilkini primary say
        raw_artists = str(row["artist_names"]) if pd.notna(row["artist_names"]) else "Unknown"
        artist_list = [a.strip() for a in raw_artists.split(",")]
        primary_artist_name = artist_list[0]

        # artist_id olarak isimden deterministik ID üret (API ID yok)
        primary_artist_id = "csv_" + primary_artist_name.lower().replace(" ", "_")[:40]

        # UPSERT: her sanatci
        for a_name in artist_list:
            a_id = "csv_" + a_name.lower().replace(" ", "_")[:40]
            cursor.execute("""
                INSERT OR IGNORE INTO dim_artists (artist_id, name, genres, popularity)
                VALUES (?, ?, ?, ?)
            """, (a_id, a_name, "", 0))
            stats["artists"] += 1

        # UPSERT: sarki
        cursor.execute("""
            INSERT OR REPLACE INTO dim_tracks
                (track_id, name, album_id, album_name, release_date, duration_ms, explicit)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (track_id, track_name,
              row.get("source", ""),    # album_id olarak source kullan
              row.get("source", ""),    # album_name
              SNAPSHOT_DATE, 0, 0))
        stats["tracks"] += 1

        # INSERT: ranking (streams'i added_at yerine not olarak kullanmak icin
        #  fact_rankings sema degismeden kalsin, streams degerini position ile birlikte yaz)
        cursor.execute("""
            INSERT INTO fact_rankings (playlist_id, track_id, artist_id, position, added_at)
            VALUES (?, ?, ?, ?, ?)
        """, (PLAYLIST_ID, track_id, primary_artist_id, position, SNAPSHOT_DATE))
        stats["rankings"] += 1

    conn.commit()

    # ── 5. Sonuc raporu ─────────────────────────────────────────────────────
    print("\n--- Import Tamamlandi ---")
    print(f"Eklenen Sanatci  : {stats['artists']}")
    print(f"Eklenen Sarki    : {stats['tracks']}")
    print(f"Eklenen Siralama : {stats['rankings']}")

    print("\n--- Veritabanindaki Toplam Kayit Sayilari ---")
    for table in ["dim_playlists", "dim_artists", "dim_tracks", "fact_rankings"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table}: {cursor.fetchone()[0]} kayit")

    print("\n--- Top 10 Sarki ---")
    cursor.execute("""
        SELECT f.position, t.name, a.name
        FROM fact_rankings f
        JOIN dim_tracks t  ON f.track_id  = t.track_id
        JOIN dim_artists a ON f.artist_id = a.artist_id
        ORDER BY f.position
        LIMIT 10
    """)
    for row in cursor.fetchall():
        name   = str(row[1]).encode("ascii","replace").decode()
        artist = str(row[2]).encode("ascii","replace").decode()
        print(f"  #{row[0]:<3} {name:<35} - {artist}")

    conn.close()

if __name__ == "__main__":
    load_csv()
