import sqlite3
import os

DB_NAME = "greenify.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Create dim_artists table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dim_artists (
        artist_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        genres TEXT,
        popularity INTEGER
    )
    ''')

    # Create dim_tracks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dim_tracks (
        track_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        album_id TEXT,
        album_name TEXT,
        release_date TEXT,
        duration_ms INTEGER,
        explicit BOOLEAN
    )
    ''')

    # Create dim_playlists table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dim_playlists (
        playlist_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        owner_id TEXT,
        description TEXT
    )
    ''')

    # Create fact_rankings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fact_rankings (
        ranking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_id TEXT,
        track_id TEXT,
        artist_id TEXT,
        position INTEGER,
        added_at TEXT,
        FOREIGN KEY (playlist_id) REFERENCES dim_playlists(playlist_id),
        FOREIGN KEY (track_id) REFERENCES dim_tracks(track_id),
        FOREIGN KEY (artist_id) REFERENCES dim_artists(artist_id)
    )
    ''')

    conn.commit()
    conn.close()
    print(f"Database {DB_NAME} and tables created successfully.")

if __name__ == "__main__":
    init_db()
