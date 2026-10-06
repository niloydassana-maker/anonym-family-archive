"""Contact provenance and buyer-intent signals for the public-web hunt.

Public contact details are retained with their source and channel type. A repo
similarity score is not purchase intent, and an MX/SMTP acceptance is not proof
that a person received or read a message.
"""
import html
import re
import urllib.parse

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
MAILTO_RE = re.compile(r"(?i)mailto:([^\"'<>\s?#]+)")
FREE_MAIL = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.in", "hotmail.com",
    "outlook.com", "live.com", "icloud.com", "protonmail.com", "proton.me",
    "aol.com", "gmx.com", "mail.com", "zoho.com",
}
ROLE_LOCAL = re.compile(
    r"^(info|hello|contact|sales|team|support|business|partnerships|press|office|admin|careers|jobs)$",
    re.I,
)
BAD_EMAIL = re.compile(
    r"(noreply|no-reply|donotreply|example\.|test@|sentry|wixpress|"
    r"@(domain|email|example|yourdomain)\.)",
    re.I,
)

# Require an explicit request for a solution or provider. Company descriptions,
# product marketing, hiring pages, and repo similarity alone do not qualify.
NEED_RE = re.compile(
    r"\b(?:i|we|our team)\s+(?:am |are )?(?:looking for|seeking|need(?: help with)?|"
    r"want to hire|cannot find|can't find|struggling with)\b[^.!?\n]{0,180}\b"
    r"(?:developer|engineer|agency|prototype|mvp|app|software|automation|dataset|"
    r"training data|voice assistant|receptionist|integration|consultant|vendor|tool)\b",
    re.I,
)
ADVICE_RE = re.compile(
    r"\b(?:looking for a technical cofounder|need an? (?:mvp|developer|engineer|"
    r"dataset|prototype)|seeking an? (?:agency|developer|vendor)|anyone know a good "
    r"(?:developer|agency|tool)|can someone recommend (?:a |an )?(?:developer|agency|tool))\b",
    re.I,
)


def _host(url):
    return (urllib.parse.urlsplit(url or "").hostname or "").lower().strip(".")


def _first_party(email_domain, host):
    email_domain = (email_domain or "").lower().strip(".")
    host = (host or "").lower().strip(".")
    return bool(email_domain and host and (
        email_domain == host or host.endswith("." + email_domain)
        or email_domain.endswith("." + host)
    ))


def extract_public_emails(markup, page_url):
    """Extract addresses disclosed on the organization's own public site.

    Each result has provenance. Third-party addresses embedded in comments,
    widgets, or quoted content are excluded; free-mail addresses remain review-only.
    """
    if not markup:
        return []
    host = _host(page_url)
    raw = html.unescape(markup)
    candidates = {}
    for match in MAILTO_RE.finditer(raw):
        value = urllib.parse.unquote(match.group(1)).split(",", 1)[0].lower()
        for email in EMAIL_RE.findall(value):
            candidates.setdefault(email.strip(".-"), set()).add("mailto")

    # Read visible text when BeautifulSoup is available. The fallback strips tags
    # conservatively; matching raw script/style blocks is intentionally avoided.
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw, "html.parser")
        for node in soup(["script", "style", "noscript", "svg"]):
            node.decompose()
        visible = soup.get_text(" ", strip=True)
    except Exception:
        visible = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", raw)
        visible = re.sub(r"<[^>]+>", " ", visible)

    visible = re.sub(r"(?i)\s*\[at\]\s*|\s*\(at\)\s*|\s+at\s+", "@", visible)
    visible = re.sub(r"(?i)\s*\[dot\]\s*|\s*\(dot\)\s*|\s+dot\s+", ".", visible)
    for email in EMAIL_RE.findall(visible.lower()):
        candidates.setdefault(email.strip(".-"), set()).add("visible-text")

    out = []
    for email, sources in sorted(candidates.items()):
        if len(email) > 254 or BAD_EMAIL.search(email) or email.count("@") != 1:
            continue
        local, domain = email.rsplit("@", 1)
        if len(local) > 64 or not domain or "." not in domain:
            continue
        if not _first_party(domain, host) and domain not in FREE_MAIL:
            continue
        personal = domain in FREE_MAIL
        out.append({
            "email": email,
            "provenance": "public-personal-review" if personal else "official-domain-public",
            "kind": "personal" if personal else ("role" if ROLE_LOCAL.match(local) else "direct"),
            "source": "+".join(sorted(sources)),
            "send_gate": "HOLD" if personal else "DELIVERY_UNCONFIRMED",
        })
    return out


def buyer_intent(text):
    """Return (status, exact evidence) without conflating fit with buying intent."""
    clean = re.sub(r"\s+", " ", text or "").strip()
    for rx in (NEED_RE, ADVICE_RE):
        match = rx.search(clean)
        if match:
            return "EXPLICIT_NEED", match.group(0)[:240]
    return "NO_EXPLICIT_NEED", ""
