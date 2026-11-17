"""Unit tests for the profile pipeline (standard library unittest, no network).

Run: python -m unittest discover -s tests
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from pipeline import fixtures, render_cards, render_gauge, render_hero, render_readme
from pipeline.run import load_cards, main
from pipeline.season import season_for
from pipeline.validate import audit_svg, check_calendar, check_card, verify_claims

ROOT = Path(__file__).resolve().parent.parent


class SeasonTests(unittest.TestCase):
    def test_boundaries_follow_revised_calendar(self):
        cases = {
            date(2026, 4, 13): "boshonto", date(2026, 4, 14): "grishmo",
            date(2026, 6, 14): "grishmo", date(2026, 6, 15): "borsha",
            date(2026, 8, 16): "shorot", date(2026, 10, 16): "shorot",
            date(2026, 10, 17): "hemonto", date(2026, 12, 15): "hemonto",
            date(2026, 12, 16): "sheet", date(2027, 1, 1): "sheet",
            date(2027, 2, 13): "sheet", date(2027, 2, 14): "boshonto",
        }
        for d, expected in cases.items():
            with self.subTest(d=d):
                self.assertEqual(season_for(d).key, expected)


class CalendarContractTests(unittest.TestCase):
    run_date = date(2026, 11, 17)

    def _ok(self, days):
        return all(c.ok for c in check_calendar(days, self.run_date))

    def test_fixture_passes(self):
        self.assertTrue(self._ok(fixtures.calendar(self.run_date)))

    def test_negative_count_rejected(self):
        days = fixtures.calendar(self.run_date)
        days[10]["count"] = -1
        self.assertFalse(self._ok(days))

    def test_gap_rejected(self):
        days = fixtures.calendar(self.run_date)
        del days[100]
        self.assertFalse(self._ok(days))

    def test_stale_data_rejected(self):
        days = fixtures.calendar(self.run_date - timedelta(days=10))
        self.assertFalse(self._ok(days))


class CardContractTests(unittest.TestCase):
    def setUp(self):
        self.cards = load_cards(ROOT / "cards")

    def test_shipped_cards_pass(self):
        for card in self.cards:
            for check in check_card(card):
                with self.subTest(card=card["title"], check=check.name):
                    self.assertTrue(check.ok, check.detail)

    def test_orphan_number_rejected(self):
        card = dict(self.cards[0], headline="+0.999 precision@4 over rule counts")
        names = {c.name: c.ok for c in check_card(card)}
        self.assertFalse(names[f"card.{card['title']}.no_orphan_numbers"])

    def test_claims_verified_and_stale(self):
        card = {"claims": ["0.131", "-8.56%"]}
        ok = verify_claims(card, "gain 0.131 and cost −8.56% relative", "a" * 40)
        self.assertEqual(ok["state"], "verified")  # Unicode minus matches hyphen
        stale = verify_claims(card, "gain 0.130", "b" * 40)
        self.assertEqual(stale["state"], "stale")
        self.assertEqual(stale["missing"], ["0.131", "-8.56%"])


class RenderTests(unittest.TestCase):
    season = season_for(date(2026, 11, 17))

    def _assert_clean(self, name, svg):
        for check in audit_svg(name, svg):
            with self.subTest(asset=name, check=check.name):
                self.assertTrue(check.ok, check.detail)

    def test_every_asset_passes_audit_in_both_themes(self):
        run_date = date(2026, 11, 17)
        days = fixtures.calendar(run_date)
        verdict = {"state": "unverified", "sha": "", "missing": []}
        for theme in ("dark", "light"):
            self._assert_clean("hero", render_hero.render(self.season, theme))
            self._assert_clean("gauge", render_gauge.render(days, run_date, self.season, theme, True))
            for card in load_cards(ROOT / "cards"):
                self._assert_clean(card["title"], render_cards.render(card, verdict, self.season, theme))

    def test_user_text_is_escaped(self):
        card = load_cards(ROOT / "cards")[0]
        card = dict(card, title="<script>&")
        svg = render_cards.render(card, {"state": "unverified", "sha": "", "missing": []},
                                  self.season, "dark")
        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;script&gt;&amp;", svg)

    def test_external_refs_caught(self):
        bad = '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://x.test/a.png"/></svg>'
        self.assertFalse(all(c.ok for c in audit_svg("bad", bad)))


class ReadmeTests(unittest.TestCase):
    def test_block_replaced_and_rest_untouched(self):
        cards = load_cards(ROOT / "cards")
        slugs = [c["repo"].split("/")[-1].lower() for c in cards]
        src = f"intro\n{render_readme.START}\nold\n{render_readme.END}\noutro"
        out = render_readme.update(src, cards, slugs)
        self.assertTrue(out.startswith("intro\n") and out.endswith("\noutro"))
        self.assertNotIn("\nold\n", out)
        self.assertEqual(out.count("<picture>"), len(cards))
        self.assertEqual(render_readme.update(out, cards, slugs), out)  # idempotent

    def test_missing_markers_raise(self):
        with self.assertRaises(ValueError):
            render_readme.update("no markers", [], [])


class WeeklyBinTests(unittest.TestCase):
    def test_bins_sum_window_exactly(self):
        run_date = date(2026, 11, 17)
        days = fixtures.calendar(run_date)
        weeks = render_gauge.weekly_totals(days, run_date)
        self.assertEqual(len(weeks), 52)
        self.assertEqual(weeks[-1][0] + timedelta(days=6), run_date)
        self.assertEqual(sum(v for _, v in weeks), sum(d["count"] for d in days[-364:]))

    def test_percentile_matches_linear_method(self):
        self.assertEqual(render_gauge.percentile([1, 2, 3, 4], 0.5), 2.5)
        self.assertAlmostEqual(render_gauge.percentile(list(range(11)), 0.9), 9.0)


class PublishTests(unittest.TestCase):
    def test_fixture_run_publishes_and_failed_run_keeps_old_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "assets"
            readme = Path(tmp) / "README.md"
            readme.write_text((ROOT / "README.md").read_text())
            self.assertEqual(main(["--mode", "fixture", "--out", str(out), "--readme", str(readme),
                                   "--date", "2026-11-17"]), 0)
            self.assertIn("card-curbstone-dark.svg", readme.read_text())
            manifest = json.loads((out / "manifest.json").read_text())
            self.assertEqual(manifest["mode"], "fixture")
            before = (out / "hero-dark.svg").read_text()

            # A card that breaks its contract must block publishing entirely.
            cards = Path(tmp) / "cards"
            cards.mkdir()
            broken = json.loads((ROOT / "cards" / "curbstone.json").read_text())
            broken["headline"] = "+9.999 made-up number"
            (cards / "c.json").write_text(json.dumps(broken))
            code = main(["--mode", "fixture", "--out", str(out), "--cards", str(cards),
                         "--readme", str(readme), "--date", "2026-11-18"])
            self.assertEqual(code, 1)
            self.assertEqual((out / "hero-dark.svg").read_text(), before)
            self.assertEqual(json.loads((out / "manifest.json").read_text())["run_date"], "2026-11-17")


if __name__ == "__main__":
    unittest.main()
