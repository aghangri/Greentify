import sqlite3

DB_NAME = "greenify.db"

def create_views():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Mevcut view'lari temizle (idempotent)
    for view in ['vw_top_artists', 'vw_track_metrics', 'vw_genre_distribution']:
        cursor.execute(f"DROP VIEW IF EXISTS {view}")

    # ------------------------------------------------------------------
    # 1. vw_top_artists
    #    Sanatcilarin adi, popÃ¼lerligi ve kac sarkida yer aldigini gosterir.
    #    (dim_artists'te followers kolonu olmadigi icin track_count kullaniyoruz)
    # ------------------------------------------------------------------
    cursor.execute('''
        CREATE VIEW vw_top_artists AS
        SELECT
            a.artist_id,
            a.name                              AS artist_name,
            a.popularity,
            COUNT(DISTINCT f.track_id)          AS track_count,
            COUNT(DISTINCT f.playlist_id)       AS playlist_count,
            GROUP_CONCAT(DISTINCT p.name)       AS playlists
        FROM dim_artists a
        JOIN fact_rankings f ON a.artist_id = f.artist_id
        JOIN dim_playlists p ON f.playlist_id = p.playlist_id
        GROUP BY a.artist_id, a.name, a.popularity
        ORDER BY track_count DESC, a.popularity DESC
    ''')
    print("âœ“ vw_top_artists olusturuldu")

    # ------------------------------------------------------------------
    # 2. vw_track_metrics
    #    Sarkilarin adi, sanatcisi, album bilgisi, sure (dk), explicit flag
    # ------------------------------------------------------------------
    cursor.execute('''
        CREATE VIEW vw_track_metrics AS
        SELECT
            t.track_id,
            t.name                                          AS track_name,
            a.name                                          AS artist_name,
            t.album_name,
            t.release_date,
            t.duration_ms,
            ROUND(t.duration_ms / 60000.0, 2)              AS duration_min,
            CASE WHEN t.explicit = 1 THEN 'Yes' ELSE 'No'  END AS explicit,
            f.position,
            p.name                                          AS playlist_name
        FROM dim_tracks t
        JOIN fact_rankings f  ON t.track_id  = f.track_id
        JOIN dim_artists  a   ON f.artist_id = a.artist_id
        JOIN dim_playlists p  ON f.playlist_id = p.playlist_id
        ORDER BY p.name, f.position
    ''')
    print("âœ“ vw_track_metrics olusturuldu")

    # ------------------------------------------------------------------
    # 3. vw_genre_distribution
    #    genres sutunu bos olabilir; o durumda track sayisina gore
    #    artist bazli bir dagitim saglar.
    #    Genres dolu oldugunda her turu ayri satira parcalar.
    # ------------------------------------------------------------------
    cursor.execute('''
        CREATE VIEW vw_genre_distribution AS
        SELECT
            CASE
                WHEN a.genres IS NULL OR TRIM(a.genres) = ''
                THEN 'Unknown'
                ELSE TRIM(genre.value)
            END                             AS genre,
            COUNT(DISTINCT a.artist_id)     AS artist_count,
            COUNT(DISTINCT f.track_id)      AS track_count
        FROM dim_artists a
        JOIN fact_rankings f ON a.artist_id = f.artist_id
        -- SQLite JSON each trick ile virgule gore genre parcalama
        LEFT JOIN (
            WITH RECURSIVE split(artist_id, value, rest) AS (
                SELECT artist_id,
                       CASE WHEN INSTR(genres, ',') > 0
                            THEN SUBSTR(genres, 1, INSTR(genres, ',') - 1)
                            ELSE genres END,
                       CASE WHEN INSTR(genres, ',') > 0
                            THEN SUBSTR(genres, INSTR(genres, ',') + 1)
                            ELSE '' END
                FROM dim_artists
                WHERE genres IS NOT NULL AND TRIM(genres) != ''
                UNION ALL
                SELECT artist_id,
                       CASE WHEN INSTR(rest, ',') > 0
                            THEN SUBSTR(rest, 1, INSTR(rest, ',') - 1)
                            ELSE rest END,
                       CASE WHEN INSTR(rest, ',') > 0
                            THEN SUBSTR(rest, INSTR(rest, ',') + 1)
                            ELSE '' END
                FROM split WHERE rest != ''
            )
            SELECT artist_id, TRIM(value) AS value FROM split WHERE TRIM(value) != ''
        ) genre ON genre.artist_id = a.artist_id
        GROUP BY genre
        ORDER BY track_count DESC, artist_count DESC
    ''')
    print("âœ“ vw_genre_distribution olusturuldu")

    conn.commit()

    # ------------------------------------------------------------------
    # Dogrulama: Her view'dan ornek veri goster
    # ------------------------------------------------------------------
    print("\n========== vw_top_artists (ilk 5) ==========")
    cursor.execute("SELECT artist_name, popularity, track_count, playlists FROM vw_top_artists LIMIT 5")
    for row in cursor.fetchall():
        print(f"  {str(row[0]).encode('ascii','replace').decode():<30} pop={row[1]}  tracks={row[2]}  lists={str(row[3]).encode('ascii','replace').decode()}")

    print("\n========== vw_track_metrics (ilk 5) ==========")
    cursor.execute("SELECT track_name, artist_name, duration_min, explicit, playlist_name FROM vw_track_metrics LIMIT 5")
    for row in cursor.fetchall():
        print(f"  {str(row[0]).encode('ascii','replace').decode():<35} | {str(row[1]).encode('ascii','replace').decode():<20} | {row[2]} dk | explicit={row[3]} | {str(row[4]).encode('ascii','replace').decode()}")

    print("\n========== vw_genre_distribution (ilk 5) ==========")
    cursor.execute("SELECT genre, artist_count, track_count FROM vw_genre_distribution LIMIT 5")
    for row in cursor.fetchall():
        print(f"  {str(row[0]).encode('ascii','replace').decode():<25} | sanatci={row[1]} | sarki={row[2]}")

    print("\n--- Tum view'lar basariyla olusturuldu ve dogrulandi ---")
    conn.close()

if __name__ == "__main__":
    create_views()

