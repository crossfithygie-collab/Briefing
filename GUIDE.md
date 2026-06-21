# 📱 Briefing — Guide de mise en route (100% iPhone, dans Safari)

Tout se fait depuis Safari sur ton iPhone. Compte ~1h la première fois.
Après, tu n'y reviens plus : l'app vit sur ton écran d'accueil et se met à jour 2×/jour toute seule.

Tu auras besoin, dans l'ordre :
1. Un mot de passe d'application Gmail (16 caractères)
2. Une clé API Anthropic
3. Une clé API YouTube
4. Un compte GitHub (héberge le code)
5. Un compte Render (héberge le serveur, gratuit)

---

## Étape 1 — Mot de passe d'application Gmail (5 min)

1. Safari → **myaccount.google.com/apppasswords**
2. Si bloqué : active d'abord la validation en 2 étapes sur **myaccount.google.com/security**
3. Nom de l'app : **Briefing** → **Créer**
4. Note le code à **16 caractères** (sans les espaces) dans tes Notes
   → c'est ton `GMAIL_APP_PWD`

⚠️ Ne le partage avec personne. Tu le colleras seulement dans Render (étape 5).

---

## Étape 2 — Clé API Anthropic (5 min)

1. Safari → **console.anthropic.com** → crée un compte / connecte-toi
2. Ajoute un moyen de paiement et mets un petit crédit (5 € suffisent pour des mois)
3. **API Keys** → **Create Key** → nomme-la "Briefing"
4. Copie la clé `sk-ant-...` → note-la
   → c'est ton `ANTHROPIC_API_KEY`

---

## Étape 3 — Clé API YouTube (5 min)

Réutilise le projet Google Cloud que tu as déjà (celui du cockpit).

1. Safari → **console.cloud.google.com**
2. Sélectionne ton projet existant en haut
3. **APIs & Services → Library** → cherche **YouTube Data API v3** → **Enable**
4. **APIs & Services → Credentials → Create Credentials → API Key**
5. Copie la clé `AIza...` → note-la
   → c'est ton `YOUTUBE_API_KEY`

---

## Étape 4 — Mettre le code sur GitHub (15 min)

1. Safari → **github.com** → crée un compte (ou connecte-toi)
2. **+ (en haut à droite) → New repository**
3. Nom : `briefing` — coche **Private** — **Create repository**
4. Sur la page du dépôt vide : **uploading an existing file**
5. Décompresse le zip `briefing.zip` sur ton iPhone (Fichiers → appui long → Décompresser)
6. Glisse TOUS les fichiers/dossiers du projet dans la zone d'upload GitHub
   (app.py, requirements.txt, config.json, summarizer.py, store.py, Procfile,
    render.yaml, le dossier collectors/, le dossier web/)
7. **Commit changes**

---

## Étape 5 — Déployer sur Render (15 min)

1. Safari → **render.com** → **Get Started** → connecte-toi **avec GitHub**
2. **New + → Web Service**
3. Autorise Render à voir ton dépôt `briefing` → sélectionne-le
4. Render lit le `render.yaml` automatiquement. Vérifie :
   - Runtime : **Python**
   - Build : `pip install -r requirements.txt`
   - Start : `gunicorn app:app`
   - Plan : **Free**
5. **Environment** → ajoute tes variables (une par une, "Add Environment Variable") :

   | Key | Value |
   |---|---|
   | `ANTHROPIC_API_KEY` | ta clé sk-ant-... |
   | `GMAIL_USER` | tonadresse@gmail.com |
   | `GMAIL_APP_PWD` | ton code 16 caractères |
   | `YOUTUBE_API_KEY` | ta clé AIza... |
   | `COLLECT_TOKEN` | invente un mot de passe au hasard |

6. **Create Web Service** → attends ~3 min que ça build
7. Render te donne une URL type `https://briefing-hygie.onrender.com`
   → ouvre-la dans Safari : ton app apparaît 🎉

---

## Étape 6 — Lancer la 1re collecte

Dans Safari, ouvre :
```
https://TON-URL.onrender.com/api/collect?token=TON_COLLECT_TOKEN
```
(remplace TON-URL et TON_COLLECT_TOKEN)

Ça va chercher tes mails + Mayhem + LEGEND, résume, et remplit le briefing.
Recharge la page d'accueil : le feed est rempli.

---

## Étape 7 — Collecte automatique 2×/jour

Render Free met le serveur en veille, donc on le réveille avec un cron gratuit externe.

1. Safari → **cron-job.org** → crée un compte gratuit
2. **Create cronjob**
   - URL : `https://TON-URL.onrender.com/api/collect?token=TON_COLLECT_TOKEN`
   - Schedule : tous les jours à **07:00** → crée
3. Refais-en un deuxième pour **19:00**

C'est tout. Tes 2 briefings quotidiens se construisent seuls.

---

## Étape 8 — Mettre l'app sur l'écran d'accueil

1. Ouvre `https://TON-URL.onrender.com` dans Safari
2. Bouton **Partager** (carré + flèche) → **Sur l'écran d'accueil**
3. Nomme-la "Briefing" → **Ajouter**

Tu as maintenant une icône comme une vraie app, plein écran. 🚀

---

## Ajouter une source plus tard

Depuis l'app → **Réglages**. (L'édition complète des sources depuis l'app
arrive ; en attendant tu peux modifier `config.json` sur GitHub et Render
redéploie tout seul.)

## Notes
- Coût : quelques centimes/jour d'API Anthropic, le reste est gratuit.
- Render Free peut être lent au 1er chargement (réveil du serveur) : normal.
- LEGEND est volumineux : on résume la description de l'épisode, pas l'audio.
