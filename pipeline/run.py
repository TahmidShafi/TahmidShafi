"""Entry point: extract -> validate -> render -> audit -> publish.

    python -m pipeline.run --mode live      # in GitHub Actions (needs GITHUB_TOKEN)
    python -m pipeline.run --mode fixture   # offline preview, labelled FIXTURE

Write-audit-publish: everything renders into a staging folder first. Only if
every hard check passes are the files moved into ``--out``. A failed run exits
non-zero and leaves the last good assets in place.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import (extract, fixtures, render_cards, render_gauge, render_hero, render_manifest,
               render_readme)
from .season import season_for
from .svg import THEMES
from .validate import Check, audit_svg, check_calendar, check_card, verify_claims

DHAKA = timezone(timedelta(hours=6))  # Bangladesh has no daylight saving time
ROOT = Path(__file__).resolve().parent.parent


def load_cards(folder: Path) -> list[dict]:
    cards = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))]
    return sorted(cards, key=lambda c: c.get("order", 99))


def slug(card: dict) -> str:
    return card["repo"].split("/")[-1].lower()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=("live", "fixture"), default="fixture")
    ap.add_argument("--out", type=Path, default=ROOT / "assets")
    ap.add_argument("--cards", type=Path, default=ROOT / "cards")
    ap.add_argument("--readme", type=Path, default=ROOT / "README.md",
                    help="README whose cards block is regenerated (skipped if missing)")
    ap.add_argument("--login", default=os.environ.get("PROFILE_LOGIN", "TahmidShafi"))
    ap.add_argument("--date", type=date.fromisoformat, default=None,
                    help="run date (YYYY-MM-DD); defaults to today in Asia/Dhaka")
    args = ap.parse_args(argv)

    now = datetime.now(timezone.utc)
    run_date = args.date or now.astimezone(DHAKA).date()
    season = season_for(run_date)
    cards = load_cards(args.cards)
    checks: list[Check] = []
    verdicts: dict[str, dict] = {}

    # ---- extract ----
    if args.mode == "live":
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("GITHUB_TOKEN is required in live mode", file=sys.stderr)
            return 2
        try:
            days = extract.fetch_calendar(args.login, token)
            public_repos = extract.fetch_public_repo_count(args.login, token)
            for card in cards:
                sha, readme = extract.fetch_readme_at_head(card["repo"], token)
                verdicts[slug(card)] = verify_claims(card, readme, sha)
        except extract.ExtractError as err:
            print(f"extract failed, keeping last good assets: {err}", file=sys.stderr)
            return 1
    else:
        days = fixtures.calendar(run_date)
        public_repos = None
        verdicts = {slug(c): {"state": "unverified", "sha": "", "missing": []} for c in cards}

    # ---- validate inputs ----
    checks += check_calendar(days, run_date)
    for card in cards:
        checks += check_card(card)
    for name, v in verdicts.items():
        checks.append(Check(f"claims.{name}", v["state"] != "stale",
                            f"missing {v['missing']}" if v["missing"] else v["state"], "soft"))
    failed = [c for c in checks if c.severity == "hard" and not c.ok]
    if failed:
        for c in failed:
            print(f"FAIL {c.name}: {c.detail}", file=sys.stderr)
        return 1

    # ---- render into staging ----
    args.out.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=args.out.parent))
    try:
        outputs: dict[str, str] = {}
        for theme in THEMES:
            outputs[f"hero-{theme}.svg"] = render_hero.render(season, theme)
            outputs[f"gauge-{theme}.svg"] = render_gauge.render(
                days, run_date, season, theme, fixture=args.mode == "fixture")
            for card in cards:
                outputs[f"card-{slug(card)}-{theme}.svg"] = render_cards.render(
                    card, verdicts[slug(card)], season, theme)

        # ---- audit outputs ----
        for name, text in outputs.items():
            checks += audit_svg(name, text)

        manifest = {
            "mode": args.mode,
            "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_date": run_date.isoformat(),
            "run_number": os.environ.get("GITHUB_RUN_NUMBER"),
            "commit": os.environ.get("GITHUB_SHA"),
            "login": args.login,
            "season": season.key,
            "extract": {"days": len(days), "public_repos": public_repos},
            "claims": verdicts,
            "checks": [c.as_dict() for c in checks],
        }
        for theme in THEMES:
            name = f"manifest-{theme}.svg"
            outputs[name] = render_manifest.render(manifest, season, theme)
            checks += audit_svg(name, outputs[name])

        failed = [c for c in checks if c.severity == "hard" and not c.ok]
        if failed:
            for c in failed:
                print(f"FAIL {c.name}: {c.detail}", file=sys.stderr)
            return 1
        manifest["checks"] = [c.as_dict() for c in checks]

        for name, text in outputs.items():
            (staging / name).write_text(text, encoding="utf-8")
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                               encoding="utf-8")

        readme_new = None
        if args.readme.exists():
            try:
                readme_new = render_readme.update(args.readme.read_text(encoding="utf-8"),
                                                  cards, [slug(c) for c in cards])
            except ValueError as err:
                print(f"FAIL readme: {err}", file=sys.stderr)
                return 1
            (staging / "_README.md").write_text(readme_new, encoding="utf-8")

        # ---- publish: same filesystem, so each replace is atomic ----
        for path in staging.iterdir():
            target = args.readme if path.name == "_README.md" else args.out / path.name
            os.replace(path, target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    hard = [c for c in checks if c.severity == "hard"]
    soft_bad = [c for c in checks if c.severity == "soft" and not c.ok]
    print(f"published {len(outputs) + 1} files to {args.out} · season {season.latin} · "
          f"{sum(c.ok for c in hard)}/{len(hard)} hard checks · {len(soft_bad)} stale claims")
    for c in soft_bad:
        print(f"WARN {c.name}: {c.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
