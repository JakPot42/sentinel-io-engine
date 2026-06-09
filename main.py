from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from claude_analyst import AnalystError, analyze_cluster_ttps, extract_narrative, generate_intel_report
from cluster_engine import run_clustering
from config import APP_TITLE, DEMO_BANNER, DEMO_MODE
from database import SessionLocal, get_db, init_db
from ingestor import ingest_all
from models import Article, IntelReport, NarrativeCluster, TTPTag
from seed_data import load_seed_data

app = FastAPI(title=APP_TITLE)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup():
    init_db()


def _ctx(extra: dict | None = None) -> dict:
    base = {"app_title": APP_TITLE, "demo_mode": DEMO_MODE, "demo_banner": DEMO_BANNER}
    if extra:
        base.update(extra)
    return base


# ── Dashboard ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    clusters = (
        db.query(NarrativeCluster)
        .order_by(NarrativeCluster.threat_level.desc(), NarrativeCluster.velocity_score.desc())
        .all()
    )
    unanalyzed_count = db.query(Article).filter(Article.is_analyzed == False).count()
    total_articles = db.query(Article).count()
    adversary_articles = db.query(Article).filter(Article.outlet_type == "adversary").count()
    high_threat = sum(1 for c in clusters if c.threat_level == "HIGH")
    return templates.TemplateResponse(request, "index.html", _ctx({
        "clusters": clusters,
        "unanalyzed_count": unanalyzed_count,
        "total_articles": total_articles,
        "adversary_articles": adversary_articles,
        "high_threat_clusters": high_threat,
    }))


# ── Seed data ────────────────────────────────────────────────────────────────

@app.get("/seed")
def seed(db: Session = Depends(get_db)):
    result = load_seed_data(db)
    return RedirectResponse(url="/", status_code=303)


# ── Ingest ───────────────────────────────────────────────────────────────────

@app.post("/ingest")
def ingest(db: Session = Depends(get_db)):
    result = ingest_all(db)
    return RedirectResponse(url="/", status_code=303)


# ── Analyze (Claude narrative extraction + clustering) ────────────────────────

@app.post("/analyze")
def analyze(db: Session = Depends(get_db)):
    articles = db.query(Article).filter(Article.is_analyzed == False).limit(50).all()
    errors = 0
    for article in articles:
        try:
            data = extract_narrative(
                article.title,
                article.body_text or "",
                article.source_name,
                article.outlet_type,
            )
            article.narrative_summary = data["narrative_summary"]
            article.entities = data["entities"]
            article.keywords = data["keywords"]
            article.sentiment = data["sentiment"]
            article.is_divisive = data["is_divisive"]
            article.credibility_signals = data["credibility_signals"]
            article.is_analyzed = True
        except AnalystError:
            errors += 1
    db.commit()
    run_clustering(db)
    return RedirectResponse(url="/", status_code=303)


# ── Cluster detail ────────────────────────────────────────────────────────────

@app.get("/cluster/{cluster_id}", response_class=HTMLResponse)
def cluster_detail(request: Request, cluster_id: int, db: Session = Depends(get_db)):
    cluster = db.query(NarrativeCluster).filter(NarrativeCluster.id == cluster_id).first()
    if not cluster:
        return RedirectResponse(url="/", status_code=303)
    articles_by_type = {
        "adversary": [a for a in cluster.articles if a.outlet_type == "adversary"],
        "baseline": [a for a in cluster.articles if a.outlet_type == "baseline"],
        "social": [a for a in cluster.articles if a.outlet_type == "social"],
    }
    return templates.TemplateResponse(request, "cluster_detail.html", _ctx({
        "cluster": cluster,
        "articles_by_type": articles_by_type,
    }))


