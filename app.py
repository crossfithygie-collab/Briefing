"""Backend Briefing — Flask.
Expose l'API consommée par la PWA iPhone, et lance la collecte 2x/jour.

Routes :
  GET  /api/briefing          -> {hero, items}
  GET  /api/saved             -> [items sauvegardés]
  POST /api/save              -> sauvegarde un item {payload}
  POST /api/unsave            -> retire un item {uid}
  GET  /api/sources           -> config des sources
  POST /api/sources           -> met à jour la config
  POST /api/collect           -> déclenche une collecte manuelle (protégée par token)
  GET  /api/health            -> ok
  GET  /                      -> sert la PWA
"""
import os
import json
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import store
from summarizer import build_briefing
import gmail, youtube, podcasts

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

COLLECT_TOKEN = os.environ.get("COLLECT_TOKEN", "")  # protège le déclenchement de collecte


# ---------------- collecte ----------------
def run_collection():
    cfg = store.load_sources()
    raw = []
    # Mails
    try:
        m = gmail.collect(cfg["sources"].get("mail", []))
        print(f"[mail] {len(m)} items")
        raw += m
    except Exception as e:
        import traceback; print("collect mail ERREUR:", e); traceback.print_exc()
    # YouTube
    for src in cfg["sources"].get("youtube", []):
        try:
            got = youtube.collect(src)
            print(f"[yt] {src.get('name')}: {len(got)} items (channel_id={src.get('channel_id')})")
            raw += got
            if src.get("channel_id"):
                store.save_sources(cfg)
        except Exception as e:
            import traceback; print("collect yt ERREUR:", e); traceback.print_exc()
    # Podcasts
    for src in cfg["sources"].get("podcast", []):
        try:
            p = podcasts.collect(src)
            print(f"[pod] {src.get('name')}: {len(p)} items")
            raw += p
        except Exception as e:
            import traceback; print("collect pod ERREUR:", e); traceback.print_exc()

    print(f"[collecte] {len(raw)} items bruts récupérés")
    if not raw:
        return {"collected": 0, "detail": "aucun item — voir logs"}
    briefing = build_briefing(raw)
    store.replace_today(briefing)
    n = (1 if briefing.get("hero") else 0) + len(briefing.get("items", []))
    print(f"[collecte] briefing reconstruit : {n} items")
    return {"collected": n}


# ---------------- API ----------------
@app.get("/api/health")
def health():
    return jsonify(ok=True)


@app.get("/api/briefing")
def api_briefing():
    return jsonify(store.get_briefing())


@app.get("/api/saved")
def api_saved():
    return jsonify(store.get_saved())


@app.post("/api/save")
def api_save():
    store.save_item(request.json)
    return jsonify(ok=True)


@app.post("/api/unsave")
def api_unsave():
    store.unsave_item(request.json.get("uid", ""))
    return jsonify(ok=True)


@app.get("/api/sources")
def api_sources_get():
    return jsonify(store.load_sources())


@app.post("/api/sources")
def api_sources_set():
    store.save_sources(request.json)
    return jsonify(ok=True)


@app.route("/api/collect", methods=["GET", "POST"])
def api_collect():
    # déclenchement manuel (clic Safari = GET) ou par cron externe : protégé par token
    if COLLECT_TOKEN:
        sent = request.headers.get("X-Collect-Token") or request.args.get("token", "")
        if sent != COLLECT_TOKEN:
            return jsonify(error="unauthorized"), 401
    return jsonify(run_collection())


@app.post("/api/add")
def api_add():
    """Ajout manuel : résume un contenu collé et l'insère dans le briefing courant."""
    data = request.json or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify(error="empty"), 400
    t = data.get("type", "mail")
    stype = {"yt": "youtube", "pod": "podcast", "mail": "mail"}.get(t, "mail")
    raw = {
        "source_type": stype,
        "source_name": {"youtube": "YouTube", "podcast": "Podcast", "mail": "Mail"}[stype],
        "theme_hint": "",
        "title": content[:60],
        "url": data.get("url", ""),
        "published": "",
        "raw_text": content,
    }
    from summarizer import summarize_item
    s = summarize_item(raw)
    if not s:
        return jsonify(error="summarize_failed"), 500
    # insère dans le briefing existant
    current = store.get_briefing()
    items_list = []
    if current.get("hero"):
        items_list.append(current["hero"])
    items_list += current.get("items", [])
    # normalise les clés du nouvel item
    s["thumbnail"] = s.get("thumbnail", "")
    items_list.insert(0, s)
    # recalcule le hero par importance
    items_list.sort(key=lambda x: x.get("importance", 5), reverse=True)
    briefing = {"hero": items_list[0], "items": items_list[1:]}
    store.replace_today(briefing)
    return jsonify(ok=True)


@app.route("/api/reload-config", methods=["GET", "POST"])
def api_reload_config():
    """Force le rechargement de config.json dans la base (efface l'ancienne config figée)."""
    if COLLECT_TOKEN:
        sent = request.headers.get("X-Collect-Token") or request.args.get("token", "")
        if sent != COLLECT_TOKEN:
            return jsonify(error="unauthorized"), 401
    with open("config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    store.save_sources(cfg)
    return jsonify(ok=True, reloaded=True)


@app.get("/")
def root():
    return send_from_directory(".", "index.html")


# ---------------- scheduler ----------------
# ---------------- scheduler ----------------
def start_scheduler():
    """Collecte 2x/jour. Activé seulement si ENABLE_SCHEDULER=1
    (sur Render Free, mieux vaut un cron externe qui ping /api/collect)."""
    if os.environ.get("ENABLE_SCHEDULER") != "1":
        return
    from apscheduler.schedulers.background import BackgroundScheduler
    cfg = store.load_sources()
    times = cfg.get("collect_times", ["07:00", "19:00"])
    sched = BackgroundScheduler(timezone="Europe/Paris")
    for t in times:
        h, m = t.split(":")
        sched.add_job(run_collection, "cron", hour=int(h), minute=int(m))
    sched.start()
    print("Scheduler actif :", times)


store.init()
start_scheduler()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5060))
    app.run(host="0.0.0.0", port=port, debug=True)
