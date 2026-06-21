"""Collecteur Gmail via IMAP + mot de passe d'application.
Pas d'OAuth ni de Google Cloud : on se connecte en IMAP avec l'adresse Gmail
et un mot de passe d'application (16 caractères) généré sur
myaccount.google.com/apppasswords.
Lit les mails récents dont l'expéditeur correspond aux sources configurées.
"""
import os
import re
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timezone, timedelta

GMAIL_USER = os.environ.get("GMAIL_USER", "")        # ton adresse @gmail.com
GMAIL_APP_PWD = os.environ.get("GMAIL_APP_PWD", "")  # le mot de passe d'application (16 car.)
IMAP_HOST = "imap.gmail.com"


def _decode(s) -> str:
    if not s:
        return ""
    out = []
    for part, enc in decode_header(s):
        if isinstance(part, bytes):
            out.append(part.decode(enc or "utf-8", "ignore"))
        else:
            out.append(part)
    return "".join(out)


def _body_text(msg) -> str:
    """Extrait le texte d'un message email (plain d'abord, html en secours)."""
    plain, html = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if "attachment" in disp:
                continue
            try:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or "utf-8"
                text = payload.decode(charset, "ignore")
            except Exception:
                continue
            if ctype == "text/plain":
                plain += text
            elif ctype == "text/html":
                html += text
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            plain = payload.decode(charset, "ignore") if payload else ""
        except Exception:
            plain = ""
    raw = plain if plain.strip() else re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", raw).strip()


def collect(sources, since_hours: int = 168, max_per_source: int = 2):
    """sources = [{id, name, match (texte expéditeur), theme_hint}, ...]"""
    if not GMAIL_USER or not GMAIL_APP_PWD:
        print("Gmail: identifiants manquants (GMAIL_USER / GMAIL_APP_PWD)")
        return []
    try:
        imap = imaplib.IMAP4_SSL(IMAP_HOST)
        imap.login(GMAIL_USER, GMAIL_APP_PWD)
        imap.select("INBOX", readonly=True)
    except Exception as e:
        print("Gmail IMAP indisponible:", e)
        return []

    since = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).strftime("%d-%b-%Y")
    out = []
    for src in sources:
        # FROM filtre par fragment d'expéditeur ; SINCE borne la date
        crit = f'(FROM "{src["match"]}" SINCE {since})'
        try:
            typ, data = imap.search(None, crit)
        except Exception:
            continue
        if typ != "OK":
            continue
        ids = data[0].split()[-max_per_source:]
        for num in reversed(ids):
            typ, raw = imap.fetch(num, "(RFC822)")
            if typ != "OK" or not raw or not raw[0]:
                continue
            msg = email.message_from_bytes(raw[0][1])
            subject = _decode(msg.get("Subject")) or "(sans objet)"
            body = _body_text(msg)
            if len(body) < 60:
                continue
            try:
                dt = email.utils.parsedate_to_datetime(msg.get("Date"))
                published = dt.astimezone(timezone.utc).isoformat()
            except Exception:
                published = datetime.now(timezone.utc).isoformat()
            out.append({
                "source_type": "mail",
                "source_name": src["name"],
                "theme_hint": src.get("theme_hint", ""),
                "title": subject.strip(),
                "url": "https://mail.google.com/mail/u/0/#inbox",
                "published": published,
                "raw_text": body[:5000],
            })
    try:
        imap.logout()
    except Exception:
        pass
    return out
