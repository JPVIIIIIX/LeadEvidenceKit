"""Validate explicit evidence links and render inert Markdown reports."""
import html
import re
from urllib.parse import urlsplit

STATUSES = {"read", "candidate", "blocked", "not_found", "not_run"}
IDENTITIES = {"confirmed", "unconfirmed"}


def safe_url(value):
    """Allow plain HTTP(S) links without credentials or Markdown delimiters.

    No URL is fetched. This is an output check, not an SSRF protection layer.
    """
    if not isinstance(value, str) or re.search(r'[\s<>\[\]()\\"\x00-\x1f\x7f]', value):
        return False
    try:
        parsed = urlsplit(value)
        return (parsed.scheme in {"http", "https"} and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None
                and parsed.port != 0)
    except ValueError:
        return False


def validate_report(report):
    """Return consistency errors; input claims remain the caller's responsibility."""
    if not isinstance(report, dict):
        return ["report must be an object"]
    errors = []
    if not isinstance(report.get("subject"), str) or not report["subject"].strip():
        errors.append("subject must be a nonempty string")
    identity = report.get("identity")
    if not isinstance(identity, str) or identity not in IDENTITIES:
        errors.append("identity must be confirmed or unconfirmed")
    sources = report.get("sources")
    claims = report.get("claims")
    if not isinstance(sources, list) or not isinstance(claims, list):
        return errors + ["sources and claims must be arrays"]
    index = {}
    for n, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"source {n}: must be an object")
            continue
        key = source.get("id")
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", key):
            errors.append(f"source {n}: id must contain letters, digits, underscores or hyphens")
            continue
        if key in index:
            errors.append(f"source {key}: duplicate id")
        index[key] = source
        status = source.get("status")
        if not isinstance(status, str) or status not in STATUSES:
            errors.append(f"source {key}: invalid status")
        if not safe_url(source.get("url")):
            errors.append(f"source {key}: unsafe or invalid URL")
        if not isinstance(source.get("attributed"), bool):
            errors.append(f"source {key}: attributed must be an explicit boolean")
        quote = source.get("quote", "")
        if not isinstance(quote, str):
            errors.append(f"source {key}: quote must be a string")
        elif status == "read" and not quote.strip():
            errors.append(f"source {key}: read sources require an excerpt")
    for n, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append(f"claim {n}: must be an object")
            continue
        if not isinstance(claim.get("text"), str) or not claim["text"].strip():
            errors.append(f"claim {n}: text must be a nonempty string")
        kind = claim.get("kind")
        if not isinstance(kind, str) or kind not in {"fact", "candidate", "unknown"}:
            errors.append(f"claim {n}: invalid kind")
        refs = claim.get("source_ids", [])
        if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
            errors.append(f"claim {n}: source_ids must be an array of strings")
            continue
        if kind == "fact" and not refs:
            errors.append(f"claim {n}: facts require sources")
        for ref in refs:
            source = index.get(ref)
            if source is None:
                errors.append(f"claim {n}: unknown source id {ref}")
            elif kind == "fact" and (source.get("status") != "read"
                                      or source.get("attributed") is not True):
                errors.append(f"claim {n}: facts require read, attributed sources ({ref})")
        if kind == "fact" and identity != "confirmed":
            errors.append(f"claim {n}: unconfirmed subjects cannot receive attributed facts")
    return errors


def _text(value):
    value = html.escape(str(value), quote=True)
    for char in "\\`*_{}[]()#+-.!|>":
        value = value.replace(char, "\\" + char)
    return value.replace("\r", " ").replace("\n", " ")


def render_markdown(report):
    errors = validate_report(report)
    if errors:
        raise ValueError("; ".join(errors))
    lines = [f"# {_text(report['subject'])}", "",
             f"Identity: {report['identity']}", "",
             "Evidence labels are supplied by the caller; this tool does not verify truth.", ""]
    for kind, title in [("fact", "Attributed findings"), ("candidate", "Candidate references"),
                        ("unknown", "Unknowns and follow-up")]:
        lines.extend([f"## {title}", ""])
        rows = [claim for claim in report["claims"] if claim["kind"] == kind]
        for claim in rows:
            refs = ", ".join(claim.get("source_ids", []))
            lines.append(f"- {_text(claim['text'])}" + (f" (sources: {refs})" if refs else ""))
        if not rows:
            lines.append("- None recorded.")
        lines.append("")
    lines.extend(["## Source coverage", ""])
    for source in report["sources"]:
        lines.append(f"- {source['id']}: {source['status']}; attributed: {str(source['attributed']).lower()}")
        lines.append(f"  <{source['url']}>")
        if source.get("quote"):
            lines.append(f"  Excerpt: {_text(source['quote'])}")
    return "\n".join(lines) + "\n"
