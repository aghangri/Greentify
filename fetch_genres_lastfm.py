"""
fetch_genres_lastfm.py
----------------------
Last.fm API kullanarak dim_artists tablosundaki sanatcilara
genre (tag) bilgisi ceker ve veritabanina yazar.

- 140K sanatci icin ~8 saat surebilir (rate limit: 5 req/sn)
- Kaldigi yerden devam eder (checkpoint sistemi var)
- Istediginizde Ctrl+C ile durdurun, tekrar baslatinca kaldiginiz yerden devam eder
"""

import sqlite3
import requests
import time
import os
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv("LASTFM_API_KEY")
BASE_URL = "http://ws.audioscrobbler.com/2.0/"
DB_NAME  = "greenify.db"
CHECKPOINT_FILE = "lastfm_checkpoint.json"
BATCH_SIZE = 200      # Her BATCH_SIZE istekte bir DB'ye yaz
RATE_LIMIT = 0.22     # 4.5 req/sn (limit: 5/sn, biraz pay birak)

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"processed": 0, "updated": 0, "not_found": 0}

def save_checkpoint(data):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f)

def get_artist_genre(artist_name):
    """Last.fm'den sanatcinin en populer tag'lerini cek."""
    try:
        resp = requests.get(BASE_URL, params={
            "method":  "artist.getTopTags",
            "artist":  artist_name,
            "api_key": API_KEY,
            "format":  "json"
        }, timeout=5)
        data = resp.json()
        tags = data.get("toptags", {}).get("tag", [])
        if not tags:
            return ""
        # En populer 3 tag'i al (count >= 10 olanlar)
        genres = [t["name"].lower() for t in tags[:5] if int(t.get("count", 0)) >= 10]
        return ", ".join(genres[:3])
    except Exception:
        return None   # None = hata, "" = bulunamadi

def fetch_genres():
    conn   = sqlite3.connect(DB_NAME, timeout=30)
    cursor = conn.cursor()

    # Genres bos olan sanatcilari al, en cok sarki sahibi once
    cursor.execute("""
        SELECT a.artist_id, a.name
        FROM dim_artists a
        WHERE a.genres = '' OR a.genres IS NULL
        ORDER BY (
            SELECT COUNT(*) FROM fact_rankings f WHERE f.artist_id = a.artist_id
        ) DESC
    """)
    artists = cursor.fetchall()
    total   = len(artists)

    chk = load_checkpoint()
    start   = chk["processed"]
    updated = chk["updated"]
    not_found = chk["not_found"]

    print(f"Toplam genre'siz sanatci : {total:,}")
    print(f"Kaldigi yerden devam     : {start:,}. sanatcidan")
    print(f"Rate limit               : {1/RATE_LIMIT:.1f} req/sn")
    print(f"Tahmini sure             : {(total-start)*RATE_LIMIT/3600:.1f} saat")
    print("Ctrl+C ile durdurabilirsiniz. Tekrar baslatinca kaldiginiz yerden devam eder.")
    print("-" * 60)

    batch_updates = []

    try:
        for i, (a_id, a_name) in enumerate(artists[start:], start=start):
            genre = get_artist_genre(a_name)

            if genre is None:
                # API hatasi — atla
                pass
            elif genre == "":
                not_found += 1
                # Bulunamadi ama bos yaz (bir daha sormasin)
                batch_updates.append(("unknown", a_id))
            else:
                updated += 1
                batch_updates.append((genre, a_id))

            # Her BATCH_SIZE'da bir DB'ye yaz
            if len(batch_updates) >= BATCH_SIZE:
                cursor.executemany(
                    "UPDATE dim_artists SET genres=? WHERE artist_id=?",
                    batch_updates
                )
                conn.commit()
                batch_updates.clear()

            # Checkpoint kaydet
            if (i + 1) % 500 == 0:
                save_checkpoint({"processed": i+1, "updated": updated, "not_found": not_found})
                pct = (i+1) / total * 100
                print(f"  [{pct:5.1f}%] {i+1:,}/{total:,} | genre bulunan: {updated:,} | bulunamayan: {not_found:,}")

            time.sleep(RATE_LIMIT)

    except KeyboardInterrupt:
        print("\n\nDurduruldu! Checkpoint kaydedildi.")
        if batch_updates:
            cursor.executemany(
                "UPDATE dim_artists SET genres=? WHERE artist_id=?",
                batch_updates
            )
            conn.commit()
        save_checkpoint({"processed": i, "updated": updated, "not_found": not_found})
        conn.close()
        return

    # Kalan batch
    if batch_updates:
        cursor.executemany(
            "UPDATE dim_artists SET genres=? WHERE artist_id=?",
            batch_updates
        )
        conn.commit()

    save_checkpoint({"processed": total, "updated": updated, "not_found": not_found})

    print("\n===== Tamamlandi =====")
    print(f"Genre bulunan  : {updated:,}")
    print(f"Bulunamayan    : {not_found:,}")

    # Ornek
    print("\n--- Ornek Genre'ler ---")
    cursor.execute("""
        SELECT name, genres FROM dim_artists
        WHERE genres != '' AND genres != 'unknown'
        ORDER BY RANDOM() LIMIT 8
    """)
    for row in cursor.fetchall():
        name = str(row[0]).encode("ascii","replace").decode()
        print(f"  {name:<30} -> {row[1]}")

    conn.close()

    # Precompute'u yenile
    print("\nSummary tablolar yenileniyor...")
    os.system(f"python precompute.py")

if __name__ == "__main__":
    # Once API'yi test et
    test = get_artist_genre("Radiohead")
    if test is None:
        print("API hatasi! API key kontrol edin.")
    else:
        print(f"API testi OK! Radiohead -> '{test}'")
        print()
        fetch_genres()

