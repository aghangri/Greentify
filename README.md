# 🌿 Greentify (Greenify)

> **High-Performance Spotify & Music Data Analytics Platform**  
> Interactive analytics, full-text search, and visual exploration over **1.2M+ tracks**, **140K+ artists**, and **1,700+ genres** on embedded infrastructure.

---

## ⚡ Overview

**Greentify** is an end-to-end music intelligence and analytics platform. It collects, enriches, normalizes, and visualizes massive audio datasets from Spotify, Last.fm, and Kaggle.

Designed specifically to eliminate performance bottlenecks over large relational datasets, Greentify achieves **sub-100ms response times** across 1.2M+ records using SQLite FTS5 full-text search, OLAP precomputations, covering indices, and modern frontend caching—requiring zero distributed cluster overhead.

---

## ✨ Features

- **🚀 Instant Full-Text Search (FTS5):** Sub-10ms search across 1,200,000+ tracks and artists with prefix and token matching.
- **⏱️ Interactive Dual-Handle Timeline:** Custom timeline slider (1960–2024) with instant data filtering across metrics, release distributions, and artist rankings.
- **🎨 Modern Glassmorphic SPA:** Dark/Light theme toggle, dynamic interactive canvas soundwave background, smooth sidebar drawer, and responsive charts.
- **🎵 Logo-Matched Equalizer Animations:** Custom CSS-animated equalizer soundwave loader synced with the brand design for immediate feedback.
- **📊 Interactive Charts (Chart.js & Plotly):**
  - **Tracks Dashboard:** Track metrics, duration distributions, explicit vs. clean breakdown, release timeline, and live search.
  - **Artists Dashboard:** Artist rankings by release volume, customizable periods (Top 10 to Top 100), genre tags, and searchable artist cards.
- **🛠️ Dual Presentation Layers:**
  - **Modern Web App:** Flask REST microservice + Glassmorphic Single Page Application ([web_app.py](web_app.py) on `:5000`).
  - **Analytical Explorer:** Python-native Streamlit dashboard ([streamlit_app.py](streamlit_app.py) on `:8501`).

---

## 🏗️ Architecture

```
+-----------------------------------------------------------------------------------------+
|                                    GREENTIFY PLATFORM                                   |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|   +--------------------+   +---------------------+   +-----------------------------+    |
|   |  Spotify Web API   |   | Last.fm Tagging API |   | Kaggle & CSV Dataset Ingest |    |
|   +---------+----------+   +----------+----------+   +--------------+--------------+    |
|             |                         |                             |                   |
|             +-------------------------+-----------------------------+                   |
|                                       | (ETL & Ingestion Pipelines)                     |
|                                       v                                                 |
|   +---------------------------------------------------------------------------------+   |
|   |                           SQLite Star Schema & FTS5                             |   |
|   |       dim_tracks | dim_artists | dim_playlists | fact_rankings | fts_tracks     |   |
|   +-----------------------------------+---------------------------------------------+   |
|                                       | (Precomputation & Covering Indices)             |
|                                       v                                                 |
|   +---------------------------------------------------------------------------------+   |
|   |                   Precomputed Materialized Summary Layer (OLAP)                 |   |
|   |   summary_metrics | summary_top_artists | summary_yearly | summary_artist_yearly|   |
|   +-----------------------------------+---------------------------------------------+   |
|                                       |                                                 |
|                     +-----------------+-----------------+                               |
|                     |                                   |                               |
|                     v                                   v                               |
|       +---------------------------+       +---------------------------+                 |
|       |     Flask REST API        |       |    Streamlit Dashboard    |                 |
|       |   (web_app.py :5000)      |       |  (streamlit_app.py :8501) |                 |
|       +-------------+-------------+       +---------------------------+                 |
|                     |                                                                   |
|                     v                                                                   |
|       +---------------------------+                                                     |
|       |   Glassmorphic Web UI     |                                                     |
|       | (Chart.js + Canvas Waves) |                                                     |
|       +---------------------------+                                                     |
+-----------------------------------------------------------------------------------------+
```

For complete database schema details and architectural diagrams, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.9+ installed
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/aghangri/Greentify.git
cd Greentify
```

### 3. Set Up Virtual Environment & Dependencies
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 4. Configuration (Optional for API Enrichment)
If you wish to run the data collection and enrichment scripts, create a `.env` file in the root directory:
```env
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:9090
LASTFM_API_KEY=your_lastfm_api_key
```

---

## 💻 Running the Application

### Option A: Modern Flask Web App (Recommended)
```bash
python web_app.py
```
Open your browser and navigate to **[http://localhost:5000](http://localhost:5000)**.

### Option B: Streamlit Analytical Dashboard
```bash
streamlit run streamlit_app.py
```
Open your browser and navigate to **[http://localhost:8501](http://localhost:8501)**.

---

## 📁 Repository Structure

```
├── templates/
│   └── index.html             # Glassmorphic Single-Page Application (HTML5/CSS3/JS)
├── web_app.py                 # Flask REST service with optimized SQL & FTS5 queries
├── streamlit_app.py           # Streamlit data visualization dashboard
├── dashboard.py               # Auxiliary dashboard implementation
├── ARCHITECTURE.md            # Comprehensive system & database architecture documentation
├── init_db.py                 # Star schema table initialization
├── import_kaggle.py           # Chunked importer for 1.2M Kaggle dataset
├── import_csv.py              # CSV chart ingestion
├── fetch_spotify_data.py      # Spotify Web API ingestion connector
├── fetch_genres_lastfm.py     # Last.fm tagging API connector with checkpointing
├── update_genres.py           # Batch genre enrichment
├── precompute.py              # Precomputation engine for core metric summaries
├── precompute_genres.py       # Precomputation engine for genre analytics
├── create_views.py            # Analytical SQL view generator
├── requirements.txt           # Python package dependencies
└── .gitignore                 # Git ignore rules for environments, secrets & DBs
```

---

## ⚡ Performance Optimizations

| Area | Solution | Result |
| :--- | :--- | :--- |
| **Track & Artist Search** | SQLite FTS5 Full-Text Search with prefix tokenization | **10.0s ➔ 0.03s** (~300x faster) |
| **Year Range Filtering** | Composite covering index `(year, artist_id, track_count)` + subquery aggregation | **1.45s ➔ 0.08s** (~17x faster) |
| **Concurrency** | SQLite WAL (Write-Ahead Logging) + 64MB page cache | Zero reader/writer lock blocking |
| **Frontend Rendering** | In-place Chart.js updates + parallel `Promise.all()` fetching | Buttery-smooth slider interaction |

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
