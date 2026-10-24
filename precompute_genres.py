import sqlite3
from collections import defaultdict

def precompute_genres():
    print("Precomputing genres...")
    conn = sqlite3.connect('greenify.db')
    c = conn.cursor()

    c.execute("""
        SELECT a.artist_id, a.genres, COUNT(f.track_id)
        FROM dim_artists a
        JOIN fact_rankings f ON a.artist_id = f.artist_id
        WHERE a.genres != '' AND a.genres != 'unknown' AND a.genres IS NOT NULL
        GROUP BY a.artist_id
    """)

    genre_stats = defaultdict(lambda: {"artists": 0, "tracks": 0})
    batch = []

    for artist_id, genres_str, track_count in c.fetchall():
        genres = [g.strip().lower() for g in genres_str.split(",")]
        for g in genres:
            if not g: continue
            genre_stats[g]["artists"] += 1
            genre_stats[g]["tracks"] += track_count
            batch.append((artist_id, g))

    print("Creating dim_artist_genres...")
    c.execute("DROP TABLE IF EXISTS dim_artist_genres")
    c.execute("CREATE TABLE dim_artist_genres (artist_id TEXT, genre TEXT)")
    c.executemany("INSERT INTO dim_artist_genres (artist_id, genre) VALUES (?, ?)", batch)
    c.execute("CREATE INDEX IF NOT EXISTS idx_dag_artist ON dim_artist_genres(artist_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_dag_genre ON dim_artist_genres(genre)")

    print("Creating summary_genres...")
    c.execute("DROP TABLE IF EXISTS summary_genres")
    c.execute("CREATE TABLE summary_genres (genre TEXT, artist_count INTEGER, track_count INTEGER)")
    
    genre_rows = [(g, s["artists"], s["tracks"]) for g, s in genre_stats.items()]
    c.executemany("INSERT INTO summary_genres (genre, artist_count, track_count) VALUES (?, ?, ?)", genre_rows)
    c.execute("CREATE INDEX IF NOT EXISTS idx_sg_tracks ON summary_genres(track_count DESC)")

    conn.commit()
    conn.close()
    print("Done! Found", len(genre_rows), "unique genres.")

if __name__ == "__main__":
    precompute_genres()
