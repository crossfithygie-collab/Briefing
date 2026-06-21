"""Résumeur — appelle Claude pour transformer le contenu brut en briefing.
Pour chaque item : titre court + résumé 2-3 lignes + thème + score d'importance.
Puis sélection du hero (item le plus important du jour, jugé librement par Claude)."""
import os
import json
import anthropic

MODEL = os.environ.get("BRIEFING_MODEL", "claude-sonnet-4-6")
# nettoie la clé de tout caractère parasite (espace, saut de ligne, caractères non-ASCII collés au copier-coller)
_raw_key = os.environ.get("ANTHROPIC_API_KEY", "")
_api_key = "".join(c for c in _raw_key.strip() if ord(c) < 128)
client = anthropic.Anthropic(api_key=_api_key)

THEMES = ["CrossFit", "Business", "Rétention", "Nutrition", "Coaching", "Société/Inspiration"]

SUMM_PROMPT = """Tu prépares un briefing quotidien pour Jérémy, gérant d'une salle de CrossFit.
Voici un contenu (mail, vidéo YouTube ou podcast). Résume-le pour son briefing.

Source : {source_type} — {source_name}
Titre original : {title}
Contenu :
{raw_text}

Réponds UNIQUEMENT en JSON, sans texte autour, avec ce format exact :
{{
  "titre": "titre reformulé court et clair (max 12 mots, en français)",
  "resume": "2 à 3 phrases qui vont à l'essentiel, ton direct, sans blabla ni formule creuse. Ce qui est actionnable ou à retenir d'abord.",
  "theme": "un seul thème parmi : {themes}",
  "importance": un entier de 1 à 10 (10 = à ne pas rater pour lui)
}}"""

HERO_NOTE = """Sois honnête sur l'importance : un vrai scoop CrossFit ou une info business directement
utile pour sa salle = 8-10. Un contenu sympa mais accessoire = 3-5. Du remplissage = 1-2."""


def summarize_item(item: dict) -> dict | None:
    prompt = SUMM_PROMPT.format(
        source_type=item["source_type"],
        source_name=item["source_name"],
        title=item["title"],
        raw_text=item["raw_text"][:2500],
        themes=", ".join(THEMES),
    ) + "\n\n" + HERO_NOTE
    try:
        resp = client.messages.create(
            model=MODEL, max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        txt = "".join(b.text for b in resp.content if b.type == "text")
        txt = txt.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(txt)
    except Exception as e:
        print("Résumé échoué pour", item["title"][:40], ":", e)
        return None
    # garde-fou thème
    theme = data.get("theme", "")
    if theme not in THEMES:
        theme = item.get("theme_hint") or "Société/Inspiration"
    return {
        **item,
        "titre": data.get("titre", item["title"])[:120],
        "resume": data.get("resume", ""),
        "theme": theme,
        "importance": int(data.get("importance", 5)),
    }


def build_briefing(raw_items: list[dict]) -> dict:
    """Résume tous les items, choisit le hero (importance la plus haute),
    renvoie {hero, items} triés."""
    summarized = []
    for it in raw_items:
        s = summarize_item(it)
        if s:
            summarized.append(s)
    if not summarized:
        return {"hero": None, "items": []}
    summarized.sort(key=lambda x: x["importance"], reverse=True)
    hero = summarized[0]
    return {"hero": hero, "items": summarized[1:]}


if __name__ == "__main__":
    # Test à sec si pas de clé
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Pas de clé ANTHROPIC_API_KEY — test sauté.")
    else:
        demo = [{
            "source_type": "podcast", "source_name": "LEGEND",
            "title": "Interview d'un entrepreneur", "theme_hint": "Société/Inspiration",
            "raw_text": "Un entrepreneur raconte comment il a bâti son réseau de salles de sport en partant de zéro, les erreurs de recrutement, la fidélisation des membres.",
        }]
        print(json.dumps(build_briefing(demo), ensure_ascii=False, indent=2))
