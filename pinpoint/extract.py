"""Conservative HTML extraction. Profiles are accepted only with body evidence."""

import hashlib
import json
import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Comment

from pinpoint.config import FIRMS

PROFILE_PATHS = {
    "kirkland": r"^/lawyers/[a-z]/[^/]+/?$",
    "wachtell": r"^/attorney/[^/]+/?$",
    "quinn": r"^/attorneys/[^/]+/?$",
    "davispolk": r"^/lawyers/[^/]+/?$",
    "simpson": r"^/our-team/(?:partners/)?[^/]+/?$",
    "paulweiss": r"^/professionals/(?:partners-and-counsel/)?[^/]+/?$",
    "gibson": r"^/(?:lawyer|people)/[^/]+/?$",
    "latham": r"^/en/people/[^/]+/?$",
    "cravath": r"^/people/[^/]+(?:\.html)?/?$",
    "milbank": r"^/en/professionals/[^/]+\.html$",
    "sullivan": r"^/(?:lawyers|professionals)/[^/]+/?$",
    "paulhastings": r"^/professionals/[^/]+/?$",
    "skadden": r"^/professionals/[a-z]/[^/]+/?$",
    "king": r"^/people/[^/]+/?$",
    "weil": r"^/people/[^/]+/?$",
}
OFFICES = [
    "Abu Dhabi",
    "Amsterdam",
    "Atlanta",
    "Austin",
    "Beijing",
    "Berlin",
    "Boston",
    "Brussels",
    "Century City",
    "Charlotte",
    "Chicago",
    "Cologne",
    "Dallas",
    "Denver",
    "Dubai",
    "Dusseldorf",
    "Düsseldorf",
    "Frankfurt",
    "Hamburg",
    "Hong Kong",
    "Houston",
    "London",
    "Los Angeles",
    "Luxembourg",
    "Madrid",
    "Menlo Park",
    "Miami",
    "Milan",
    "Munich",
    "New York",
    "Orange County",
    "Palo Alto",
    "Paris",
    "Riyadh",
    "Rome",
    "Sacramento",
    "San Diego",
    "San Francisco",
    "São Paulo",
    "Sao Paulo",
    "Seoul",
    "Shanghai",
    "Silicon Valley",
    "Singapore",
    "Tokyo",
    "Washington, D.C.",
    "Washington, DC",
    "Washington D.C.",
    "Washington, D.C",
    "Washington DC",
    "Wilmington",
]
CHALLENGE = re.compile(
    r"verify (?:that )?you are human|access denied|just a moment\.\.\.|checking your browser", re.I
)


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def official_url(firm_id, url):
    parsed = urlsplit(url)
    domain = urlsplit(FIRMS[firm_id]["base"]).hostname.removeprefix("www.")
    return (
        parsed.scheme == "https"
        and parsed.hostname in {domain, "www." + domain}
        and parsed.port in {None, 443}
        and not parsed.username
        and not parsed.password
    )


def is_profile_url(firm_id, url):
    if (
        urlsplit(url)
        .path.lower()
        .endswith((".vcf", ".pdf", ".png", ".jpg", ".jpeg", ".json", ".zip"))
    ):
        return False
    return official_url(firm_id, url) and bool(
        re.match(PROFILE_PATHS[firm_id], urlsplit(url).path, re.I)
    )


def profile_links(firm_id, base, html):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.select("a[href]"):
        url = urlsplit(urljoin(base, a["href"]))
        normal = urlunsplit((url.scheme, url.netloc, url.path, "", ""))
        if is_profile_url(firm_id, normal):
            links.add(normal)
    return sorted(links)


