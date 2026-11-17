"""Offline fixture data for previews and tests.

The calendar is synthetic: seeded random activity with a few bursts. Every
asset rendered from it is labelled FIXTURE, and the live workflow never uses it.
"""
from __future__ import annotations

import random
from datetime import date, timedelta


def calendar(run_date: date, days: int = 371, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    start = run_date - timedelta(days=days - 1)
    out = []
    burst = 0
    for i in range(days):
        d = start + timedelta(days=i)
        if burst == 0 and rng.random() < 0.035:
            burst = rng.randint(4, 12)
        base = 0 if rng.random() < 0.45 else rng.randint(1, 4)
        if burst:
            base += rng.randint(3, 11)
            burst -= 1
        if d.weekday() == 4 and rng.random() < 0.6:  # quieter Fridays
            base //= 3
        out.append({"date": d.isoformat(), "count": base})
    return out
