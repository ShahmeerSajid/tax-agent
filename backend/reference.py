"""
This file answers two kinds of questions without any calculation: "what is the
official figure for X" and "is this source link trustworthy". The first,
verified_parameters(), returns the figures stored in
data/tax_parameters_2026.json (RRSP limits, TFSA limits, CPP, CPP2, EI and the
capital gains inclusion rate) exactly as stored, with the official pages they
came from. The second, verify_source(), checks a link against two things: an
allowlist of official government domains, and the list of source links that are
actually stored in our rules and parameters.

We need this because of two rules of the project: the AI must never invent a
tax figure, and it must never invent a citation. When Gemini wants to cite a
page or quote a limit, it can call these tools and get the stored answer, or
learn that the link is not one we hold. Verification here is honest about its
reach: it does not open the web page, so "official domain" means the address
belongs to an official site, and "stored source" means we recorded that exact
page when we read the figures. It never says the page content was re-checked.
"""

from urllib.parse import urlparse

from backend.common import get_parameters, get_rules

OFFICIAL_DOMAINS = ("canada.ca", "gc.ca", "revenuquebec.ca")
TOPICS = ("rrsp", "tfsa", "cpp", "ei", "capital_gains")


def _normalize(url):
    parsed = urlparse(url.strip())
    return f"{parsed.scheme}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"


def _stored_sources():
    labels = {}
    rules = get_rules()
    for code, j in rules["jurisdictions"].items():
        labels.setdefault(_normalize(j["source_url"]), []).append(f"brackets:{code}")
    params = get_parameters()
    for topic in TOPICS:
        for url in params[topic]["source_urls"]:
            labels.setdefault(_normalize(url), []).append(f"parameters:{topic}")
    return labels


def verified_parameters(topic):
    key = topic.strip().lower() if isinstance(topic, str) else ""
    params = get_parameters()
    if key == "all":
        data = {t: params[t] for t in TOPICS}
    elif key in TOPICS:
        data = {key: params[key]}
    else:
        raise ValueError("Topic must be one of: rrsp, tfsa, cpp, ei, capital_gains, all")
    return {
        "result_type": "reference",
        "tax_year": params["tax_year"],
        "parameters": data,
        "note": params["note"],
    }


def verify_source(url):
    if not isinstance(url, str) or not url.strip():
        raise ValueError("A URL is required")
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        raise ValueError("The URL must start with https://")
    official = any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS)
    stored = _stored_sources().get(_normalize(url))
    if stored:
        status = "stored_source"
        message = "This exact page is one of the sources recorded in our rules or parameters."
    elif official:
        status = "official_domain_not_stored"
        message = (
            "The address belongs to an official government domain, but this page is not one "
            "we recorded. Do not cite it for a figure unless the figure came from a tool."
        )
    else:
        status = "not_official"
        message = "The address is not on the allowlist of official domains. Do not cite it as an official source."
    return {
        "result_type": "reference",
        "url": url.strip(),
        "status": status,
        "is_official_domain": official,
        "is_stored_source": bool(stored),
        "used_for": stored or [],
        "message": message,
        "page_content_checked": False,
    }
