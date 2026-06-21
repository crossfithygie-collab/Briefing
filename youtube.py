"""Collecteur YouTube.
Utilise le flux RSS public d'une chaîne (pas de quota API) pour les dernières vidéos,
et youtube-transcript-api pour le contenu. La clé YouTube Data API sert uniquement à
résoudre un nom de chaîne -> channel_id la première fois (puis on met en cache dans config)."""
import re
import os
import time
import requests
import feedparser
from datetime import datetime, timezone, timedelta

HEADERS = {"User-Agent": "Mozilla/5.0 (BriefingApp)"}
YT_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

CHANNEL_FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={cid}"


def resolve_channel_id(name_or_url: str) -> str | None:
    """Nom de chaîne ou URL -> channel_id.
    Essaie d'abord l'extraction directe depuis une URL, sinon l'API Data si une clé est dispo."""
    s = name_or_url or ""
    m = re.search(r"channel/(UC[\w-]{22})", s)
    if m:
        return m.group(1)
    if YT_API_KEY:
        try:
            r = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={"part": "snippet", "q": s, "type": "channel",
                        "maxResults": 1, "key": YT_API_KEY},
                timeout=10).json()
            items = r.get("items", [])
            if items:
                return items[0]["snippet"]["channelId"]
        except Exception:
            return None
    return None


def _get_transcript(video_id: str) -> str:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        for langs in (["fr"], ["en"], None):
            try:
                tr = YouTubeTranscriptApi.get_transcript(video_id, languages=langs) if langs \
                    else YouTubeTranscriptApi.get_transcript(video_id)
                return " ".join(seg["text"] for seg in tr)[:6000]
            except Exception:
                continue
    except Exception:
        pass
    return ""


def collect(source: dict, since_hours: int = 36, max_items: int = 3) -> list[dict]:
    """source = {id, name, channel, channel_id (cache), theme_hint}"""
    cid = source.get("channel_id") or resolve_channel_id(source.get("channel") or source.get("name"))
    if not cid:
        return []
    source["channel_id"] = cid  # caché par l'appelant dans config
    try:
        raw = requests.get(CHANNEL_FEED.format(cid=cid), headers=HEADERS, timeout=15).content
    except Exception:
        return []
    d = feedparser.parse(raw)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    out = []
    for e in d.entries[:max_items * 2]:
        pub = e.get("published_parsed")
        when = datetime.fromtimestamp(time.mktime(pub), tz=timezone.utc) if pub else None
        if when and when < cutoff:
            continue
        vid = e.get("yt_videoid") or ""
        desc = ""
        if hasattr(e, "media_description"):
            desc = e.media_description or ""
        transcript = _get_transcript(vid) if vid else ""
        body = transcript or desc
        if len(body) < 60:
            body = (desc or e.get("title", ""))
        out.append({
            "source_type": "youtube",
            "source_name": source["name"],
            "theme_hint": source.get("theme_hint", ""),
            "title": e.get("title", "").strip(),
            "url": e.get("link", f"https://youtu.be/{vid}"),
            "published": when.isoformat() if when else "",
            "raw_text": body[:6000],
            "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else "",
        })
        if len(out) >= max_items:
            break
    return out


if __name__ == "__main__":
    test = {"id": "mayhem", "name": "Mayhem CrossFit",
            "channel": "Mayhem CrossFit", "channel_id": "", "theme_hint": "CrossFit"}
    items = collect(test)
    print(f"{len(items)} vidéos | channel_id résolu: {test['channel_id']}")
    for it in items:
        print("-", it["title"][:55], "| texte", len(it["raw_text"]), "car.")
