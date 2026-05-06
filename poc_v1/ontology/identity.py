"""Company identity resolver — TLD-preserving, PSL-aware.

`person@ibm.com` and `person@ibm.ai` are different companies.
Subdomains of one company collapse to the same brand:
`careers@ibm.com` and `mail@careers.ibm.com` both land at
`spice_ibm_com`. Multi-part TLDs (`.co.uk`, `.com.au`) are honored via
``tldextract``'s bundled Public Suffix List snapshot.

This is the canonical identity layer for the Subconscious knowledge
graph: spice-harvester's ``./run.sh``, the burn-substrate Graphiti
sidecar's URL routes, twenty CRM's projection, and any future agent
all turn email/domain inputs into the same trio:

    canonical_domain = "ibm.com"      # display + provenance
    route_slug       = "ibm_com"      # filesystem (output/<slug>) + URL
    group_id         = "spice_ibm_com" # Graphiti namespace

Why this lives in market-ontology rather than each consumer:

The slug shape is part of "what defines a Company" — same conceptual
layer as the Pydantic ``Company`` model. Splitting it across consumers
guarantees drift: spice-harvester had `lib/company_slug.py` and the
sidecar had a separate `namespace.py` that did *less* than the
spice-harvester version (no PSL, no IDN). Subdomains submitted to the
sidecar landed in distinct graphs from the same brand's primary domain.
Single source of truth here removes that footgun.

Public API:

    CompanyIdentity                     dataclass
    to_identity(value)                  one-call resolver (email/URL/domain/slug)
    email_to_slug(email)                email-specific
    domain_to_slug(domain)              domain/URL-specific
    normalize_slug(slug)                boundary validator (subset of to_identity,
                                        for HTTP routes that already have a clean slug)
"""
from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass

import tldextract

# `suffix_list_urls=()` uses the bundled PSL snapshot rather than
# fetching mozilla.org at first call. Predictability matters more than
# freshness for a contract layer.
_extract = tldextract.TLDExtract(suffix_list_urls=())


@dataclass(frozen=True)
class CompanyIdentity:
    """One company's identity at every workspace boundary.

    Attributes:
        canonical_domain: brand + suffix only (``ibm.com``,
            ``lloyds.co.uk``). Subdomains collapsed. IDN punycode-encoded.
        route_slug: filesystem/URL form, dots and hyphens become
            underscores (``ibm_com``, ``lloyds_co_uk``). Matches
            ``[a-z0-9_]+``.
        group_id: Graphiti namespace, ``spice_`` + route_slug.
    """
    canonical_domain: str
    route_slug: str
    group_id: str


_SLUG_OK = re.compile(r"^[a-z0-9][a-z0-9_]*$")
_MAX_LEN = 100


def _strip_protocol_and_path(value: str) -> str:
    """``https://www.openai.com/about?x=1`` -> ``openai.com``.

    Lowercases and removes ``www.`` en route. Returns the empty string
    for empty input — caller handles.
    """
    cleaned = value.strip().lower()
    if "://" in cleaned:
        parsed = urllib.parse.urlparse(cleaned)
        cleaned = parsed.netloc or parsed.path.split("/", 1)[0]
    elif "/" in cleaned:
        cleaned = cleaned.split("/", 1)[0]
    cleaned = cleaned.removeprefix("www.").rstrip("/")
    return cleaned


def _to_ascii(domain: str) -> str:
    """IDN -> punycode. ``café.fr`` -> ``xn--caf-dma.fr``.

    Stable, ASCII, FalkorDB-safe. Returns the original on any encode
    error so the downstream regex check rejects it cleanly.
    """
    if domain.isascii():
        return domain
    try:
        return domain.encode("idna").decode("ascii")
    except UnicodeError:
        return domain


def _validate_slug(slug: str) -> None:
    """Final sanity check on the constructed route slug. ``_SLUG_OK``
    matches what FalkorDB and filesystem paths both accept."""
    if len(slug) > _MAX_LEN:
        raise ValueError(
            f"slug too long ({len(slug)} > {_MAX_LEN}); refusing to "
            f"create a database name from this input"
        )
    if not _SLUG_OK.match(slug):
        raise ValueError(
            f"slug {slug!r} contains illegal characters after "
            f"normalization; expected [a-z0-9][a-z0-9_]*"
        )


def _identity_from_brand_suffix(brand: str, suffix: str) -> CompanyIdentity:
    """Build identity from the (brand, suffix) tuple ``tldextract``
    returned. ``(ibm, com)`` -> route_slug ``ibm_com``. ``(lloyds,
    co.uk)`` -> ``lloyds_co_uk``."""
    canonical = f"{brand}.{suffix}" if suffix else brand
    slug = canonical.replace(".", "_").replace("-", "_")
    _validate_slug(slug)
    return CompanyIdentity(
        canonical_domain=canonical,
        route_slug=slug,
        group_id=f"spice_{slug}",
    )


