"""
streamlit_app.py
Greentify — Spotify Music Analytics Dashboard
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Greentify",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get Help": None, "Report a bug": None, "About": "Greentify — Spotify Music Analytics"}
)

DB = "greenify.db"

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* hide default chrome */
#MainMenu, footer { visibility: hidden; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #0b1510;
    border-right: 1px solid rgba(255,255,255,0.06);
}
section[data-testid="stSidebar"] h1 {
    color: #c8e6c9;
    font-size: 1.4rem;
    font-weight: 700;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 18px 20px !important;
}
[data-testid="stMetricLabel"] { color: #8CA090 !important; font-size: 0.78rem !important; }
[data-testid="stMetricValue"] { color: #c8e6c9 !important; font-size: 1.65rem !important; font-weight: 700 !important; }

/* Dataframe */
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

/* Slider track */
.stSlider [data-baseweb="slider"] { padding: 0 4px; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03);
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px;
    color: #8CA090;
    font-size: 0.82rem;
    font-weight: 500;
    padding: 6px 14px;
}
.stTabs [aria-selected="true"] {
    background: rgba(30,215,96,0.12) !important;
    color: #1ED760 !important;
}

/* Input */
[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    color: #c8e6c9;
}

/* Select box */
[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background: rgba(255,255,255,0.04);
    border-radius: 10px;
}

/* Info / warning boxes */
.stInfo, .stWarning { border-radius: 10px; }

/* Caption */
.stCaption { color: #8CA090; }

/* Divider */
hr { border-color: rgba(255,255,255,0.07); }
</style>
""", unsafe_allow_html=True)

# ── Plotly dark theme ──────────────────────────────────────────────────────────
EMERALD      = "#1ED760"
EMERALD_MED  = "rgba(30,215,96,0.50)"
EMERALD_DIM  = "rgba(30,215,96,0.22)"
GRID_COLOR   = "rgba(255,255,255,0.05)"

BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#8CA090", family="Inter, Arial, sans-serif", size=12),
    xaxis=dict(gridcolor=GRID_COLOR, linecolor="transparent", tickcolor="#3E5244"),
    yaxis=dict(gridcolor=GRID_COLOR, linecolor="transparent", tickcolor="#3E5244"),
    margin=dict(l=8, r=8, t=36, b=8),
    hoverlabel=dict(
        bgcolor="rgba(8,13,10,0.95)",
        bordercolor="rgba(30,215,96,0.25)",
        font_color="#c8e6c9",
        font_size=12,
    ),
)

# ── DB helpers ─────────────────────────────────────────────────────────────────
def db_query(sql, params=()):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df

@st.cache_data
def get_metrics():
    return db_query("SELECT * FROM summary_metrics").iloc[0]

@st.cache_data
def get_yearly_tracks(min_year: int, max_year: int):
    return db_query(
        "SELECT year, track_count FROM summary_yearly "
        "WHERE year >= ? AND year <= ? ORDER BY year",
        (str(min_year), str(max_year))
    )

@st.cache_data
def get_explicit():
    return db_query("SELECT * FROM summary_explicit")

@st.cache_data
def get_duration_sample():
    return db_query("SELECT duration_min FROM summary_duration_sample LIMIT 10000")

@st.cache_data
def get_top_artists_alltime(n: int):
    """Fast path: uses precomputed summary table."""
    return db_query(
        "SELECT artist, track_count FROM summary_top_artists "
        "ORDER BY track_count DESC LIMIT ?", (n,)
    )

@st.cache_data
def get_top_artists_filtered(n: int, min_year: int, max_year: int):
    """Filtered path: live query with year range."""
    return db_query("""
        SELECT a.name AS artist, COUNT(DISTINCT f.track_id) AS track_count
        FROM dim_artists a
        JOIN fact_rankings f ON a.artist_id = f.artist_id
        JOIN dim_tracks t ON f.track_id = t.track_id
        WHERE CAST(SUBSTR(t.release_date,1,4) AS INTEGER) BETWEEN ? AND ?
        GROUP BY a.artist_id, a.name
        ORDER BY track_count DESC LIMIT ?
    """, (min_year, max_year, n))

