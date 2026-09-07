import re
import math
import html
from collections import Counter
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher

import feedparser
import requests
import streamlit as st
from dateutil import parser as dateparser


st.set_page_config(
    page_title="Tech Week 5",
    page_icon="⚡",
    layout="centered",
)

SOURCES = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "WIRED": "https://www.wired.com/feed/rss",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "BBC Technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
}

FALLBACK_FEED = (
    "https://news.google.com/rss/search?"
    "q=technology%20when%3A7d&hl=en-US&gl=US&ceid=US%3Aen"
)

STOPWORDS = {
    "the","a","an","and","or","to","of","in","on","for","with","from","at","by",
    "is","are","be","as","its","it","this","that","these","those","new","says",
    "will","has","have","had","after","before","about","into","over","under",
    "your","you","we","our","their","they","he","she","his","her","more","how",
    "why","what","when","where","which","who","can","could","would","should",
    "tech","technology","latest","report","reports","reportedly"
}

IMPACT_TERMS = {
    "ai": 1.6,
    "artificial intelligence": 1.6,
    "openai": 1.2,
    "google": 0.8,
    "apple": 0.8,
    "microsoft": 0.8,
    "meta": 0.8,
    "amazon": 0.8,
    "nvidia": 1.0,
    "chip": 1.0,
    "chips": 1.0,
    "semiconductor": 1.1,
    "cybersecurity": 1.2,
    "breach": 1.4,
    "hack": 1.1,
    "ransomware": 1.5,
    "regulation": 1.2,
    "regulator": 1.0,
    "ban": 1.2,
    "antitrust": 1.4,
    "lawsuit": 1.0,
    "acquisition": 1.4,
    "acquires": 1.4,
    "merger": 1.4,
    "ipo": 1.2,
    "launch": 0.7,
    "released": 0.7,
    "robot": 0.8,
    "robotics": 0.9,
    "quantum": 1.0,
    "space": 0.7,
    "satellite": 0.7,
}

TOPIC_RULES = [
    ("IA", [" ai ", "artificial intelligence", "openai", "model", "llm", "chatgpt"]),
    ("Ciberseguridad", ["cyber", "breach", "hack", "ransomware", "malware", "security"]),
    ("Chips", ["chip", "semiconductor", "nvidia", "gpu", "processor"]),
    ("Regulación", ["regulation", "regulator", "ban", "antitrust", "lawsuit", "court"]),
    ("Big Tech", ["apple", "google", "microsoft", "meta", "amazon"]),
    ("Startups", ["startup", "funding", "venture", "acquisition", "ipo"]),
    ("Hardware", ["device", "phone", "laptop", "hardware", "robot", "wearable"]),
    ("Espacio", ["space", "satellite", "rocket", "nasa", "spacex"]),
]


