"""Bangla season (ritu) for a given date.

Boundaries follow Bangladesh's revised Bangla calendar (2019 revision), in which
Pohela Boishakh is 14 April and Pohela Falgun is 14 February. Each ritu spans
two Bangla months. Dates are Gregorian month/day starts, so this is exact for
the revised calendar and an approximation for the traditional one.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Season:
    key: str
    bangla: str
    latin: str
    english: str
    motif: str


# (start month, start day) -> season, kept in calendar order for the lookup.
_SEASONS: list[tuple[tuple[int, int], Season]] = [
    ((2, 14), Season("boshonto", "বসন্ত", "Boshonto", "spring", "shimul and palash blossoms")),
    ((4, 14), Season("grishmo", "গ্রীষ্ম", "Grishmo", "summer", "mango heat")),
    ((6, 15), Season("borsha", "বর্ষা", "Borsha", "monsoon", "monsoon rain")),
    ((8, 16), Season("shorot", "শরৎ", "Shorot", "early autumn", "kash flowers, open sky")),
    ((10, 17), Season("hemonto", "হেমন্ত", "Hemonto", "late autumn", "ripening paddy")),
    ((12, 16), Season("sheet", "শীত", "Sheet", "winter", "winter fog, date-palm sap")),
]


def season_for(d: date) -> Season:
    """Return the ritu in effect on date ``d``.

    Dates before the first start in the year (1 Jan to 13 Feb) belong to the
    previous year's Sheet, which the default handles.
    """
    current = _SEASONS[-1][1]
    for (month, day), season in _SEASONS:
        if (d.month, d.day) >= (month, day):
            current = season
    return current