@app.post("/cluster/{cluster_id}/analyze-ttps")
def analyze_ttps(cluster_id: int, db: Session = Depends(get_db)):
    cluster = db.query(NarrativeCluster).filter(NarrativeCluster.id == cluster_id).first()
    if not cluster:
        return RedirectResponse(url="/", status_code=303)

    articles_summary = [
        {
            "source_name": a.source_name,
            "outlet_type": a.outlet_type,
            "title": a.title,
            "narrative_summary": a.narrative_summary or "",
        }
        for a in cluster.articles[:20]
    ]

    try:
        data = analyze_cluster_ttps(cluster.label, articles_summary)
        # Clear existing TTP tags for this cluster
        for t in cluster.ttp_tags:
            db.delete(t)
        db.flush()
        for ttp in data.get("ttps", []):
            db.add(TTPTag(
                cluster_id=cluster.id,
                ttp_id=ttp.get("id", ""),
                ttp_name=ttp.get("name", ""),
                confidence=ttp.get("confidence", "low"),
                rationale=ttp.get("rationale", ""),
            ))
        cluster.threat_level = data.get("threat_level", cluster.threat_level)
        db.commit()
    except AnalystError:
        pass
    return RedirectResponse(url=f"/cluster/{cluster_id}", status_code=303)


# ── Reports ───────────────────────────────────────────────────────────────────

@app.get("/reports", response_class=HTMLResponse)
def report_list(request: Request, db: Session = Depends(get_db)):
    reports = db.query(IntelReport).order_by(IntelReport.generated_at.desc()).all()
    return templates.TemplateResponse(request, "report_list.html", _ctx({"reports": reports}))


@app.post("/reports/generate")
def generate_report(db: Session = Depends(get_db)):
    clusters = db.query(NarrativeCluster).all()
    clusters_data = [
        {
            "label": c.label,
            "threat_level": c.threat_level,
            "article_count": c.article_count,
            "adversary_count": c.adversary_count,
            "spread_hours": c.spread_hours,
            "ttps": [t.ttp_id for t in c.ttp_tags],
            "summary": c.summary,
        }
        for c in clusters
    ]
    try:
        data = generate_intel_report(clusters_data)
        existing_count = db.query(IntelReport).count()
        ref = f"SENTINEL-{datetime.now(timezone.utc).year}-{existing_count + 1:03d}"
        report = IntelReport(
            ref_number=ref,
            title=data["title"],
            subject=data["subject"],
            confidence_level=data["confidence_level"],
            attribution=data.get("attribution", ""),
            full_text=data["full_text"],
        )
        report.key_findings = data.get("key_findings", [])
        report.clusters.extend(clusters)
        db.add(report)
        db.commit()
        return RedirectResponse(url=f"/report/{report.id}", status_code=303)
    except AnalystError as exc:
        return RedirectResponse(url="/reports", status_code=303)


@app.get("/report/{report_id}", response_class=HTMLResponse)
def view_report(request: Request, report_id: int, db: Session = Depends(get_db)):
    report = db.query(IntelReport).filter(IntelReport.id == report_id).first()
    if not report:
        return RedirectResponse(url="/reports", status_code=303)
    return templates.TemplateResponse(request, "report_detail.html", _ctx({"report": report}))


# ── Source monitor ────────────────────────────────────────────────────────────

@app.get("/sources", response_class=HTMLResponse)
def source_monitor(request: Request, db: Session = Depends(get_db)):
    from sqlalchemy import func
    source_stats = (
        db.query(
            Article.source_name,
            Article.outlet_type,
            func.count(Article.id).label("count"),
            func.max(Article.fetched_at).label("last_seen"),
        )
        .group_by(Article.source_name, Article.outlet_type)
        .order_by(Article.outlet_type, Article.source_name)
        .all()
    )
    return templates.TemplateResponse(request, "source_monitor.html", _ctx({"source_stats": source_stats}))


# ── API ───────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def api_stats(db: Session = Depends(get_db)):
    clusters = db.query(NarrativeCluster).all()
    return {
        "total_articles": db.query(Article).count(),
        "analyzed_articles": db.query(Article).filter(Article.is_analyzed == True).count(),
        "clusters": len(clusters),
        "high_threat_clusters": sum(1 for c in clusters if c.threat_level == "HIGH"),
        "reports": db.query(IntelReport).count(),
    }
