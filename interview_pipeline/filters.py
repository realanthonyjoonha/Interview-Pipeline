from __future__ import annotations

import re

from interview_pipeline.catalog import default_min_minutes, watched_people
from interview_pipeline.models import Episode, FilterDecision, Show

DEFAULT_MIN_MINUTES = 20
DWARKESH_ESSAY_MAX_MINUTES = 20

_GUEST_WITH = re.compile(
    r"\b[Ww]ith\s+((?:[A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){0,4})(?:\s+and\s+[A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){0,3})?)",
)
_GUEST_DASH = re.compile(
    r"^\s*([A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){0,4})\s+[–—-]\s+\S"
)
_GUEST_JOINS = re.compile(
    r"\b([A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){0,3})\s+joins\b"
)
_GUEST_PIPE = re.compile(
    r"\|\s*([A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){0,5})"
)
_ROLE_GUEST = re.compile(
    r"\b(?:CEO|CPO|CTO|CPTO|co-founder|founder|head of)\s+([A-Z][\w'.-]+\s+[A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){0,2})",
    re.I,
)

_ESSAY_HINTS = re.compile(
    r"(audio version of|blog post|essay|thoughts on|read the (essay|post)|predictions for)",
    re.I,
)
_NEWS_ROUNDTABLE = re.compile(
    r"(roundtable|news round-?up|this week in|week in (tech|review)|weekly news|news recap|host.?only|mailbag)",
    re.I,
)
_BEST_OF = re.compile(r"\bbest of\b", re.I)
_AINEWS = re.compile(r"\bai\s*news\b|\baineews\b|\baine ws\b|\bAINews\b", re.I)
_SHORT_HINT = re.compile(r"\b(short|shorts|clip|brief|lightning)\b", re.I)
_AMA_ONLY = re.compile(r"\bAMA\b")
_ILTB_TOPIC = re.compile(
    r"\b(ai|a\.i\.|llm|gpt|claude|gpu|gpus|chip|chips|semiconductor|nvidia|tsmc|"
    r"foundry|datacenter|data center|infra|infrastructure|lab|laboratory|model|"
    r"inference|training|silicon|wafer|hbm|compute|openai|anthropic|deepmind|"
    r"xai|robotics|accelerator|asic|tpu|foundational)\b",
    re.I,
)
_SEMI_SHORT_OK = re.compile(
    r"(china silicon|chinese silicon|smic|huawei|inferencex|inference x|\bteardown\b)",
    re.I,
)
_DEVTOOL_ADOPTION = re.compile(
    r"\b(ai|llm|tool|tools|developer|dev-?tool|enterprise|adoption|platform|"
    r"engineering|observability|agent|agents|ide|copilot|cursor)\b",
    re.I,
)
_LENNY_AI_PRODUCT = re.compile(
    r"\b(ai|a\.i\.|llm|llms|gpt|claude|anthropic|openai|gemini|copilot|cursor|"
    r"agent|agents|model|models|foundation model|inference|chatbot|genai|"
    r"generative|machine learning|deep learning|token|tokens|ai-product|"
    r"ai product)\b",
    re.I,
)
_HOST_ONLY_HINTS = re.compile(
    r"(host.?only|just (sarah|elad|the hosts)|no guest|between the hosts)",
    re.I,
)
_DYLAN_PATEL = re.compile(r"\bdylan\s+patel\b", re.I)
ALWAYS_IN_SCOPE_PERSON = "Dylan Patel"


def extract_guest_hint(
    title: str,
    description: str = "",
    hosts: tuple[str, ...] = (),
) -> str | None:
    blob = title.strip()
    guest = None
    for pattern in (_GUEST_WITH, _GUEST_JOINS, _GUEST_DASH, _GUEST_PIPE):
        match = pattern.search(blob)
        if match:
            guest = _clean_guest(match.group(1))
            break
    if guest is None:
        role = _ROLE_GUEST.search(blob)
        if role:
            guest = _clean_guest(role.group(0))
    if guest is None:
        desc_match = _GUEST_JOINS.search(description) or _GUEST_WITH.search(description)
        if desc_match:
            guest = _clean_guest(desc_match.group(1))
    if guest and _is_only_hosts(guest, hosts):
        return None
    return guest


def _is_only_hosts(guest: str, hosts: tuple[str, ...]) -> bool:
    if not hosts:
        return False
    parts = [part.strip() for part in re.split(r"\s*(?:&|and|,|/)\s*", guest) if part.strip()]
    if not parts:
        return False
    host_l = {host.lower() for host in hosts}
    for part in parts:
        lowered = part.lower()
        if lowered in host_l:
            continue
        if any(lowered == host or lowered in host.split() for host in host_l):
            continue
        return False
    return True


