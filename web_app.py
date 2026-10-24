from flask import Flask, jsonify, request, render_template, make_response
import sqlite3

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True   # always read templates from disk
DB = "greenify.db"

def db_query(sql, params=()):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(sql, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

@app.route('/')
def index():
    resp = make_response(render_template('index.html'))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    return resp

@app.route('/api/metrics')
def api_metrics():
    r = db_query("SELECT * FROM summary_metrics")
    return jsonify(r[0] if r else {})

@app.route('/api/top-artists')
def api_top_artists():
    n = request.args.get('n', 15, type=int)
    min_year = request.args.get('min_year', '').strip()
    max_year = request.args.get('max_year', '').strip()

    # Fast path: all-time
    is_filtered = (min_year and min_year > '1960') or (max_year and max_year < '2024')
    if not is_filtered:
        return jsonify(db_query(
            "SELECT artist, track_count FROM summary_top_artists ORDER BY track_count DESC LIMIT ?", (n,)
        ))

    where = []
    params = []
    if min_year:
        where.append("year >= ?")
        params.append(min_year)
    if max_year:
        where.append("year <= ?")
        params.append(max_year)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(n)

    # Fast subquery aggregate on covering index, then join artist name
    return jsonify(db_query(f"""
        SELECT a.name AS artist, sub.track_count
        FROM (
            SELECT artist_id, CAST(SUM(track_count) AS INTEGER) AS track_count
            FROM summary_artist_yearly
            {where_sql}
            GROUP BY artist_id
            ORDER BY track_count DESC LIMIT ?
        ) sub
        JOIN dim_artists a ON sub.artist_id = a.artist_id
        ORDER BY sub.track_count DESC
    """, tuple(params)))

@app.route('/api/yearly')
def api_yearly():
    min_y = request.args.get('min', '1960').strip()
    max_y = request.args.get('max', '2026').strip()
    return jsonify(db_query(
        "SELECT year, track_count FROM summary_yearly WHERE year >= ? AND year <= ? ORDER BY year",
        (min_y, max_y)
    ))

@app.route('/api/explicit')
def api_explicit():
    return jsonify(db_query("SELECT * FROM summary_explicit"))

@app.route('/api/duration')
def api_duration():
    return jsonify(db_query("SELECT duration_min FROM summary_duration_sample LIMIT 5000"))

@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip()
    limit = request.args.get('limit', 50, type=int)
    min_year = request.args.get('min_year', '').strip()
    max_year = request.args.get('max_year', '').strip()

    if not q:
        return jsonify([])

    # Use FTS5 index for instant sub-millisecond search
    clean_q = ''.join(ch for ch in q if ch.isalnum() or ch.isspace())
    terms = [f'"{w}"*' for w in clean_q.split() if w]
    if not terms:
        return jsonify([])
    match_expr = ' '.join(terms)

    where = ["fts_tracks MATCH ?"]
    params = [match_expr]
    if min_year:
        where.append("year >= ?")
        params.append(min_year)
    if max_year:
        where.append("year <= ?")
        params.append(max_year)

    where_sql = "WHERE " + " AND ".join(where)
    params.append(limit)

    try:
        return jsonify(db_query(f"""
            SELECT track, artist, album, year, duration_min, explicit, genres
            FROM fts_tracks
            {where_sql}
            LIMIT ?
        """, tuple(params)))
    except Exception:
        # Fallback to standard LIKE if FTS fails
        fallback_params = [f"%{q}%", f"%{q}%", limit]
        return jsonify(db_query("""
            SELECT t.name AS track, a.name AS artist, t.album_name AS album,
                   SUBSTR(t.release_date,1,4) AS year,
                   ROUND(t.duration_ms/60000.0,2) AS duration_min,
                   CASE WHEN t.explicit=1 THEN 1 ELSE 0 END AS explicit,
                   a.genres
            FROM dim_tracks t
            JOIN fact_rankings f ON t.track_id = f.track_id
            JOIN dim_artists a ON f.artist_id = a.artist_id
            WHERE (t.name LIKE ? OR a.name LIKE ?)
            LIMIT ?
        """, tuple(fallback_params)))

@app.route('/api/artists')
def api_artists():
    n = request.args.get('n', 20, type=int)
    q = request.args.get('q', '').strip()
    min_year = request.args.get('min_year', '').strip()
    max_year = request.args.get('max_year', '').strip()

    is_filtered_by_year = (min_year and min_year > '1960') or (max_year and max_year < '2024')

    if is_filtered_by_year or q:
        if q:
            where_year = []
            params = [f"%{q}%"]
            if min_year:
                where_year.append("s.year >= ?")
                params.append(min_year)
            if max_year:
                where_year.append("s.year <= ?")
                params.append(max_year)
            where_year_sql = ("AND " + " AND ".join(where_year)) if where_year else ""
            params.append(n)

            return jsonify(db_query(f"""
                SELECT a.name AS artist, CAST(COALESCE(SUM(s.track_count), 0) AS INTEGER) AS track_count, a.genres
                FROM dim_artists a
                JOIN summary_artist_yearly s ON a.artist_id = s.artist_id
                WHERE a.name LIKE ? {where_year_sql}
                GROUP BY a.artist_id, a.name, a.genres
                ORDER BY track_count DESC LIMIT ?
            """, tuple(params)))

        where = []
        params = []
        if min_year:
            where.append("year >= ?")
            params.append(min_year)
        if max_year:
            where.append("year <= ?")
            params.append(max_year)

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        params.append(n)

        return jsonify(db_query(f"""
            SELECT a.name AS artist, sub.track_count, a.genres
            FROM (
                SELECT artist_id, CAST(SUM(track_count) AS INTEGER) AS track_count
                FROM summary_artist_yearly
                {where_sql}
                GROUP BY artist_id
                ORDER BY track_count DESC LIMIT ?
            ) sub
            JOIN dim_artists a ON sub.artist_id = a.artist_id
            ORDER BY sub.track_count DESC
        """, tuple(params)))

    return jsonify(db_query("""
        SELECT a.name AS artist, s.track_count, a.genres
        FROM summary_top_artists s
        JOIN dim_artists a ON s.artist_id = a.artist_id
        ORDER BY s.track_count DESC LIMIT ?
    """, (n,)))

@app.route('/api/genres/top')
def api_genres_top():
    n = request.args.get('n', 15, type=int)
    return jsonify(db_query(
        "SELECT genre, artist_count, track_count FROM summary_genres ORDER BY track_count DESC LIMIT ?", (n,)
    ))

if __name__ == '__main__':
    print("")
    print("  Greentify Web UI")
    print("  Open: http://localhost:5000")
    print("")
    app.run(debug=False, port=5000)
