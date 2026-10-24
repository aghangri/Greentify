import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Greenify | Spotify Analytics",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* ── Base ── */
    .stApp {
        background-color: #F4F8F5;
        background-image:
            radial-gradient(circle at 5% 15%,  rgba(29, 185, 84, 0.10), transparent 35%),
            radial-gradient(circle at 95% 85%, rgba(29, 185, 84, 0.07), transparent 35%);
        color: #1A2E1F;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.75) !important;
        backdrop-filter: blur(18px) !important;
        -webkit-backdrop-filter: blur(18px) !important;
        border-right: 1px solid rgba(29, 185, 84, 0.2) !important;
        box-shadow: 2px 0 20px rgba(29, 185, 84, 0.06);
    }

    /* ── Metric Cards ── */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.80) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(29, 185, 84, 0.25) !important;
        border-radius: 14px !important;
        padding: 18px 22px !important;
        box-shadow: 0 2px 16px rgba(29, 185, 84, 0.08),
                    0 1px 4px  rgba(0, 0, 0, 0.05) !important;
        transition: transform 0.3s ease, box-shadow 0.3s ease !important;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-5px) !important;
        box-shadow: 0 8px 32px rgba(29, 185, 84, 0.18),
                    0 2px 8px  rgba(0, 0, 0, 0.08) !important;
        border-color: rgba(29, 185, 84, 0.55) !important;
    }
    [data-testid="stMetricValue"] {
        color: #1DB954 !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #5A8A68 !important;
    }

    /* ── Headings ── */
    h1, h2, h3, h4 {
        color: #157A3C !important;
        font-weight: 700 !important;
    }

    /* ── Inputs & Selects ── */
    .stSelectbox div[data-baseweb="select"] > div,
    .stTextInput div[data-baseweb="input"] > div {
        background: rgba(255, 255, 255, 0.9) !important;
        border: 1px solid rgba(29, 185, 84, 0.35) !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 6px rgba(29, 185, 84, 0.06) !important;
        transition: all 0.25s ease !important;
    }
    .stSelectbox div[data-baseweb="select"] > div:focus-within,
    .stTextInput div[data-baseweb="input"] > div:focus-within {
        border-color: #1DB954 !important;
        box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.15) !important;
    }

    /* ── Plot containers ── */
    [data-testid="stPlotlyChart"] {
        background: rgba(255, 255, 255, 0.75) !important;
        border: 1px solid rgba(29, 185, 84, 0.15) !important;
        border-radius: 14px !important;
        padding: 8px !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        box-shadow: 0 2px 12px rgba(29, 185, 84, 0.06) !important;
    }

    /* ── DataFrame ── */
    [data-testid="stDataFrame"] > div {
        background: rgba(255, 255, 255, 0.85) !important;
        border: 1px solid rgba(29, 185, 84, 0.15) !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 12px rgba(29, 185, 84, 0.06) !important;
    }

    /* ── Divider ── */
    hr { border-color: rgba(29, 185, 84, 0.12) !important; }

    /* ── Caption ── */
    .stCaption, small { color: #7AAF88 !important; }

    /* ── Info box ── */
    [data-testid="stNotification"] {
        background: rgba(255, 255, 255, 0.85) !important;
        border: 1px solid rgba(29, 185, 84, 0.25) !important;
        border-radius: 10px !important;
        color: #157A3C !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: #F4F8F5; }
    ::-webkit-scrollbar-thumb { background: #B8DFC4; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #1DB954; }
</style>
""", unsafe_allow_html=True)

DB_NAME = "greenify.db"

@st.cache_data(ttl=300)
def query(sql, params=()):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA journal_mode=WAL")
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df

def light_chart(fig, height=380):
    fig.update_layout(
        paper_bgcolor='rgba(255,255,255,0)',
        plot_bgcolor='rgba(255,255,255,0)',
        font=dict(color='#5A8A68', size=12),
        xaxis=dict(
            showgrid=True,
            gridcolor='rgba(29, 185, 84, 0.08)',
            zerolinecolor='rgba(29, 185, 84, 0.15)',
            tickfont=dict(color='#5A8A68'),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(29, 185, 84, 0.08)',
            zerolinecolor='rgba(29, 185, 84, 0.15)',
            tickfont=dict(color='#5A8A68'),
        ),
        height=height,
        margin=dict(l=0, r=10, t=20, b=0),
        legend=dict(bgcolor='rgba(255,255,255,0)', font=dict(color='#5A8A68'))
    )
    return fig

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.image("https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_RGB_Green.png", width=160)
st.sidebar.title("Greenify 🌿")
st.sidebar.markdown("**Spotify Analytics — 1.2M Şarkı**")
st.sidebar.divider()

top_n = st.sidebar.slider("🏆 Top N Sanatçı", 5, 30, 15)
min_year, max_year = st.sidebar.select_slider(
    "📅 Yıl Aralığı",
    options=list(range(1950, 2027)),
    value=(1990, 2026)
)
st.sidebar.divider()
st.sidebar.caption("Veriler precompute.py ile önceden hesaplandı — sorgular anlık!")

# ── Data ──────────────────────────────────────────────────────────────────────
metrics     = query("SELECT * FROM summary_metrics")
explicit    = query("SELECT * FROM summary_explicit")
duration    = query("SELECT * FROM summary_duration_sample")
top_artists = query(f"SELECT artist, track_count FROM summary_top_artists ORDER BY track_count DESC LIMIT {top_n}")
yearly      = query(f"SELECT year, track_count FROM summary_yearly WHERE year >= '{min_year}' AND year <= '{max_year}' ORDER BY year")

# ── Title ─────────────────────────────────────────────────────────────────────
st.title("🎵 Greenify — Spotify Analytics Dashboard")
st.markdown(f"**{min_year}–{max_year}** yılları | Top **{top_n}** sanatçı")
st.divider()

# ── KPI Cards ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("🎵 Toplam Şarkı",   f"{int(metrics['total_tracks'][0]):,}")
c2.metric("🎤 Toplam Sanatçı", f"{int(metrics['total_artists'][0]):,}")
c3.metric("⏱ Ort. Süre (dk)", f"{metrics['avg_duration_min'][0]:.2f}")
c4.metric("🔞 Explicit Şarkı", f"{int(metrics['explicit_count'][0]):,}")

st.divider()

# ── Row 1: Top Artists + Explicit ─────────────────────────────────────────────
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"🏆 Top {top_n} Sanatçı")
    if not top_artists.empty:
        fig = px.bar(
            top_artists, x="track_count", y="artist", orientation="h",
            color="track_count",
            color_continuous_scale=[
                [0.0, "#E8F5EE"],
                [0.5, "#1DB954"],
                [1.0, "#0D7A35"],
            ],
            text="track_count",
            labels={"track_count": "Şarkı Sayısı", "artist": "Sanatçı"}
        )
        fig.update_traces(
            textposition="outside",
            textfont=dict(color="#157A3C", size=11)
        )
        fig.update_layout(
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False
        )
        st.plotly_chart(light_chart(fig, height=460), use_container_width=True)

with col2:
    st.subheader("🔞 Explicit Dağılımı")
    if not explicit.empty:
        fig2 = px.pie(
            explicit, names="type", values="count",
            color="type",
            color_discrete_map={"Explicit": "#1DB954", "Clean": "#D4EFD9"},
            hole=0.62
        )
        fig2.update_traces(
            textposition="inside",
            textinfo="percent+label",
            textfont=dict(color="#1A2E1F"),
            marker=dict(line=dict(color='#F4F8F5', width=3))
        )
        fig2.update_layout(showlegend=False)
        st.plotly_chart(light_chart(fig2, height=460), use_container_width=True)

# ── Row 2: Yearly + Duration ───────────────────────────────────────────────────
col3, col4 = st.columns(2)

with col3:
    st.subheader(f"📅 Yıla Göre Şarkı Sayısı")
    if not yearly.empty:
        fig3 = px.area(
            yearly, x="year", y="track_count",
            color_discrete_sequence=["#1DB954"],
            labels={"year": "Yıl", "track_count": "Şarkı Sayısı"}
        )
        fig3.update_traces(
            fillcolor="rgba(29, 185, 84, 0.15)",
            line=dict(color="#1DB954", width=2.5)
        )
        st.plotly_chart(light_chart(fig3, height=350), use_container_width=True)

with col4:
    st.subheader("⏱ Şarkı Süresi Dağılımı")
    if not duration.empty:
        fig4 = px.histogram(
            duration, x="duration_min", nbins=40,
            color_discrete_sequence=["#1DB954"],
            labels={"duration_min": "Süre (dakika)"}
        )
        fig4.update_traces(
            marker=dict(
                color="rgba(29, 185, 84, 0.75)",
                line=dict(color="#0D7A35", width=0.5)
            )
        )
        fig4.update_layout(bargap=0.08)
        st.plotly_chart(light_chart(fig4, height=350), use_container_width=True)

# ── Search ────────────────────────────────────────────────────────────────────
st.divider()
st.subheader("🔍 Şarkı / Sanatçı Arama")

col_s1, col_s2 = st.columns([4, 1])
with col_s1:
    search = st.text_input("Şarkı adı veya sanatçı adı gir...", "")
with col_s2:
    limit = st.selectbox("Limit", [50, 100, 200], index=0)

if search:
    result = query("""
        SELECT
            t.name AS Sarki, a.name AS Sanatci,
            t.album_name AS Album,
            SUBSTR(t.release_date,1,4) AS Yil,
            ROUND(t.duration_ms/60000.0,2) AS "Sure(dk)",
            CASE WHEN t.explicit=1 THEN 'Explicit' ELSE 'Clean' END AS Tur
        FROM dim_tracks t
        JOIN fact_rankings f ON t.track_id = f.track_id
        JOIN dim_artists a   ON f.artist_id = a.artist_id
        WHERE t.name LIKE ? OR a.name LIKE ?
        LIMIT ?
    """, params=(f"%{search}%", f"%{search}%", limit))
    result.index = range(1, len(result) + 1)
    st.dataframe(result, use_container_width=True, height=400)
    st.caption(f"**{len(result):,}** sonuç gösteriliyor.")
else:
    st.info("Yukarıya bir şarkı veya sanatçı adı girerek arama yapın.")

st.divider()
st.caption("Greenify | Veri: Spotify 1.2M Songs (Kaggle) | Grafikler: Plotly | UI: Streamlit")