def _clean_guest(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" ,;:.-")
    cleaned = re.sub(r"\s+\((?:CEO|CPO|CTO|founder).*$", "", cleaned, flags=re.I)
    return cleaned


def _minutes(episode: Episode) -> float | None:
    return episode.duration_minutes


def _too_short(episode: Episode, minimum: float, *, allow_unknown: bool = False) -> bool:
    minutes = _minutes(episode)
    if minutes is None:
        return not allow_unknown
    return minutes < minimum


def _dylan_patel_named(episode: Episode, hosts: tuple[str, ...] = ()) -> bool:
    guest = _guest(episode, hosts) or ""
    blob = f"{episode.title}\n{guest}\n{episode.description[:800]}"
    return bool(_DYLAN_PATEL.search(blob))


def decide(episode: Episode, show: Show, *, min_minutes: int | None = None) -> FilterDecision:
    """Return whether this episode should be fetched / reported on."""
    bar = float(min_minutes if min_minutes is not None else default_min_minutes())
    if (
        ALWAYS_IN_SCOPE_PERSON in watched_people()
        and _dylan_patel_named(episode, show.hosts)
        and not _too_short(episode, bar, allow_unknown=True)
    ):
        guest = _guest(episode, show.hosts) or ALWAYS_IN_SCOPE_PERSON
        return _ok([f"Dylan Patel sit (>= {bar:g} min); always in-scope"], guest)
    handler = {
        "dwarkesh": _dwarkesh,
        "cheeky_pint": _cheeky_pint,
        "no_priors": _no_priors,
        "bg2": _bg2,
        "big_technology": _big_technology,
        "iltb": _iltb,
        "semianalysis": _semianalysis,
        "latent_space": _latent_space,
        "pragmatic_engineer": _pragmatic_engineer,
        "lennys": _lennys,
        "length_only": _length_only,
    }.get(show.filter, _length_only)
    return handler(episode, bar, show.hosts)


def _ok(reasons: list[str], guest: str | None = None) -> FilterDecision:
    return FilterDecision(True, tuple(reasons), guest)


def _skip(reasons: list[str], guest: str | None = None) -> FilterDecision:
    return FilterDecision(False, tuple(reasons), guest)


def _guest(episode: Episode, hosts: tuple[str, ...] = ()) -> str | None:
    return extract_guest_hint(episode.title, episode.description, hosts)


def _dwarkesh(episode: Episode, bar: float, hosts: tuple[str, ...] = ()) -> FilterDecision:
    guest = _guest(episode, hosts)
    minutes = _minutes(episode)
    essay = bool(_ESSAY_HINTS.search(episode.title) or _ESSAY_HINTS.search(episode.description[:400]))
    if minutes is not None and minutes < DWARKESH_ESSAY_MAX_MINUTES:
        return _skip([f"skip sub-{DWARKESH_ESSAY_MAX_MINUTES:.0f} min Dwarkesh essay/short"], guest)
    if essay and not guest:
        return _skip(["interviews only; title/description looks like an essay"], guest)
    if not guest:
        return _skip(["interviews only; no guest name in title"], guest)
    if minutes is not None and minutes < bar:
        # Interviews over the essay floor still pass; guest sits at 20+ count.
        return _ok([f"Dwarkesh interview ({minutes:.0f} min, guest sit)"], guest)
    return _ok(["Dwarkesh interview"], guest)


def _cheeky_pint(episode: Episode, bar: float, hosts: tuple[str, ...] = ()) -> FilterDecision:
    guest = _guest(episode, hosts)
    if not guest:
        return _skip(["Cheeky Pint: founder sit required; no guest in title"])
    if _too_short(episode, bar, allow_unknown=True):
        return _skip([f"under {bar:.0f} min length bar"], guest)
    return _ok(["Cheeky Pint founder sit"], guest)


def _no_priors(episode: Episode, bar: float, hosts: tuple[str, ...] = ()) -> FilterDecision:
    guest = _guest(episode, hosts)
    minutes = _minutes(episode)
    host_only = bool(_HOST_ONLY_HINTS.search(episode.title)) or not guest
    if host_only and (minutes is None or minutes < bar):
        return _skip([f"No Priors: skip host-only under {bar:g}"], guest)
    if guest:
        return _ok(["No Priors guest sit"], guest)
    return _ok([f"No Priors host conversation at {minutes:.0f} min (>= {bar:g})"], guest)


def _bg2(episode: Episode, bar: float, hosts: tuple[str, ...] = ()) -> FilterDecision:
    guest = _guest(episode, hosts)
    if _too_short(episode, bar, allow_unknown=True):
        return _skip([f"BG2 under {bar:.0f} min"], guest)
    return _ok(["BG2 episode over length bar"], guest)


