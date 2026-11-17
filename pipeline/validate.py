"""Validate step: data contracts for inputs and audits for rendered outputs.

Hard checks block publishing; the previous assets stay live. Soft checks (claim
verification) change what a card says instead of failing the run, so one edited
README cannot take the whole profile down.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import date, timedelta

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
VIZ_TYPES = {"ci", "seeds", "gate", "stack"}
CARD_FIELDS = {"repo", "title", "order", "status", "summary", "links", "stack", "viz",
               "headline", "subline", "limitation", "claims"}
# Character limits sized for the 480px card (measured with Inter; Segoe UI is similar).
MAX_LINE = {"summary": 62, "limitation": 66, "headline": 54, "subline": 66,
            "stack": 30, "status": 30}
MAX_SVG_BYTES = 120_000


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    severity: str = "hard"

    def as_dict(self) -> dict:
        return asdict(self)


# ---------- inputs ----------

def check_calendar(days: list[dict], run_date: date) -> list[Check]:
    checks = [Check("calendar.non_empty", len(days) >= 364, f"{len(days)} days")]
    if not days:
        return checks
    bad = [d for d in days if not isinstance(d.get("count"), int) or d["count"] < 0]
    checks.append(Check("calendar.counts_non_negative_int", not bad, f"{len(bad)} bad rows"))
    try:
        parsed = [date.fromisoformat(d["date"]) for d in days]
    except (KeyError, ValueError) as err:
        return checks + [Check("calendar.dates_parse", False, str(err))]
    gaps = sum(1 for a, b in zip(parsed, parsed[1:]) if b - a != timedelta(days=1))
    checks.append(Check("calendar.contiguous_ascending", gaps == 0, f"{gaps} gaps or reversals"))
    lag = (run_date - parsed[-1]).days
    # GitHub's calendar is in UTC; a Dhaka-midnight run can be one day ahead.
    checks.append(Check("calendar.fresh", -1 <= lag <= 2, f"latest day lags run date by {lag}d"))
    return checks


def _display_numbers(card: dict) -> list[str]:
    texts = [card["headline"], card["subline"], *card["limitation"]]
    return [n for t in texts for n in NUMBER.findall(t)]


def check_card(card: dict) -> list[Check]:
    name = card.get("title", "?")
    missing = CARD_FIELDS - card.keys()
    if missing:
        return [Check(f"card.{name}.fields", False, f"missing {sorted(missing)}")]
    checks = [Check(f"card.{name}.viz_type", card["viz"].get("type") in VIZ_TYPES,
                    str(card["viz"].get("type")))]
    too_long = []
    for field, limit in MAX_LINE.items():
        values = card[field] if isinstance(card[field], list) else [card[field]]
        too_long += [f"{field}:{len(v)}>{limit}" for v in values if len(v) > limit]
    checks.append(Check(f"card.{name}.line_lengths", not too_long, ", ".join(too_long) or "ok"))
    # No orphan numbers: every number a reader sees must be backed by a claim.
    orphans = [n for n in _display_numbers(card) if not any(n in c for c in card["claims"])]
    checks.append(Check(f"card.{name}.no_orphan_numbers", not orphans,
                        f"unbacked: {orphans}" if orphans else "ok"))
    return checks


def verify_claims(card: dict, readme: str, sha: str) -> dict:
    """Soft check: are all claim strings present verbatim in the README at ``sha``?

    Hyphen-minus and the Unicode minus are treated as the same character.
    """
    norm = readme.replace("−", "-")
    missing = [c for c in card["claims"] if c.replace("−", "-") not in norm]
    return {"state": "stale" if missing else "verified", "sha": sha, "missing": missing}


# ---------- outputs ----------

_EXTERNAL = re.compile(r'(?:href|src)\s*=\s*"(?:https?:)?//', re.IGNORECASE)
_NAN = re.compile(r"(?<![A-Za-z])(?:nan|NaN|inf)(?![A-Za-z])")


def audit_svg(name: str, text: str) -> list[Check]:
    checks = [Check(f"svg.{name}.size", len(text.encode()) <= MAX_SVG_BYTES,
                    f"{len(text.encode())} bytes")]
    try:
        ET.fromstring(text)
        checks.append(Check(f"svg.{name}.well_formed", True, "ok"))
    except ET.ParseError as err:
        checks.append(Check(f"svg.{name}.well_formed", False, str(err)))
    checks.append(Check(f"svg.{name}.no_external_refs", not _EXTERNAL.search(text),
                        "GitHub blocks external resources inside SVG images"))
    checks.append(Check(f"svg.{name}.no_nan", not _NAN.search(text),
                        "NaN coordinates break rendering"))
    return checks