@st.cache_data(ttl=60)
def search_tracks(q: str, limit: int, min_year: int, max_year: int):
    return db_query("""
        SELECT
            t.name            AS Track,
            a.name            AS Artist,
            a.genres          AS Genres,
            t.album_name      AS Album,
            SUBSTR(t.release_date,1,4)             AS Year,
            ROUND(t.duration_ms/60000.0,2)         AS "Duration (min)",
            CASE WHEN t.explicit=1 THEN 'E' ELSE 'C' END AS Label
        FROM dim_tracks t
        JOIN fact_rankings f ON t.track_id = f.track_id
        JOIN dim_artists   a ON f.artist_id = a.artist_id
        WHERE (t.name LIKE ? OR a.name LIKE ?)
          AND CAST(SUBSTR(t.release_date,1,4) AS INTEGER) BETWEEN ? AND ?
        LIMIT ?
    """, (f"%{q}%", f"%{q}%", min_year, max_year, limit))

@st.cache_data(ttl=60)
def get_artists(n: int, q: str, min_year: int, max_year: int):
    if q:
        return db_query("""
            SELECT a.name AS Artist, COUNT(DISTINCT f.track_id) AS Tracks, a.genres AS Genres
            FROM dim_artists a
            JOIN fact_rankings f ON a.artist_id = f.artist_id
            JOIN dim_tracks t ON f.track_id = t.track_id
            WHERE a.name LIKE ?
              AND CAST(SUBSTR(t.release_date,1,4) AS INTEGER) BETWEEN ? AND ?
            GROUP BY a.artist_id, a.name, a.genres
            ORDER BY Tracks DESC LIMIT ?
        """, (f"%{q}%", min_year, max_year, n))
    return db_query("""
        SELECT a.name AS Artist, COUNT(DISTINCT f.track_id) AS Tracks, a.genres AS Genres
        FROM dim_artists a
        JOIN fact_rankings f ON a.artist_id = f.artist_id
        JOIN dim_tracks t ON f.track_id = t.track_id
        WHERE CAST(SUBSTR(t.release_date,1,4) AS INTEGER) BETWEEN ? AND ?
        GROUP BY a.artist_id, a.name, a.genres
        ORDER BY Tracks DESC LIMIT ?
    """, (min_year, max_year, n))

# ── Chart factories ────────────────────────────────────────────────────────────
def bar_chart(df, x_col, y_col, title="", height=420):
    colors = [
        EMERALD if i == 0 else (EMERALD_MED if i < 3 else EMERALD_DIM)
        for i in range(len(df))
    ]
    fig = go.Figure(go.Bar(
        x=df[x_col], y=df[y_col], orientation="h",
        marker_color=colors, marker_line_width=0,
        hovertemplate="<b>%{y}</b><br>%{x:,} tracks<extra></extra>",
    ))
    layout = dict(**BASE_LAYOUT, height=height, title=dict(text=title, font=dict(color="#8CA090", size=13)))
    layout["yaxis"] = dict(autorange="reversed", **BASE_LAYOUT["yaxis"])
    fig.update_layout(**layout)
    return fig

def area_chart(df, x_col, y_col, height=340):
    fig = go.Figure(go.Scatter(
        x=df[x_col], y=df[y_col], mode="lines", fill="tozeroy",
        line=dict(color=EMERALD, width=2.5),
        fillcolor="rgba(30,215,96,0.10)",
        hovertemplate="<b>%{x}</b>: %{y:,} tracks<extra></extra>",
    ))
    fig.update_layout(**BASE_LAYOUT, height=height)
    return fig

def donut_chart(df, labels_col, values_col, height=340):
    fig = go.Figure(go.Pie(
        labels=df[labels_col], values=df[values_col], hole=0.65,
        marker=dict(
            colors=[EMERALD, "rgba(255,255,255,0.07)"],
            line=dict(color=["rgba(30,215,96,0.4)", "rgba(255,255,255,0.09)"], width=1),
        ),
        hovertemplate="<b>%{label}</b><br>%{value:,} (%{percent})<extra></extra>",
        textposition="none",
    ))
    fig.update_layout(
        **BASE_LAYOUT, height=height, showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, font=dict(color="#8CA090")),
    )
    return fig

