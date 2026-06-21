# Briefing — app perso de veille (CrossFit / Business)

Agrège mails (Morning Chalk Up, CrossFit), YouTube (Mayhem CrossFit) et
podcasts (LEGEND), les résume avec Claude et les classe par thème.
Backend Flask + PWA iPhone. Collecte auto 2×/jour.

👉 Pour tout installer depuis ton iPhone : voir **GUIDE.md**

## Structure
- `app.py` — serveur Flask + API + scheduler
- `collectors/` — gmail (IMAP), youtube (RSS), podcasts (RSS via iTunes)
- `summarizer.py` — résumé + thème + score via Claude
- `store.py` — base SQLite (briefing, sauvegardés, sources)
- `web/index.html` — la PWA