def clean_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_date(entry):
    candidates = [
        entry.get("published"),
        entry.get("updated"),
        entry.get("created"),
    ]
    for value in candidates:
        if not value:
            continue
        try:
            dt = dateparser.parse(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
    return None


def tokens(title):
    words = re.findall(r"[a-z0-9][a-z0-9\-]+", title.lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def similarity(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    jaccard = len(ta & tb) / len(ta | tb)
    seq = SequenceMatcher(None, a.lower(), b.lower()).ratio()
    return max(jaccard, seq * 0.60)


def impact_score(text):
    t = f" {text.lower()} "
    score = 0.0
    for term, weight in IMPACT_TERMS.items():
        if term in t:
            score += weight
    return min(score, 4.0)


def topic_for(text):
    t = f" {text.lower()} "
    scores = []
    for topic, kws in TOPIC_RULES:
        hits = sum(1 for kw in kws if kw in t)
        if hits:
            scores.append((hits, topic))
    return max(scores)[1] if scores else "Tecnología"


def why_it_matters(topic, source_count):
    reach = (
        f"La historia aparece en {source_count} fuentes distintas, una señal de que está marcando la agenda tecnológica."
        if source_count > 1
        else "Destaca por su combinación de actualidad e impacto potencial."
    )
    reasons = {
        "IA": "Puede cambiar capacidades, productos o competencia dentro del ecosistema de inteligencia artificial.",
        "Ciberseguridad": "Puede afectar riesgo empresarial, privacidad, infraestructura o confianza digital.",
        "Chips": "Los semiconductores condicionan la carrera de IA, hardware, centros de datos y cadenas de suministro.",
        "Regulación": "Puede modificar las reglas con las que operan plataformas, desarrolladores y grandes tecnológicas.",
        "Big Tech": "Los movimientos de las grandes plataformas suelen tener efectos inmediatos sobre usuarios, desarrolladores y mercados.",
        "Startups": "Puede señalar hacia dónde se está moviendo el capital, la innovación y la próxima ola de productos.",
        "Hardware": "Puede anticipar cambios en la forma en que usamos dispositivos y servicios digitales.",
        "Espacio": "Puede tener implicaciones para conectividad, ciencia, defensa o infraestructura espacial.",
        "Tecnología": "Tiene potencial de mover productos, empresas o comportamientos dentro del sector tecnológico.",
    }
    return f"{reasons.get(topic, reasons['Tecnología'])} {reach}"


@st.cache_data(ttl=1800, show_spinner=False)
def load_feed(source_name, url):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; TechWeek5/1.0; +https://streamlit.io)"
    }
    response = requests.get(url, headers=headers, timeout=12)
    response.raise_for_status()
    parsed = feedparser.parse(response.content)

    items = []
    for entry in parsed.entries[:60]:
        title = clean_html(entry.get("title", ""))
        link = entry.get("link", "")
        summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
        dt = parse_date(entry)

        if not title or not link or not dt:
            continue

        items.append({
            "title": title,
            "link": link,
            "summary": summary,
            "published": dt,
            "source": source_name,
        })
    return items


def collect_articles(selected_sources):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    all_items = []
    errors = []

    for source in selected_sources:
        try:
            all_items.extend(load_feed(source, SOURCES[source]))
        except Exception:
            errors.append(source)

    recent = [
        x for x in all_items
        if cutoff <= x["published"] <= now + timedelta(hours=6)
    ]

    # If several feeds are unavailable, use Google News as a resilience fallback.
    if len(recent) < 12:
        try:
            fallback = load_feed("Google News", FALLBACK_FEED)
            recent.extend([
                x for x in fallback
                if cutoff <= x["published"] <= now + timedelta(hours=6)
            ])
        except Exception:
            pass

    # Exact-link/title dedupe
    seen = set()
    deduped = []
    for item in sorted(recent, key=lambda x: x["published"], reverse=True):
        key = re.sub(r"\W+", "", item["title"].lower())[:180]
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped, errors


def cluster_articles(articles):
    clusters = []

    for article in sorted(articles, key=lambda x: x["published"], reverse=True):
        best_idx = None
        best_sim = 0.0

        for i, cluster in enumerate(clusters):
            representative = cluster[0]["title"]
            sim = similarity(article["title"], representative)
            if sim > best_sim:
                best_sim = sim
                best_idx = i

        if best_idx is not None and best_sim >= 0.30:
            clusters[best_idx].append(article)
        else:
            clusters.append([article])

    return clusters


def score_cluster(cluster):
    now = datetime.now(timezone.utc)
    unique_sources = len({a["source"] for a in cluster})
    newest = max(a["published"] for a in cluster)
    age_days = max(0.0, (now - newest).total_seconds() / 86400)
    freshness = max(0.0, 1.0 - (age_days / 7.0))

    text = " ".join(a["title"] for a in cluster)
    impact = impact_score(text)

    # Cross-source confirmation is the strongest signal.
    source_signal = min(unique_sources, 5) * 2.5
    cluster_signal = min(len(cluster), 5) * 0.45

    return source_signal + cluster_signal + freshness * 1.8 + impact


def pick_representative(cluster):
    # Prefer the newest article from a named editorial source over fallback.
    ordered = sorted(
        cluster,
        key=lambda x: (
            x["source"] != "Google News",
            x["published"]
        ),
        reverse=True
    )
    return ordered[0]


def top_five(articles):
    clusters = cluster_articles(articles)
    ranked = sorted(clusters, key=score_cluster, reverse=True)

    results = []
    topic_counts = Counter()

    # First pass: favor editorial diversity (max 2 stories per topic).
    for cluster in ranked:
        representative = pick_representative(cluster)
        text = " ".join(a["title"] for a in cluster)
        topic = topic_for(text)
        if topic_counts[topic] >= 2:
            continue

        sources = sorted({a["source"] for a in cluster})
        representative = {**representative}
        representative["topic"] = topic
        representative["sources"] = sources
        representative["source_count"] = len(sources)
        representative["cluster_size"] = len(cluster)
        representative["score"] = score_cluster(cluster)
        representative["why"] = why_it_matters(topic, len(sources))
        results.append(representative)
        topic_counts[topic] += 1

        if len(results) == 5:
            break

    # Second pass in case diversity filtering left fewer than 5.
    if len(results) < 5:
        used_links = {r["link"] for r in results}
        for cluster in ranked:
            representative = pick_representative(cluster)
            if representative["link"] in used_links:
                continue
            text = " ".join(a["title"] for a in cluster)
            topic = topic_for(text)
            sources = sorted({a["source"] for a in cluster})
            representative = {**representative}
            representative["topic"] = topic
            representative["sources"] = sources
            representative["source_count"] = len(sources)
            representative["cluster_size"] = len(cluster)
            representative["score"] = score_cluster(cluster)
            representative["why"] = why_it_matters(topic, len(sources))
            results.append(representative)
            used_links.add(representative["link"])
            if len(results) == 5:
                break

    return results


st.markdown("""
<style>
    .block-container {max-width: 900px; padding-top: 2.2rem; padding-bottom: 3rem;}
    .eyebrow {font-size:.78rem; letter-spacing:.12em; text-transform:uppercase; opacity:.62; font-weight:700;}
    .hero-title {font-size:3.2rem; line-height:1; font-weight:850; letter-spacing:-.055em; margin:.25rem 0 .8rem 0;}
    .hero-copy {font-size:1.05rem; opacity:.76; max-width:700px; margin-bottom:1.4rem;}
    .news-card {
        border:1px solid rgba(128,128,128,.22);
        border-radius:18px;
        padding:1.15rem 1.2rem 1.05rem 1.2rem;
        margin:0 0 1rem 0;
    }
    .rank {font-size:.78rem; font-weight:800; opacity:.55; letter-spacing:.09em; text-transform:uppercase;}
    .news-title {font-size:1.32rem; line-height:1.25; font-weight:760; letter-spacing:-.015em; margin:.35rem 0 .45rem 0;}
    .meta {font-size:.82rem; opacity:.63; margin-bottom:.55rem;}
    .why {font-size:.94rem; line-height:1.5; opacity:.86;}
    .badge {
        display:inline-block; border:1px solid rgba(128,128,128,.32);
        border-radius:999px; padding:.18rem .55rem; font-size:.74rem;
        font-weight:700; margin-right:.35rem;
    }
    a {text-decoration:none;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="eyebrow">Radar semanal · tecnología global</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">Tech Week 5</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-copy">Cinco historias para entender qué movió el mundo tech esta semana, sin perderte entre cien titulares.</div>',
    unsafe_allow_html=True
)

with st.sidebar:
    st.header("Fuentes")
    selected = st.multiselect(
        "Medios incluidos",
        list(SOURCES.keys()),
        default=list(SOURCES.keys()),
    )
    st.caption("La selección se limita a publicaciones de los últimos 7 días.")
    if st.button("Actualizar ahora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if not selected:
    st.warning("Selecciona al menos una fuente en la barra lateral.")
    st.stop()

with st.spinner("Separando señal de ruido…"):
    articles, errors = collect_articles(selected)
    picks = top_five(articles)

if errors:
    st.caption("Algunas fuentes no respondieron en esta carga: " + ", ".join(errors) + ".")

if len(picks) < 5:
    st.warning(
        "No pude reunir cinco historias válidas de los últimos 7 días. "
        "Prueba a activar más fuentes o actualizar de nuevo."
    )

for i, item in enumerate(picks, 1):
    local_date = item["published"].astimezone().strftime("%d %b %Y")
    source_line = " · ".join(item["sources"])
    safe_title = html.escape(item["title"])
    safe_topic = html.escape(item["topic"])
    safe_source_line = html.escape(source_line)
    safe_why = html.escape(item["why"])
    summary = item["summary"]
    if summary and len(summary) > 260:
        summary = summary[:257].rsplit(" ", 1)[0] + "…"

    st.markdown(
        f"""
        <div class="news-card">
            <div class="rank">#{i} · {safe_topic}</div>
            <div class="news-title">{safe_title}</div>
            <div class="meta">{safe_source_line} · {local_date}</div>
            <div style="margin:.1rem 0 .65rem 0;">
                <span class="badge">{item['source_count']} fuente{"s" if item['source_count'] != 1 else ""}</span>
                <span class="badge">últimos 7 días</span>
            </div>
            <div class="why"><strong>Por qué importa:</strong> {safe_why}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    if summary:
        with st.expander("Ver contexto del feed"):
            st.write(summary)
    st.link_button("Leer noticia ↗", item["link"], use_container_width=True)

st.divider()
st.caption(
    "Ranking heurístico: coincidencia entre medios + actualidad + señales de impacto + diversidad temática. "
    "La app no copia artículos completos; enlaza a la publicación original."
)