def histogram_chart(dur_df, height=340):
    vals = dur_df["duration_min"].dropna()
    vals = vals[(vals > 0) & (vals < 15)]
    fig = px.histogram(
        vals, nbins=30,
        color_discrete_sequence=["rgba(30,215,96,0.45)"],
        labels={"value": "Duration (min)", "count": "Tracks"},
    )
    fig.update_traces(marker_line_width=1, marker_line_color=EMERALD)
    fig.update_layout(**BASE_LAYOUT, height=height, bargap=0.05,
                      xaxis_title="Duration (min)", yaxis_title="Tracks")
    return fig

# ── Sidebar navigation ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎵 Greentify")
    st.caption("Spotify Music Analytics")
    st.divider()
    page = st.radio(
        "Navigate",
        ["🏠  Overview", "🎵  Tracks", "👥  Artists"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Data: Kaggle 1.2M Tracks Dataset")

# ── Constants ──────────────────────────────────────────────────────────────────
MIN_Y, MAX_Y = 1960, 2024


# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
if "Overview" in page:
    st.markdown("# 🎵 Greentify")
    st.markdown("#### Spotify music data analytics platform")
    st.caption("Explore charts, artists, tracks and global trends with powerful data insights.")
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.info("**🎵 Tracks**  \nAnalyze track performance, popularity, release trends and audio features across 1.2M songs.")
    with c2:
        st.info("**👥 Artists**  \nDiscover artist growth, genre trends and audience insights across 140K artists.")

    st.divider()
    m = get_metrics()
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Total Tracks",  f"{int(m['total_tracks']):,}")
    mc2.metric("Total Artists", f"{int(m['total_artists']):,}")
    mc3.metric("Avg Duration",  f"{float(m['avg_duration_min']):.1f} min")
    mc4.metric("Explicit",      f"{int(m['explicit_count']):,}")


# ══════════════════════════════════════════════════════════════════════════════
# TRACKS
# ══════════════════════════════════════════════════════════════════════════════
elif "Tracks" in page:
    st.markdown("## 🎵 Tracks")
    st.caption("Explore 1.2M tracks — distribution, trends and search")

    # ── Timeline control ───────────────────────────────────────────────────────
    year_range = st.slider(
        "📅 **Release Year Range**",
        min_value=MIN_Y, max_value=MAX_Y,
        value=(MIN_Y, MAX_Y),
        step=1, key="tr_year",
        help="Drag either handle to filter all charts by release year"
    )
    min_year, max_year = year_range
    is_alltime = (min_year == MIN_Y and max_year == MAX_Y)

    # ── Stat cards ─────────────────────────────────────────────────────────────
    m = get_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Tracks",  f"{int(m['total_tracks']):,}")
    c2.metric("Total Artists", f"{int(m['total_artists']):,}")
    c3.metric("Avg Duration",  f"{float(m['avg_duration_min']):.1f} min")
    c4.metric("Explicit",      f"{int(m['explicit_count']):,}")

    st.divider()

    # ── Tabs ───────────────────────────────────────────────────────────────────
    t_search, t_top, t_split, t_timeline, t_dur = st.tabs([
        "🔍 Search", "🏆 Top Artists", "🍩 Content Split",
        "📈 Release Timeline", "⏱ Duration Distribution",
    ])

    # ── Search ─────────────────────────────────────────────────────────────────
    with t_search:
        col_q, col_lim = st.columns([4, 1])
        q = col_q.text_input(
            "Search track or artist",
            placeholder="e.g. Bohemian Rhapsody, Taylor Swift...",
            key="tr_q", label_visibility="collapsed"
        )
        limit = col_lim.selectbox("Rows", [50, 100, 200], key="tr_lim", label_visibility="collapsed")

        if q:
            with st.spinner("Searching…"):
                df = search_tracks(q, limit, min_year, max_year)
            if df.empty:
                st.warning("No results found.")
            else:
                st.caption(f"Found **{len(df):,}** results for *{q}*  ({min_year}–{max_year})")
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Type above to search tracks. The year range slider above filters results.")

    # ── Top Artists ────────────────────────────────────────────────────────────
    with t_top:
        top_n = st.select_slider(
            "Top N artists", options=[5, 10, 12, 15, 20, 25, 30, 50],
            value=15, key="tr_topn"
        )
        with st.spinner("Loading…"):
            df = get_top_artists_alltime(top_n) if is_alltime else get_top_artists_filtered(top_n, min_year, max_year)
        if df.empty:
            st.warning("No data for this range.")
        else:
            fig = bar_chart(df, "track_count", "artist",
                            title=f"Top {top_n} Artists by Track Count ({min_year}–{max_year})",
                            height=max(340, top_n * 28))
            st.plotly_chart(fig, use_container_width=True)

    # ── Content Split ──────────────────────────────────────────────────────────
    with t_split:
        exp = get_explicit()
        col_l, col_m, col_r = st.columns([1, 2, 1])
        with col_m:
            st.plotly_chart(donut_chart(exp, "type", "count"), use_container_width=True)
        # Stats below
        total = exp["count"].sum()
        for _, row in exp.iterrows():
            pct = row["count"] / total * 100
            st.caption(f"**{row['type']}**: {int(row['count']):,} tracks ({pct:.1f}%)")

    # ── Release Timeline ───────────────────────────────────────────────────────
    with t_timeline:
        with st.spinner("Loading timeline…"):
            yr = get_yearly_tracks(min_year, max_year)
        if yr.empty:
            st.warning("No data for this year range.")
        else:
            st.plotly_chart(area_chart(yr, "year", "track_count"), use_container_width=True)
            peak = yr.loc[yr["track_count"].idxmax()]
            st.caption(f"Peak year: **{peak['year']}** with **{int(peak['track_count']):,}** tracks")

    # ── Duration Distribution ──────────────────────────────────────────────────
    with t_dur:
        dur = get_duration_sample()
        st.plotly_chart(histogram_chart(dur), use_container_width=True)
        st.caption("Sample of 10,000 tracks · Tracks under 15 minutes shown")


# ══════════════════════════════════════════════════════════════════════════════
# ARTISTS
# ══════════════════════════════════════════════════════════════════════════════
elif "Artists" in page:
    st.markdown("## 👥 Artists")
    st.caption("Top artists ranked by track count in the dataset")

    # ── Controls ───────────────────────────────────────────────────────────────
    col_slider, col_n = st.columns([4, 1])
    year_range = col_slider.slider(
        "📅 **Release Year Range**",
        min_value=MIN_Y, max_value=MAX_Y,
        value=(MIN_Y, MAX_Y),
        step=1, key="ar_year",
        help="Filter artists by tracks released in this year range"
    )
    top_n = col_n.selectbox("Top N", [10, 20, 50, 100], index=3, key="ar_n", label_visibility="visible")
    min_year, max_year = year_range

    # ── Stat cards ─────────────────────────────────────────────────────────────
    m = get_metrics()
    c1, c2 = st.columns(2)
    c1.metric("Total Artists", f"{int(m['total_artists']):,}")
    c2.metric("Year Range", f"{min_year} – {max_year}")

    st.divider()

    t_chart, t_browse = st.tabs(["📊 Top Artists Chart", "🔍 Browse Artists"])

    # ── Chart ──────────────────────────────────────────────────────────────────
    with t_chart:
        with st.spinner("Loading chart…"):
            df = get_top_artists_filtered(top_n, min_year, max_year)
        if df.empty:
            st.warning("No data for this range.")
        else:
            fig = bar_chart(
                df, "track_count", "artist",
                title=f"Top {top_n} Artists by Track Count ({min_year}–{max_year})",
                height=max(420, top_n * 26),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ── Browse ─────────────────────────────────────────────────────────────────
    with t_browse:
        col_q, col_lim = st.columns([4, 1])
        q = col_q.text_input(
            "Filter artists", placeholder="Search artist name…",
            key="ar_q", label_visibility="collapsed"
        )
        limit = col_lim.selectbox("Show", [20, 50, 100], key="ar_lim", label_visibility="collapsed")

        with st.spinner("Loading artists…"):
            df = get_artists(limit, q, min_year, max_year)

        if df.empty:
            st.warning("No artists found.")
        else:
            st.caption(f"Showing **{len(df):,}** artists · {min_year}–{max_year}")
            st.dataframe(df, use_container_width=True, hide_index=True)