def _big_technology(episode: Episode, bar: float, hosts: tuple[str, ...] = ()) -> FilterDecision:
    guest = _guest(episode, hosts)
    title = episode.title
    if _NEWS_ROUNDTABLE.search(title):
        return _skip(["Big Technology: skip news roundtables"], guest)
    if _BEST_OF.search(title) and not guest:
        return _skip(["Big Technology: skip best-of without a named guest"], guest)
    if not guest:
        return _skip(["Big Technology: named guest interview required"], guest)
    if _too_short(episode, bar, allow_unknown=True):
        return _skip([f"under {bar:.0f} min length bar"], guest)
    return _ok(["Big Technology named guest interview"], guest)


def _iltb(episode: Episode, bar: float, hosts: tuple[str, ...] = ()) -> FilterDecision:
    guest = _guest(episode, hosts)
    blob = f"{episode.title}\n{episode.description[:800]}"
    if not _ILTB_TOPIC.search(blob):
        return _skip(["Invest Like the Best: not an AI / infra / chip / lab guest"], guest)
    if _too_short(episode, bar, allow_unknown=True):
        return _skip([f"under {bar:.0f} min length bar"], guest)
    return _ok(["Invest Like the Best AI/infra/chip/lab guest"], guest)


def _semianalysis(episode: Episode, bar: float, hosts: tuple[str, ...] = ()) -> FilterDecision:
    guest = _guest(episode, hosts)
    minutes = _minutes(episode)
    blob = f"{episode.title}\n{episode.description[:600]}"
    short_ok = bool(_SEMI_SHORT_OK.search(blob))
    if minutes is not None and minutes < bar and not short_ok:
        return _skip(
            [f"SemiAnalysis Weekly under {bar:g} min without China silicon / InferenceX / teardown exception"],
            guest,
        )
    reason = "SemiAnalysis Weekly technical staff analysis"
    if short_ok and minutes is not None and minutes < bar:
        reason += " (short teardown/emergency exception)"
    return _ok([reason], guest)


def _latent_space(episode: Episode, bar: float, hosts: tuple[str, ...] = ()) -> FilterDecision:
    guest = _guest(episode, hosts)
    title = episode.title
    if _AINEWS.search(title) or title.strip().lower().startswith("ainews"):
        return _skip(["Latent Space: ignore AINews shorts"], guest)
    if _SHORT_HINT.search(title) and _too_short(episode, bar, allow_unknown=True):
        return _skip(["Latent Space: ignore shorts"], guest)
    if _too_short(episode, bar, allow_unknown=True):
        return _skip(["Latent Space: long interviews only"], guest)
    if not guest:
        return _skip(["Latent Space: long interviews only; no guest in title"], guest)
    return _ok(["Latent Space long interview"], guest)


def _pragmatic_engineer(episode: Episode, bar: float, hosts: tuple[str, ...] = ()) -> FilterDecision:
    guest = _guest(episode, hosts)
    if _AMA_ONLY.search(episode.title) and not guest:
        return _skip(["Pragmatic Engineer: skip host AMA without a guest"], guest)
    if not guest:
        return _skip(["Pragmatic Engineer: enterprise/dev-tool interview needs a guest"], guest)
    blob = f"{episode.title}\n{episode.description[:600]}"
    if not _DEVTOOL_ADOPTION.search(blob):
        return _skip(["Pragmatic Engineer: not an enterprise/dev-tool adoption interview"], guest)
    if _too_short(episode, bar, allow_unknown=True):
        return _skip([f"under {bar:.0f} min length bar"], guest)
    return _ok(["Pragmatic Engineer enterprise/dev-tool interview"], guest)


def _lennys(episode: Episode, bar: float, hosts: tuple[str, ...] = ()) -> FilterDecision:
    guest = _guest(episode, hosts)
    blob = f"{episode.title}\n{episode.description[:600]}"
    if not _LENNY_AI_PRODUCT.search(blob):
        return _skip(["Lenny's: guest/title is not AI-product"], guest)
    if _too_short(episode, bar, allow_unknown=True):
        return _skip([f"under {bar:.0f} min length bar"], guest)
    return _ok(["Lenny's AI-product episode"], guest)


def _length_only(episode: Episode, bar: float, hosts: tuple[str, ...] = ()) -> FilterDecision:
    guest = _guest(episode, hosts)
    if _too_short(episode, bar, allow_unknown=True):
        return _skip([f"under {bar:.0f} min length bar"], guest)
    return _ok([f"over {bar:.0f} min length bar"], guest)
