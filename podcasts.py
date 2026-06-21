"""Collecteur podcasts.
Résout un lien Apple Podcasts (ou un ID) vers le vrai flux RSS via l'API iTunes Lookup,
puis parse les épisodes récents. Résume à partir de la description de l'épisode
(pas de transcription audio en V1)."""
import re
import time
import requests
import feedparser
from datetime import datetime, timezone, timedelta

HEADERS = {"User-Agent": "Mozilla/5.0 (BriefingApp)"}


def apple_id_from_url(url: str) -> str | None:
    """Extrait l'ID numérique d'un lien Apple Podcasts."""
    m = re.search(r"id(\d+)", url or "")
    return m.group(1) if m else None


def resolve_feed_url(apple_url_or_id: str) -> str | None:
    """Lien/ID Apple Podcasts -> vrai feedUrl RSS via iTunes Lookup."""
    pid = apple_id_from_url(apple_url_or_id) or (apple_url_or_id if str(apple_url_or_id).isdigit() else None)
    if not pid:
        # Peut-être déjà un flux RSS direct
        return apple_url_or_id if str(apple_url_or_id).startswith("http") else None
    try:
        r = requests.get(f"https://itunes.apple.com/lookup?id={pid}", timeout=10).json()
        if r.get("results"):
            return r["results"][0].get("feedUrl")
    except Exception:
        return None
    return None


def _clean(html: str) -> str:
    """Nettoie le HTML des descriptions pour ne garder que le texte utile."""
    txt = re.sub(r"<[^>]+>", " ", html or "")
    txt = re.sub(r"\s+", " ", txt).strip()
    # Coupe les blocs promo récurrents (réseaux, partenariats)
    for marker in ["Pour toutes demandes", "Retrouvez-nous sur tous les réseaux",
                   "Hébergé par Acast", "Pour prendre vos billets"]:
        i = txt.find(marker)
        if i > 200:
            txt = txt[:i].strip()
    return txt


def collect(source: dict, since_hours: int = 36, max_items: int = 4) -> list[dict]:
    """Récupère les épisodes récents d'un podcast source.
    source = {id, name, rss (lien Apple ou RSS direct), theme_hint}"""
    feed_url = resolve_feed_url(source.get("rss", ""))
    if not feed_url:
        return []
    try:
        raw = requests.get(feed_url, headers=HEADERS, timeout=20).content
    except Exception:
        return []
    d = feedparser.parse(raw)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    out = []
    for e in d.entries[:max_items * 3]:
        pub = e.get("published_parsed") or e.get("updated_parsed")
        when = datetime.fromtimestamp(time.mktime(pub), tz=timezone.utc) if pub else None
        if when and when < cutoff:
            continue
        desc = _clean(e.get("summary", "") or e.get("description", ""))
        if len(desc) < 80:
            continue
        out.append({
            "source_type": "podcast",
            "source_name": source["name"],
            "theme_hint": source.get("theme_hint", ""),
            "title": e.get("title", "").strip(),
            "url": e.get("link", feed_url),
            "published": when.isoformat() if when else "",
            "raw_text": desc[:4000],
            "duration": e.get("itunes_duration", ""),
        })
        if len(out) >= max_items:
            break
    return out


if __name__ == "__main__":
    test = {"id": "legend", "name": "LEGEND",
            "rss": "https://podcasts.apple.com/fr/podcast/legend/id1691740320",
            "theme_hint": "Société/Inspiration"}
    items = collect(test)
    print(f"{len(items)} épisodes récupérés")
    for it in items:
        print("-", it["title"][:55], "|", len(it["raw_text"]), "car.")