def extract_profile(firm_id, url, html, observed_at):
    if not is_profile_url(firm_id, url):
        return None
    soup = BeautifulSoup(html, "html.parser")
    if firm_id == "milbank":
        for node in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(node.string or node.get_text())
                people = [p for p in data.get("@graph", []) if p.get("@type") == "Person"]
                if people and people[0].get("knowsAbout"):
                    labels = " ".join(people[0]["knowsAbout"])
                    if not re.search(r"corporate|mergers|M&A", labels, re.I):
                        return None
            except (ValueError, TypeError, AttributeError):
                pass
    for node in soup.select(
        'script,style,nav,footer,noscript,[role="navigation"],.breadcrumb,.breadcrumbs,.wp-card'
    ):
        node.decompose()
    for node in soup.select("body > header, .site-header, .main-header"):
        node.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    body = (
        soup.select_one('main, [role="main"], #main, #content, .main-content') or soup.body or soup
    )
    text = clean(body.get_text(" ", strip=True))
    if CHALLENGE.search(text[:1000]):
        return None
    heading = body.select_one("h1, .stb-article-block__heading") or soup.select_one("h1")
    if not heading:
        return None
    name = clean(heading.get_text(" ", strip=True))
    if not (3 <= len(name) <= 90) or len(name.split()) < 2:
        return None
    if any(
        x in name.casefold()
        for x in ["our team", "professionals", "access denied", "people search"]
    ):
        return None
    # Prefer role near the profile heading. A former partner in narrative must not
    # promote a counsel or associate into the dataset.
    # Find the actual heading text rather than a featured-news mention of the name.
    following = clean(" ".join(str(t) for t in heading.find_all_next(string=True)))
    role_lead = name + " " + following[:400]
    role = re.search(r"\b(partner|counsel|associate|retired)\b", role_lead, re.I)
    if not role or role.group(1).lower() != "partner":
        return None
    practices = []
    # Practice links are stronger evidence than words in news/deal descriptions.
    practice_labels = " ".join(
        a.get_text(" ", strip=True)
        for a in body.select("a[href]")
        if any(
            x in a["href"].lower()
            for x in ["/practices/", "/practice-areas/", "/practice/", "/capabilities/"]
        )
    )
    scope_text = practice_labels + " " + text[:3500]
    ma_pattern = r"\bmergers?\s*(?:&|and)\s*acquisitions?\b(?!\s+(?:litigation|disputes))|\bM&A\b(?!\s+(?:litigation|disputes))"
    corp_pattern = r"\bcorporate(?:\s+(?:department|group|practice|partner|finance|governance)|/M&A)\b|\bPartner\s*,?\s*Corporate\b"
    ma = re.search(ma_pattern, scope_text, re.I)
    corp = re.search(corp_pattern, scope_text, re.I) or re.search(
        r"\bCorporate\b(?!\s+Tax)", practice_labels
    )
    adjacent = re.search(
        r"(?:M&A|Mergers?\s*(?:&|and)\s*Acquisitions?)\s+Litigation", scope_text, re.I
    )
    if firm_id == "quinn":
        # Quinn is litigation-focused. Capture explicitly labelled M&A litigation
        # separately; a corporate dispute alone is not a corporate practice.
        if not adjacent:
            return None
        ma = corp = None
        practices.append("M&A Litigation (adjacent)")
    if ma:
        practices.append("Mergers & Acquisitions")
    if corp:
        practices.append("Corporate")
    if not practices:
        return None
    # Office membership comes from profile contact/location elements only, never
    # from deals, education or global navigation.
    locations = []
    location_tokens = []
    for node in body.select(
        '[class*="office"], [class*="location"], [class*="contact"], [itemprop="address"], .wp-profile-wrapper, .header-b'
    ):
        if len(node.get_text(" ", strip=True)) < 1600:
            locations.append(node.get_text(" ", strip=True))
            location_tokens.extend(clean(t) for t in node.stripped_strings)
    location_text = " ".join(locations)
    offices = [
        office for office in OFFICES if office.casefold() in {t.casefold() for t in location_tokens}
    ]
    offices = sorted(set("Washington, D.C." if o.startswith("Washington") else o for o in offices))
    paragraphs = [clean(p.get_text(" ", strip=True)) for p in body.select("p")]
    bio = next(
        (
            p
            for p in paragraphs
            if len(p) > 80
            and re.search(r"\b(partner|advises|represents|practice|focuses)\b", p, re.I)
        ),
        "",
    )
    summary = bio[:400] if bio else ""
    # Minimal excerpts support title/practice; retain full HTML privately for repeatable debugging.
    snippets = [role_lead[:200]]
    if practice_labels:
        snippets.append("Profile practice labels: " + practice_labels[:220])
    for match in [ma, corp, adjacent]:
        if match:
            snippets.append(scope_text[max(0, match.start() - 60) : match.end() + 120])
    evidence = " | ".join(dict.fromkeys(snippets))[:650]
    return dict(
        firm_id=firm_id,
        source_url=url,
        name=name,
        title="Partner",
        practices=practices,
        offices=offices,
        summary=summary,
        evidence=evidence,
        office_evidence=clean(location_text)[:700] if offices else "",
        content_hash=hashlib.sha256(html.encode()).hexdigest(),
        observed_at=observed_at,
        extraction_version="2",
        verification="official_profile",
        scope_note="Practice evidence; review practice fit before outreach",
    )
