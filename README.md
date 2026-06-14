# SENTINEL — Influence Operations Detection Engine

AI-powered influence operations monitor for defense and intelligence analysts — ingests adversary media and social channels, clusters emerging narratives, maps them to DISARM framework TTPs, and generates finished intelligence assessments.

Built for information warfare analysts, IO planners, and defense contractors who need to track coordinated adversary messaging campaigns in near-real-time.

**Live demo:** https://sentinel-io-engine.onrender.com

---

## What It Does

Influence operations work by seeding a false narrative across multiple outlets simultaneously, then amplifying it through social media before anyone can respond. This tool models that detection workflow:

1. **Ingest** — pulls RSS feeds from adversary outlets (RT, Sputnik, TASS, Global Times) and baseline press (Reuters, BBC), plus Reddit threads for amplification signals
2. **Analyze** — Claude reads each article and extracts: narrative summary, named entities, keywords, sentiment, divisiveness flag, and credibility red flags
3. **Cluster** — keyword-overlap algorithm groups articles driving the same narrative into clusters and scores them for threat level and velocity
4. **TTP Mapping** — Claude maps each cluster to DISARM framework tactics, techniques, and procedures (T0007–T0085)
5. **Report** — Claude writes a formatted finished intelligence assessment across all active clusters in formal intel writing style

---

## Features

| Feature | Description |
|---------|-------------|
| Adversary feed monitor | RT, Sputnik, TASS, Global Times tracked as adversary outlets |
| Baseline press | Reuters, BBC as ground-truth comparison |
| Reddit amplification | Monitors r/worldnews, r/news, r/conspiracy, r/military, r/antiwar for social spread |
| Narrative extraction | Claude identifies the core claim, entities, keywords, credibility signals per article |
| Cluster dashboard | Narrative clusters ranked by threat level (HIGH/MEDIUM/LOW) and velocity score |
| DISARM TTP tagging | 10 TTPs across Plan/Prepare/Execute/Monetise phases mapped with confidence ratings |
| Source monitor | Per-outlet article counts and last-seen timestamps |
| Intel report generator | Finished intelligence assessment with key findings, attribution, and recommended actions |
| Ref numbering | Reports numbered SENTINEL-YYYY-NNN for traceable filing |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.12 |
| AI | Claude Haiku (narrative extraction + TTP classification + report generation) |
| Feed ingestion | feedparser (RSS) + httpx (Reddit JSON API) |
| Clustering | Keyword-overlap algorithm with velocity scoring |
| Database | SQLite + SQLAlchemy 2.0 |
| Frontend | Jinja2 templates + vanilla CSS |
| Deploy | Render (free tier) |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/JaKPoT/sentinel-io-engine.git
cd sentinel-io-engine

# 2. Add your Anthropic API key
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY=sk-ant-...

# 3. Run (Windows)
START_HERE.bat

# Or manually:
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\uvicorn main:app --reload
```

Open http://localhost:8000

---

## Demo

Load the pre-built demo at `/seed`. Shows **Operation STEEL ECHO** — a fictional coordinated adversary campaign:

- Scenario: RT seeds a false claim that Northgate Defense Systems (fictional) falsified F-35 targeting computer certifications
- Wave 1: RT and Sputnik seed the narrative (14:23–14:31)
- Wave 2: TASS and Global Times amplify it with fabricated expert quotes (15:45–16:02)
- Wave 3: Reddit threads spread it to a wider audience (16:15–16:58)
- Reuters and BBC provide contrasting baseline coverage with named sources and DoD denials

The dashboard shows 3 narrative clusters, threat levels, velocity scores, and DISARM TTP tags. Click any cluster to drill into the article breakdown by outlet type. Generate a report to produce a finished SENTINEL-2026-001 intelligence assessment.

---

## API Keys Required

| Key | Where to get it | Cost |
|-----|----------------|------|
| `ANTHROPIC_API_KEY` | console.anthropic.com | ~$0.01–0.02/analysis run (Haiku model) |

---

## DISARM TTPs Covered

| ID | Name | Phase |
|----|------|-------|
| T0007 | Create Inauthentic Accounts | Plan |
| T0008 | Create Fake Experts | Plan |
| T0019 | Seed Distortions | Prepare |
| T0023 | Distort Facts | Prepare |
| T0046 | Search Engine Optimization | Execute |
| T0049 | Flooding the Information Space | Execute |
| T0057 | Amplify Divisive Content | Execute |
| T0061 | Sell Advertising around Content | Monetise |
| T0081 | Aggregate and Promote Existing Narratives | Execute |
| T0085 | Coordinate on Encrypted Platforms | Plan |

---

## Architecture

```
config.py           RSS sources, Reddit subreddits, clustering thresholds
ingestor.py         feedparser RSS + Reddit JSON ingestion, URL deduplication
cluster_engine.py   keyword-overlap clustering, velocity scoring, threat level
disarm_ttps.py      DISARM framework TTP catalog
claude_analyst.py   3 Claude calls: narrative extraction, TTP classification, report generation
models.py           SQLAlchemy ORM (Article, NarrativeCluster, TTPTag, IntelReport)
database.py         Engine + session plumbing
main.py             FastAPI routes + Jinja rendering
templates/          Dashboard, cluster detail, report list/detail, source monitor
static/css/         Local stylesheet
seed_data.py        Operation STEEL ECHO synthetic dataset
```

The clustering engine and Claude analyst are fully decoupled from the web layer and can be called and tested independently.

---

## Deployment (Render)

1. Push to GitHub
2. Connect repo at render.com → New Web Service
3. Set `ANTHROPIC_API_KEY` as an Environment Secret in the Render dashboard
4. Deploy — Render auto-detects `render.yaml`

---

## Tests

```bash
venv\Scripts\python.exe -m pytest tests/ -v
# 19 passed in 1.49s
```

Tests cover: keyword overlap, threat level classification, narrative extraction (including markdown fence stripping and missing-field handling), TTP cluster analysis, and API error propagation.

---

*DEMONSTRATION ONLY — synthetic data — Operation STEEL ECHO is entirely fictional. Not for operational intelligence use.*
