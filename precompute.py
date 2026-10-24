"""
precompute.py
Bir kere calistir, dashboard aninda calissin.
Ozet tablolari hesaplar ve greenify.db'ye yazar.
"""
import sqlite3

DB_NAME = "greenify.db"

def precompute():
    conn = sqlite3.connect(DB_NAME, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-64000")   # 64 MB cache
    conn.execute("PRAGMA synchronous=NORMAL")
    c = conn.cursor()

    # ── 1. Top Artists ────────────────────────────────────────────────────
    print("[1/5] summary_top_artists hesaplaniyor...")
    c.execute("DROP TABLE IF EXISTS summary_top_artists")
    c.execute("""
        CREATE TABLE summary_top_artists AS
        SELECT
            a.artist_id,
            a.name        AS artist,
            COUNT(DISTINCT f.track_id) AS track_count
        FROM dim_artists a
        JOIN fact_rankings f ON a.artist_id = f.artist_id
        GROUP BY a.artist_id, a.name
        ORDER BY track_count DESC
    """)
    conn.commit()
    print("   OK")

    # ── 2. Yearly Track Count ─────────────────────────────────────────────
    print("[2/5] summary_yearly hesaplaniyor...")
    c.execute("DROP TABLE IF EXISTS summary_yearly")
    c.execute("""
        CREATE TABLE summary_yearly AS
        SELECT
            SUBSTR(release_date, 1, 4) AS year,
            COUNT(*) AS track_count
        FROM dim_tracks
        WHERE release_date IS NOT NULL
          AND LENGTH(release_date) >= 4
          AND SUBSTR(release_date,1,4) BETWEEN '1900' AND '2026'
        GROUP BY year
        ORDER BY year
    """)
    conn.commit()
    print("   OK")

    # ── 3. Explicit Distribution ──────────────────────────────────────────
    print("[3/5] summary_explicit hesaplaniyor...")
    c.execute("DROP TABLE IF EXISTS summary_explicit")
    c.execute("""
        CREATE TABLE summary_explicit AS
        SELECT
            CASE WHEN explicit=1 THEN 'Explicit' ELSE 'Clean' END AS type,
            COUNT(*) AS count
        FROM dim_tracks
        GROUP BY explicit
    """)
    conn.commit()
    print("   OK")

    # ── 4. Duration Sample (10k) ─────────────────────────────────────────
    print("[4/5] summary_duration_sample hesaplaniyor...")
    c.execute("DROP TABLE IF EXISTS summary_duration_sample")
    c.execute("""
        CREATE TABLE summary_duration_sample AS
        SELECT ROUND(duration_ms / 60000.0, 1) AS duration_min
        FROM dim_tracks
        WHERE duration_ms > 0 AND duration_ms < 900000
        ORDER BY RANDOM()
        LIMIT 20000
    """)
    conn.commit()
    print("   OK")

    # ── 5. Global Metrics ─────────────────────────────────────────────────
    print("[5/5] summary_metrics hesaplaniyor...")
    c.execute("DROP TABLE IF EXISTS summary_metrics")
    c.execute("""
        CREATE TABLE summary_metrics AS
        SELECT
            (SELECT COUNT(*) FROM dim_tracks)  AS total_tracks,
            (SELECT COUNT(*) FROM dim_artists) AS total_artists,
            (SELECT COUNT(*) FROM dim_playlists) AS total_playlists,
            (SELECT ROUND(AVG(duration_ms)/60000.0,2) FROM dim_tracks WHERE duration_ms > 0) AS avg_duration_min,
            (SELECT COUNT(*) FROM dim_tracks WHERE explicit=1) AS explicit_count
    """)
    conn.commit()
    print("   OK")

    # Indexler
    print("\nSummary indexleri olusturuluyor...")
    c.execute("CREATE INDEX IF NOT EXISTS idx_top_artists_count ON summary_top_artists(track_count DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_yearly_year ON summary_yearly(year)")
    conn.commit()

    # Rapor
    print("\n===== Precompute Tamamlandi =====")
    for tbl in ["summary_top_artists","summary_yearly","summary_explicit","summary_duration_sample","summary_metrics"]:
        c.execute(f"SELECT COUNT(*) FROM {tbl}")
        print(f"  {tbl}: {c.fetchone()[0]:,} kayit")

    conn.close()

if __name__ == "__main__":
    precompute()