def _identity_from_canonical(value: str) -> CompanyIdentity:
    """Resolve a domain or URL-shaped input to identity.

    Subdomains collapse to brand+suffix via ``tldextract``
    (``mail.acme.com`` -> ``acme.com``). Bare slugs without a TLD pass
    through (``notion`` -> ``notion``). IDN punycode-encodes at the
    boundary.
    """
    if not value or not value.strip():
        raise ValueError("input must be a non-empty string")
    if ".." in value:
        raise ValueError(
            f"input {value!r} contains path-traversal characters"
        )

    cleaned = _strip_protocol_and_path(value)
    if not cleaned:
        raise ValueError(f"input {value!r} contained no hostname")

    cleaned = _to_ascii(cleaned)

    extracted = _extract(cleaned)
    if extracted.domain and extracted.suffix:
        return _identity_from_brand_suffix(
            extracted.domain, extracted.suffix
        )

    # tldextract didn't see a TLD. Two fallback paths:
    # 1. Route-slug round-trip: ``ibm_com`` (no dots) -> retry as ``ibm.com``.
    if "_" in cleaned and "." not in cleaned:
        retry_input = cleaned.replace("_", ".")
        retry = _extract(retry_input)
        if retry.domain and retry.suffix:
            return _identity_from_brand_suffix(
                retry.domain, retry.suffix
            )

    # 2. Bare slug (legacy ``./run.sh notion`` form): preserve as-is.
    if "." not in cleaned and "/" not in cleaned:
        slug = cleaned.replace("-", "_")
        _validate_slug(slug)
        return CompanyIdentity(
            canonical_domain=cleaned,
            route_slug=slug,
            group_id=f"spice_{slug}",
        )

    raise ValueError(
        f"input {value!r} is not a recognizable domain (no TLD found "
        f"by tldextract, and no underscore/bare-slug fallback applies)"
    )


def email_to_slug(email: str) -> CompanyIdentity:
    """Resolve ``<local>@<domain>`` (with optional ``+tag``) -> identity.

    Strips local-part subaddressing
    (``founder+demo@ibm.com`` -> ``ibm.com``). The domain part flows
    through ``domain_to_slug``.
    """
    if not isinstance(email, str) or "@" not in email:
        raise ValueError(f"not an email: {email!r}")
    local, _, domain = email.strip().partition("@")
    if not local or not domain:
        raise ValueError(f"email missing local or domain part: {email!r}")
    return domain_to_slug(domain)


def domain_to_slug(domain: str) -> CompanyIdentity:
    """Resolve a bare or URL-shaped domain -> identity. Collapses
    subdomains to brand+suffix; punycode-encodes IDN."""
    return _identity_from_canonical(domain)


def to_identity(value: str) -> CompanyIdentity:
    """One-call resolver: emails go through ``email_to_slug``, everything
    else (domains, URLs, route slugs, bare legacy slugs) flows through
    the canonical resolver."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("input must be a non-empty string")
    cleaned = value.strip()
    if "@" in cleaned:
        return email_to_slug(cleaned)
    return domain_to_slug(cleaned)


def normalize_slug(value: str | None) -> CompanyIdentity:
    """Boundary validator for HTTP routes / FastAPI path params.

    Accepts a clean route slug (``ibm_com``) or canonical domain
    (``ibm.com``) and validates it matches ``[a-z0-9_]+`` after lowercase
    + dot/hyphen-to-underscore. Useful as a defense-in-depth check at the
    HTTP path boundary where the caller is expected to have already run
    a producer-side resolver — direct curl POSTs that hit this without
    PSL collapse will be accepted as literal slugs (``mail_acme_com``
    would pass, distinct from ``acme_com``).

    Returns ``CompanyIdentity`` so callers can read both ``route_slug``
    and ``group_id``. Raises ``ValueError`` on empty input, length
    overflow, path traversal, shell metacharacters, uppercase, or
    unicode.

    Equivalent to ``to_identity`` for already-clean inputs but does not
    invoke ``tldextract``, so it's a few microseconds faster — useful
    on hot HTTP paths.
    """
    if not value or not value.strip():
        raise ValueError("slug must be a non-empty string")
    candidate = value.strip().lower().replace(".", "_").replace("-", "_")
    _validate_slug(candidate)
    return CompanyIdentity(
        canonical_domain=candidate.replace("_", "."),
        route_slug=candidate,
        group_id=f"spice_{candidate}",
    )


__all__ = [
    "CompanyIdentity",
    "domain_to_slug",
    "email_to_slug",
    "normalize_slug",
    "to_identity",
]
