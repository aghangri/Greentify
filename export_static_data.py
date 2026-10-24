import sqlite3
import json
import os

print("Exporting data from greenify.db for GitHub Pages static build...")

conn = sqlite3.connect('greenify.db')
c = conn.cursor()

# 1. metrics
c.execute('SELECT * FROM summary_metrics')
metrics = dict(sqlite3.Row(c, c.fetchone()))

# 2. explicit
c.execute('SELECT * FROM summary_explicit')
cols = [col[0] for col in c.description]
explicit = [dict(zip(cols, r)) for r in c.fetchall()]

# 3. yearly
c.execute('SELECT year, track_count FROM summary_yearly ORDER BY year')
yearly = [dict(year=r[0], track_count=r[1]) for r in c.fetchall()]

# 4. duration sample
c.execute('SELECT duration_min FROM summary_duration_sample LIMIT 5000')
duration = [round(r[0], 2) for r in c.fetchall()]

# 5. Top 500 artists
c.execute('''
    SELECT a.name AS artist, s.track_count, a.genres
    FROM summary_top_artists s
    JOIN dim_artists a ON s.artist_id = a.artist_id
    ORDER BY s.track_count DESC
    LIMIT 500
''')
cols = [col[0] for col in c.description]
top_artists = [dict(zip(cols, r)) for r in c.fetchall()]

# 6. Artists yearly for top 200 artists
c.execute('''
    SELECT a.name AS artist, CAST(s.year AS INTEGER) AS year, s.track_count
    FROM summary_artist_yearly s
    JOIN dim_artists a ON s.artist_id = a.artist_id
    JOIN (
        SELECT artist_id FROM summary_top_artists ORDER BY track_count DESC LIMIT 200
    ) top ON s.artist_id = top.artist_id
''')
cols = [col[0] for col in c.description]
artist_yearly = [dict(zip(cols, r)) for r in c.fetchall()]

# 7. 6,000 tracks (popular + representative)
c.execute('''
    SELECT t.name AS track, a.name AS artist,
           t.album_name AS album,
           CAST(SUBSTR(t.release_date,1,4) AS INTEGER) AS year,
           ROUND(t.duration_ms/60000.0,2) AS duration_min,
           CASE WHEN t.explicit=1 THEN 1 ELSE 0 END AS explicit,
           a.genres
    FROM dim_tracks t
    JOIN fact_rankings f ON t.track_id = f.track_id
    JOIN dim_artists a ON f.artist_id = a.artist_id
    ORDER BY a.popularity DESC
    LIMIT 6000
''')
cols = [col[0] for col in c.description]
tracks = [dict(zip(cols, r)) for r in c.fetchall()]

os.makedirs('data', exist_ok=True)
output_path = os.path.join('data', 'dataset.json')

bundle = {
    'metrics': metrics,
    'explicit': explicit,
    'yearly': yearly,
    'duration': duration,
    'top_artists': top_artists,
    'artist_yearly': artist_yearly,
    'tracks': tracks
}

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(bundle, f, separators=(',', ':'), ensure_ascii=False)

file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
print(f"Export complete: {output_path} ({file_size_mb:.2f} MB)")
